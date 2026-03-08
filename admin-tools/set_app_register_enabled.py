#!/usr/bin/env python3
"""
Admin script to set an app's register_enabled flag.

Usage:
    python set_app_register_enabled.py <app> <true|false>

Example:
    python set_app_register_enabled.py Mylif false
"""

import json
import sys
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent
CONF_FILE = BASE_PATH / "appData" / "conf.json"


def set_app_register_enabled(app: str, enabled: bool):
    if not CONF_FILE.exists():
        print(f"Error: conf.json not found at {CONF_FILE}")
        sys.exit(1)

    with open(CONF_FILE) as f:
        conf = json.load(f)

    apps = conf.get("apps", [])
    for entry in apps:
        if entry.get("name") == app:
            entry["register_enabled"] = enabled
            with open(CONF_FILE, "w") as f:
                json.dump(conf, f, indent=2)
            print(f"Set register_enabled={enabled} for app '{app}'")
            return

    print(f"Error: app '{app}' not found in conf.json")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python set_app_register_enabled.py <app> <true|false>")
        sys.exit(1)

    app_name = sys.argv[1]
    raw = sys.argv[2].lower()

    if raw not in ("true", "false"):
        print("Error: value must be 'true' or 'false'")
        sys.exit(1)

    set_app_register_enabled(app_name, raw == "true")
