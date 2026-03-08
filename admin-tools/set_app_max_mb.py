#!/usr/bin/env python3
"""
Admin script to set an app's default max storage limit.

Usage:
    python set_app_max_mb.py <app> <mb>

Example:
    python set_app_max_mb.py Mylif 500
"""

import json
import sys
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent
CONF_FILE = BASE_PATH / "appData" / "conf.json"


def set_app_max_mb(app: str, mb: int):
    if not CONF_FILE.exists():
        print(f"Error: conf.json not found at {CONF_FILE}")
        sys.exit(1)

    with open(CONF_FILE) as f:
        conf = json.load(f)

    apps = conf.get("apps", [])
    for entry in apps:
        if entry.get("name") == app:
            entry["default_max_mb"] = mb
            with open(CONF_FILE, "w") as f:
                json.dump(conf, f, indent=2)
            print(f"Set default_max_mb={mb} for app '{app}'")
            return

    print(f"Error: app '{app}' not found in conf.json")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python set_app_max_mb.py <app> <mb>")
        sys.exit(1)

    app_name = sys.argv[1]

    try:
        mb = int(sys.argv[2])
        if mb <= 0:
            raise ValueError
    except ValueError:
        print("Error: mb must be a positive integer")
        sys.exit(1)

    set_app_max_mb(app_name, mb)
