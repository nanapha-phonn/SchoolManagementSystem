import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from config.settings import APP_TITLE
from ui.dashboard import DashboardWindow


class SchoolBrandingDashboardTests(unittest.TestCase):

    def setUp(self):
        self.label = Mock()

        self.dashboard = SimpleNamespace(
            user={"id": 1},
            brand_title=APP_TITLE,
            school_name_label=self.label,
            title=Mock(),
        )

    @patch(
        "ui.dashboard.get_school_profile",
        return_value={
            "id": 1,
            "name": "Demo International School",
        },
    )
    def test_01_use_configured_school_name(self, mock_get):
        DashboardWindow.refresh_school_branding(
            self.dashboard
        )

        mock_get.assert_called_once_with(actor_user_id=1)

        self.assertEqual(
            self.dashboard.brand_title,
            "Demo International School",
        )

        self.dashboard.title.assert_called_once_with(
            "Demo International School - Dashboard"
        )

        self.label.configure.assert_called_once_with(
            text="DEMO INTERNATIONAL SCHOOL"
        )

    @patch(
        "ui.dashboard.get_school_profile",
        return_value=None,
    )
    def test_02_use_default_name_without_school_profile(self, mock_get):
        DashboardWindow.refresh_school_branding(
            self.dashboard
        )

        self.assertEqual(
            self.dashboard.brand_title,
            APP_TITLE,
        )

        self.label.configure.assert_called_once_with(
            text=APP_TITLE.upper()
        )

    @patch(
        "ui.dashboard.get_school_profile",
        side_effect=RuntimeError("Database unavailable"),
    )
    def test_03_fallback_when_profile_cannot_be_loaded(self, mock_get):
        DashboardWindow.refresh_school_branding(
            self.dashboard
        )

        self.assertEqual(
            self.dashboard.brand_title,
            APP_TITLE,
        )

        self.dashboard.title.assert_called_once_with(
            f"{APP_TITLE} - Dashboard"
        )


if __name__ == "__main__":
    unittest.main()
