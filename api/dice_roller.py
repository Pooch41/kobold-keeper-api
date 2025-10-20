import random
import re
from typing import Dict, Any


class InvalidRollFormula(Exception):
    """Custom exception raised when the provided dice formula is syntactically invalid."""
    pass


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
        Parses a single dice component string (e.g., '3d6', '4d20kh1'), executes the
        physical roll, and applies drop/keep logic.

        :param dice_part: A single dice component string.
        :raises InvalidRollFormula: If the dice component format is invalid.
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

        rolls = [random.randint(1, die_size) for _ in range(num_dice)]

        if not drop_keep_key:
            total = sum(rolls)
            return {
                'component_type': 'dice',
                'formula': dice_part,
                'rolls': rolls,
                'total': total,
            }

        sorted_rolls = sorted(rolls)
        retained_rolls = []
        dropped_rolls = []

        if drop_keep_key == 'dl':
            dropped_rolls = sorted_rolls[:drop_keep_amount]
            retained_rolls = sorted_rolls[drop_keep_amount:]
        elif drop_keep_key == 'kl':
            retained_rolls = sorted_rolls[:drop_keep_amount]
            dropped_rolls = sorted_rolls[drop_keep_amount:]
        elif drop_keep_key == 'dh':
            dropped_rolls = sorted_rolls[-drop_keep_amount:]
            retained_rolls = sorted_rolls[:-drop_keep_amount]
        elif drop_keep_key == 'kh':
            retained_rolls = sorted_rolls[-drop_keep_amount:]
            dropped_rolls = sorted_rolls[:-drop_keep_amount]

        return {
            'component_type': 'dice',
            'formula': dice_part,
            'drop_keep': f'{drop_keep_key}{drop_keep_amount}',
            'rolls': rolls,
            'dropped_rolls': dropped_rolls,
            'retained_rolls': retained_rolls,
            'total': sum(retained_rolls),
        }

    @classmethod
    def calculate_roll(cls, formula: str) -> Dict[str, Any]:
        """
        The main public method. Parses the full formula string, breaks it into
        components, executes all rolls, and sums the results.

        :param formula: The dice roll formula string (e.g., '1d20+5').
        :raises InvalidRollFormula: If the overall formula syntax is invalid.
        :return: A dictionary with the 'final_result', the original 'roll_formula',
                 and a list of 'roll_details' for persistence.
        """
        formula = formula.replace(' ', '')
        if not formula:
            raise InvalidRollFormula("Formula cannot be empty.")

        roll_details = []
        total = 0
        last_end = 0

        if formula[0] not in ('+', '-'):
            formula = '+' + formula

        for match in cls.TOKEN_RE.finditer(formula):
            sign = match.group(1)
            term = match.group(2)
            start, end = match.span()

            if start > last_end:
                unconsumed_str = formula[last_end:start]
                if unconsumed_str and not unconsumed_str.strip():
                    pass
                else:
                    raise InvalidRollFormula(
                        f"Formula contains invalid syntax: '{unconsumed_str}'")

            last_end = end
            component_total = 0

            if term.isdigit():
                component_total = int(term)
                detail = {
                    'component_type': 'modifier',
                    'formula': term,
                    'value': component_total
                }

            elif 'd' in term or 'D' in term:
                try:
                    detail = cls._parse_and_roll_dice(term)
                    component_total = detail['total']
                except ValueError:
                    raise InvalidRollFormula(
                        f"Invalid drop/keep format or unrecognized suffix in: {term}")

            else:
                raise InvalidRollFormula(f"Unrecognized term: {term}")

            if sign == '-':
                total -= component_total
            else:
                total += component_total

            roll_details.append(detail)

        if last_end < len(formula):
            unconsumed_str = formula[last_end:]
            raise InvalidRollFormula(f"Formula contains invalid syntax: '{unconsumed_str}'")

        return {
            'roll_formula': formula.strip('+'),
            'final_result': int(total),
            'roll_details': roll_details
        }
