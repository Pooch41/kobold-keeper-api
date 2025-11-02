"""
Core utility module for parsing and executing complex dice roll formulas.

This module provides the main `DiceRoller` class, which is responsible for
parsing standard dice notation (e.g., '1d20+5'), including advanced
drop/keep modifiers (e.g., '4d6kh3'). It calculates the final result, provides
a detailed breakdown of all roll components, and computes a 'luck_index'
based on the roll's deviation from the statistical average.

Classes:
    InvalidRollFormula: Custom exception raised for malformed dice strings.
    DiceRoller: A static class that parses and executes dice formulas.

Usage:
    from .dice_roller import DiceRoller, InvalidRollFormula

    try:
        roll_data = DiceRoller.calculate_roll('2d20dl1+1d4+12')
        print(roll_data['final_result'])
    except InvalidRollFormula as e:
        print(f"Error: {e}")
"""

import random
import re
from typing import Dict, Any


class InvalidRollFormula(Exception):
    """Custom exception raised when the provided dice formula is syntactically invalid."""


class DiceRoller:
    """
    Core class responsible for parsing dice formulas, executing the rolls,
    and calculating the final result.
    """
    TOKEN_RE = re.compile(
        r"([+-])?([1-9][0-9]*[dD][1-9][0-9]*(?:(?:dl|dh|kl|kh)[1-9][0-9]*)?|[1-9][0-9]*)")

    @staticmethod
    def _parse_and_roll_dice(dice_part: str) -> Dict[str, Any]:
        """
        ... (docstring) ...
        :return: A dictionary containing details of the executed roll (rolls, total, etc.).
        """
        lower_dice_part = dice_part.lower()
        match_dice = re.match(r"("
                              r"[1-9][0-9]*)[dD]([1-9][0-9]*)(?:(dl|dh|kl|kh)([1-9][0-9]*))?$",
                              lower_dice_part)

        if not match_dice:
            raise InvalidRollFormula(f"Invalid dice format in: {dice_part}")

        num_dice = int(match_dice.group(1))
        die_size = int(match_dice.group(2))
        drop_keep_key = match_dice.group(3)
        drop_keep_amount_str = match_dice.group(4)
        drop_keep_amount = int(drop_keep_amount_str) if drop_keep_amount_str else 0

        if num_dice < 1 or die_size < 1:
            raise InvalidRollFormula("Dice count and size must be at least 1.")

        if drop_keep_key and (drop_keep_amount <= 0 or drop_keep_amount >= num_dice):
            raise InvalidRollFormula(
                f"Drop/Keep amount ({drop_keep_amount}) "
                f"must be greater than 0 and less than the number of dice rolled ({num_dice})."
            )


        expected_avg_per_die = (die_size + 1) / 2.0
        roll_range_per_die = float(die_size - 1)

        rolls = [random.randint(1, die_size) for _ in range(num_dice)]

        if not drop_keep_key:
            total = sum(rolls)
            return {
                'component_type': 'dice',
                'formula': dice_part,
                'rolls': rolls,
                'total': total,
                'expected_avg': num_dice * expected_avg_per_die,
                'roll_range': num_dice * roll_range_per_die,
                'retained_sum': total
            }

        sorted_rolls = sorted(rolls)

        logic_map = {
            'dl': lambda r, a: (r[:a], r[a:]),
            'kl': lambda r, a: (r[a:], r[:a]),
            'dh': lambda r, a: (r[-a:], r[:-a]),
            'kh': lambda r, a: (r[:-a], r[-a:]),
        }

        dropped_rolls, retained_rolls = logic_map[drop_keep_key](
            sorted_rolls, drop_keep_amount
        )

        retained_sum = sum(retained_rolls)
        retained_count = len(retained_rolls)

        return {
            'component_type': 'dice',
            'formula': dice_part,
            'drop_keep': f'{drop_keep_key}{drop_keep_amount}',
            'rolls': rolls,
            'dropped_rolls': dropped_rolls,
            'retained_rolls': retained_rolls,
            'total': retained_sum,
            'expected_avg': retained_count * expected_avg_per_die,
            'roll_range': retained_count * roll_range_per_die,
            'retained_sum': retained_sum,
        }

    @classmethod
    def _process_roll_term(cls, term: str) -> Dict[str, Any]:
        """
        ... (docstring) ...
        """
        if term.isdigit():
            try:
                component_total = int(term)
            except ValueError as exc:
                raise InvalidRollFormula(f"Invalid modifier value: {term}") from exc

            return {
                'component_type': 'modifier',
                'formula': term,
                'value': component_total,
                'total': component_total
            }

        if 'd' in term or 'D' in term:
            try:
                detail = cls._parse_and_roll_dice(term)
                if 'total' not in detail:
                    raise InvalidRollFormula(f"Dice roll detail missing total for term: {term}")
                return detail
            except InvalidRollFormula as exc:
                raise InvalidRollFormula(f"Dice component validation failed for: {term}") from exc
            except ValueError as exc:
                raise InvalidRollFormula(
                    f"Internal conversion error in dice format: {term}") from exc

        raise InvalidRollFormula(f"Unrecognized term: {term}")

    @classmethod
    def calculate_roll(cls, formula: str) -> Dict[str, Any]:
        """
        ... (docstring) ...
        :return: A dictionary with 'final_result', 'roll_formula',
                 'roll_details', and 'luck_index'.
        """
        formula = formula.replace(' ', '')
        if not formula:
            raise InvalidRollFormula("Formula cannot be empty.")

        roll_details = []
        total = 0
        total_dice_sum = 0.0
        total_expected_avg = 0.0
        total_roll_range = 0.0


        last_end = 0

        if formula[0] not in ('+', '-'):
            formula = '+' + formula

        for match in cls.TOKEN_RE.finditer(formula):
            sign = match.group(1)
            term = match.group(2)
            start, end = match.span()

            if start > last_end:
                unconsumed_str = formula[last_end:start]
                if unconsumed_str and unconsumed_str.strip():
                    raise InvalidRollFormula(
                        f"Formula contains invalid syntax: '{unconsumed_str}'")

            last_end = end

            detail = cls._process_roll_term(term)
            component_total = detail['total']

            if sign == '-':
                total -= component_total
            else:
                total += component_total

            if detail.get('component_type') == 'dice':
                dice_sum = detail.get('retained_sum', 0.0)
                expected_avg = detail.get('expected_avg', 0.0)
                roll_range = detail.get('roll_range', 0.0)

                if sign == '-':
                    total_dice_sum -= dice_sum
                    total_expected_avg -= expected_avg
                else:
                    total_dice_sum += dice_sum
                    total_expected_avg += expected_avg

                total_roll_range += roll_range

            roll_details.append(detail)

        if last_end < len(formula):
            unconsumed_str = formula[last_end:]
            raise InvalidRollFormula(f"Formula contains invalid syntax: '{unconsumed_str}'")

        final_luck_index = 0.0
        if total_roll_range > 0:
            final_luck_index = (total_dice_sum - total_expected_avg) / total_roll_range

        return {
            'roll_formula': formula.strip('+'),
            'final_result': int(total),
            'roll_details': roll_details,
            'luck_index': final_luck_index # <-- The new calculated value
        }