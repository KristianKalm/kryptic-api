#!/usr/bin/env python3
"""
Admin script to set a user's max storage limit.

Usage:
    python set_user_max_mb.py <app> <username> <mb>

Example:
    python set_user_max_mb.py Mylif john_doe 500
"""

import json
import sys
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent
USER_CONF_FILE = "user_conf.json"
USER_FILE = "user.json"


def get_user_path(app: str, username: str) -> Path:
    return BASE_PATH / "appData" / app / "users" / username


def set_user_max_mb(app: str, username: str, mb: int):
    user_path = get_user_path(app, username)

    if not (user_path / USER_FILE).exists():
        print(f"Error: user '{username}' not found in app '{app}'")
        sys.exit(1)

    user_conf_file = user_path / USER_CONF_FILE
    conf = {}
    if user_conf_file.exists():
        with open(user_conf_file) as f:
            try:
                conf = json.load(f)
            except json.JSONDecodeError:
                conf = {}

    conf["max_mb"] = mb

    with open(user_conf_file, "w") as f:
        json.dump(conf, f)

    print(f"Set max_mb={mb} for user '{username}' in app '{app}'")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python set_user_max_mb.py <app> <username> <mb>")
        sys.exit(1)

    app_name = sys.argv[1]
    username = sys.argv[2]

    try:
        mb = int(sys.argv[3])
        if mb <= 0:
            raise ValueError
    except ValueError:
        print("Error: mb must be a positive integer")
        sys.exit(1)

    set_user_max_mb(app_name, username, mb)
