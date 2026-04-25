#!/usr/bin/env python3
"""
Admin script to clear login attempts for a user.

Usage:
    python clear_login_attempts.py <app> <username>

Example:
    python clear_login_attempts.py MyApp john_doe
"""

import sys
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent
USER_FILE = "user.json"
LOGIN_ATTEMPTS_FILE = "login_attempts.json"


def get_user_path(app: str, username: str) -> Path:
    return BASE_PATH / "appData" / app / "users" / username


def clear_login_attempts(app: str, username: str):
    user_path = get_user_path(app, username)

    if not (user_path / USER_FILE).exists():
        print(f"Error: user '{username}' not found in app '{app}'")
        sys.exit(1)

    attempts_file = user_path / LOGIN_ATTEMPTS_FILE

    if not attempts_file.exists():
        print(f"No login attempts file found for user '{username}' in app '{app}'")
        return

    attempts_file.unlink()
    print(f"Cleared login attempts for user '{username}' in app '{app}'")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python clear_login_attempts.py <app> <username>")
        sys.exit(1)

    app_name = sys.argv[1]
    username = sys.argv[2]

    clear_login_attempts(app_name, username)
