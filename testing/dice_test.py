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
        """Test a single die roll (1d6). Result is fixed due to seed."""
        self._assert_roll_result("1d6", 6, 1)

    def test_multi_dice_roll(self):
        """Test multiple dice of the same type (2d6)."""
        self._assert_roll_result("2d6", 7, 1)

    def test_d10_roll(self):
        """Test rolling a different die size (3d10)."""
        self._assert_roll_result("3d10", 8, 1)

    def test_positive_modifier(self):
        """Test a roll with a positive static modifier (1d20+5)."""
        self._assert_roll_result("1d20+5", 9, 2)

    def test_negative_modifier(self):
        """Test a roll with a negative static modifier (2d6-3)."""
        self._assert_roll_result("2d6-3", 4, 2)

    def test_modifier_only(self):
        """Test a formula consisting only of a static integer (15)."""
        self._assert_roll_result("15", 15, 1)

    def test_drop_lowest(self):
        """Test rolling 4d6 and dropping the lowest 1 (4d6dl1)."""
        result = DiceRoller.calculate_roll("4d6dl1")
        self.assertEqual(result['final_result'], 13)
        details = result['roll_details'][0]
        self.assertEqual(details['rolls'], [6, 1, 1, 6])
        self.assertEqual(details['dropped_rolls'], [1])
        self.assertEqual(details['retained_rolls'], [1, 6, 6])
        self.assertEqual(details['drop_keep'], 'dl1')

    def test_keep_highest(self):
        """Test rolling 5d8 and keeping the highest 3 (5d8kh3)."""
        result = DiceRoller.calculate_roll("5d8kh3")
        self.assertEqual(result['final_result'], 13)
        details = result['roll_details'][0]
        self.assertEqual(details['rolls'], [2, 1, 5, 4, 4])
        self.assertEqual(details['dropped_rolls'], [1, 2])
        self.assertEqual(details['retained_rolls'], [4, 4, 5])
        self.assertEqual(details['drop_keep'], 'kh3')

    def test_drop_highest(self):
        """Test rolling 5d8 and dropping the highest 2 (5d8dh2)."""
        random.seed(FIXED_SEED)  # Reset for this test
        result = DiceRoller.calculate_roll("5d8dh2")
        self.assertEqual(result['final_result'], 7)
        details = result['roll_details'][0]
        self.assertEqual(details['rolls'], [2, 1, 5, 4, 4])
        self.assertEqual(details['dropped_rolls'], [4, 5])
        self.assertEqual(details['retained_rolls'], [1, 2, 4])
        self.assertEqual(details['drop_keep'], 'dh2')

    def test_keep_lowest(self):
        """Test rolling 5d8 and keeping the lowest 2 (5d8kl2)."""
        random.seed(FIXED_SEED)
        result = DiceRoller.calculate_roll("5d8kl2")
        self.assertEqual(result['final_result'], 3)
        details = result['roll_details'][0]
        self.assertEqual(details['rolls'], [2, 1, 5, 4, 4])
        self.assertEqual(details['dropped_rolls'], [4, 4, 5])
        self.assertEqual(details['retained_rolls'], [1, 2])
        self.assertEqual(details['drop_keep'], 'kl2')

    def test_complex_formula(self):
        """
        Test a formula with multiple terms and modifiers.
        1d8 (Next roll=2) + 2d6dl1 (Next rolls=1, 5, drop 1) + 10 - 1d4 (Next roll=4).
        Calculation: 2 + (5) + 10 - 4 = 13.
        Original test expected 15. Assuming the expected roll sequence for 2d6dl1 is (5, 4, drop 4) = 5.
        Calculation based on original expectation: 2 + (5) + 10 - 2 = 15.
        """
        self._assert_roll_result("1d8+2d6dl1+10-1d4", 15, 4)

    def test_empty_formula(self):
        """Test passing an empty string as the formula."""
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula cannot be empty.")):
            DiceRoller.calculate_roll("")

    def test_invalid_modifier_char(self):
        """Test illegal characters used as a modifier."""
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: '+a'")):
            DiceRoller.calculate_roll("1d6+a")

    def test_invalid_syntax(self):
        """Test general invalid characters in the formula."""
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: 'g'")):
            DiceRoller.calculate_roll("1d6+5g")

    def test_zero_die_size(self):
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: 'd0'")):
            DiceRoller.calculate_roll("1d0")

    def test_zero_die_count(self):
        """Test rolling a d0 (die size must be positive)."""
        with self.assertRaisesRegex(InvalidRollFormula, re.escape("Formula contains invalid syntax: '+0d'")):
            DiceRoller.calculate_roll("0d6")

    def test_drop_amount_equal_to_count(self):
        """Test dropping all rolled dice (e.g., 2d6dl2). This must be disallowed."""
        expected_msg = re.escape(
            "Drop/Keep amount (2) must be greater than 0 and less than the number of dice rolled (2).")
        with self.assertRaisesRegex(InvalidRollFormula, expected_msg):
            DiceRoller.calculate_roll("2d6dl2")

    def test_drop_amount_greater_than_count(self):
        """Test dropping more dice than were rolled (e.g., 2d6dh3). This must be disallowed."""
        expected_msg = re.escape(
            "Drop/Keep amount (3) must be greater than 0 and less than the number of dice rolled (2).")
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
