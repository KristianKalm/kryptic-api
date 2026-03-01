import json
import os
from pathlib import Path

_config = None

FILE_PATH_CONF = "config/conf.json"


def load_conf(path=FILE_PATH_CONF):
    global _config
    with open(path) as f:
        _config = json.load(f)

    for app in _config.get("apps", []):
        os.makedirs(Path("appData") / app.get("name"), exist_ok=True)


def get_conf():
    return _config


BASE_PATH = Path(__file__).resolve().parent.parent.parent


def get_user_data_path(username, app):
    return BASE_PATH / "appData" / app / "users" / username
