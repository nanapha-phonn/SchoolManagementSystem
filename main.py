from database.database import initialize_database
from services.auth_service import count_users

from ui.setup import SetupWindow
from ui.login import LoginWindow


def main():
    initialize_database()

    # First launch: create the administrator account.
    if count_users() == 0:
        setup_window = SetupWindow()
        setup_window.mainloop()

        # Stop if the user closes setup without creating an account.
        if not setup_window.setup_complete:
            return

    # Existing account: show the login screen.
    login_window = LoginWindow()
    login_window.mainloop()


if __name__ == "__main__":
    main()
