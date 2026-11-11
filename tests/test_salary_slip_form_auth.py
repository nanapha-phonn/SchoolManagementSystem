import unittest

from ui.transactions.salary_slip_form import SalarySlipForm


class SalarySlipFormAuthenticationTests(unittest.TestCase):

    def test_missing_user_is_rejected(self):
        with self.assertRaises(TypeError):
            SalarySlipForm(master=None)

    def test_empty_user_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "authenticated user is required",
        ):
            SalarySlipForm(master=None, user={})

    def test_invalid_user_type_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "authenticated user is required",
        ):
            SalarySlipForm(master=None, user="admin")


if __name__ == "__main__":
    unittest.main(verbosity=2)
