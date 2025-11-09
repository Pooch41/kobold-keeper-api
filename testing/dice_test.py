"""
Unit tests for the DiceRoller utility class.

This module uses the standard Python `unittest` framework to verify that
the DiceRoller correctly parses and calculates various dice notation formats,
including simple rolls, modifiers, and drop/keep logic (e.g., 4d6dl1, 5d8kh3).

All tests use a fixed random seed (42) to ensure deterministic results.
"""

import random
import re
import unittest

from api.dice_roller import DiceRoller, InvalidRollFormula

FIXED_SEED = 42


class DiceRollerTestCase(unittest.TestCase):
    """Container for all tests related to the DiceRoller utility class."""

    def setUp(self):
        """Reset the random seed before every test for determinism."""
        random.seed(FIXED_SEED)

    def _assert_roll_result(self, formula: str, expected_total: int, expected_details_count: int):
        """
                Helper method to perform common assertions across various roll formulas.

                Args:
                    formula (str): The dice formula to test (e.g., "1d20+5").
                    expected_total (int): The expected final numerical result of the roll.
                    expected_details_count (int): The expected number of tokenized elements
                                                  (dice rolls or modifiers) in the result.
                """
        result = DiceRoller.calculate_roll(formula)
        self.assertEqual(result['final_result'], expected_total,
                         f"Formula '{formula}' failed:"
                         f" Expected {expected_total}, got {result['final_result']}")
        self.assertEqual(len(result['roll_details']), expected_details_count,
                         f"Formula '{formula}' failed:"
                         f" Expected {expected_details_count} tokens, "
                         f"got {len(result['roll_details'])}")

    def test_simple_d6_roll(self):
        self._assert_roll_result("1d6", 6, 1)

    def test_multi_dice_roll(self):
        self._assert_roll_result("2d6", 7, 1)

    def test_d10_roll(self):
        self._assert_roll_result("3d10", 8, 1)

    def test_positive_modifier(self):
        self._assert_roll_result("1d20+5", 9, 2)

    def test_negative_modifier(self):
        self._assert_roll_result("2d6-3", 4, 2)

    def test_modifier_only(self):
        self._assert_roll_result("15", 15, 1)

    def test_drop_lowest(self):
        result = DiceRoller.calculate_roll("4d6dl1")
        self.assertEqual(result['final_result'], 13)
        details = result['roll_details'][0]
        self.assertEqual(details['rolls'], [6, 1, 1, 6])
        self.assertEqual(details['dropped_rolls'], [1])
        self.assertEqual(details['retained_rolls'], [1, 6, 6])
        self.assertEqual(details['drop_keep'], 'dl1')

    def test_keep_highest(self):
        result = DiceRoller.calculate_roll("5d8kh3")
        self.assertEqual(result['final_result'], 13)
        details = result['roll_details'][0]
        self.assertEqual(details['rolls'], [2, 1, 5, 4, 4])
        self.assertEqual(details['dropped_rolls'], [1, 2])
        self.assertEqual(details['retained_rolls'], [4, 4, 5])
        self.assertEqual(details['drop_keep'], 'kh3')

    def test_drop_highest(self):
        random.seed(FIXED_SEED)  # Reset for this test
        result = DiceRoller.calculate_roll("5d8dh2")
        self.assertEqual(result['final_result'], 7)
        details = result['roll_details'][0]
        self.assertEqual(details['rolls'], [2, 1, 5, 4, 4])
        self.assertEqual(details['dropped_rolls'], [4, 5])
        self.assertEqual(details['retained_rolls'], [1, 2, 4])
        self.assertEqual(details['drop_keep'], 'dh2')

    def test_keep_lowest(self):
        random.seed(FIXED_SEED)
        result = DiceRoller.calculate_roll("5d8kl2")
        self.assertEqual(result['final_result'], 3)
        details = result['roll_details'][0]
        self.assertEqual(details['rolls'], [2, 1, 5, 4, 4])
        self.assertEqual(details['dropped_rolls'], [4, 4, 5])
        self.assertEqual(details['retained_rolls'], [1, 2])
        self.assertEqual(details['drop_keep'], 'kl2')

    def test_complex_formula(self):
        self._assert_roll_result("1d8+2d6dl1+10-1d4", 15, 4)

    def test_empty_formula(self):
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula cannot be empty.")):
            DiceRoller.calculate_roll("")

    def test_invalid_modifier_char(self):
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: '+a'")):
            DiceRoller.calculate_roll("1d6+a")

    def test_invalid_syntax(self):
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: 'g'")):
            DiceRoller.calculate_roll("1d6+5g")

    def test_zero_die_size(self):
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: 'd0'")):
            DiceRoller.calculate_roll("1d0")

    def test_zero_die_count(self):
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: '+0d'")):
            DiceRoller.calculate_roll("0d6")

    def test_drop_amount_equal_to_count(self):
        """Test dropping all rolled dice (e.g., 2d6dl2). This must be disallowed."""
        expected_msg = re.escape("Dice component validation failed for: 2d6dl2")
        with self.assertRaisesRegex(InvalidRollFormula, expected_msg):
            DiceRoller.calculate_roll("2d6dl2")

    def test_drop_amount_greater_than_count(self):
        """Test dropping more dice than were rolled (e.g., 2d6dh3). This must be disallowed."""
        expected_msg = re.escape("Dice component validation failed for: 2d6dh3")
        with self.assertRaisesRegex(InvalidRollFormula, expected_msg):
            DiceRoller.calculate_roll("2d6dh3")

    def test_invalid_drop_keep_format(self):
        """Test incorrect casing for drop/keep notation (e.g., dL)."""
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: 'dL'")):
            DiceRoller.calculate_roll("4d6dL1")

    def test_invalid_drop_keep_suffix(self):
        """Test missing numerical suffix for drop/keep (e.g., dl)."""
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: 'dl'")):
            DiceRoller.calculate_roll("4d6dl")

    def test_invalid_drop_keep_suffix_2(self):
        """Test non-numerical suffix for drop/keep (e.g., dlx)."""
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: 'dlx'")):
            DiceRoller.calculate_roll("4d6dlx")


if __name__ == '__main__':
    unittest.main()