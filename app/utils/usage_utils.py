import json
from pathlib import Path

from fastapi import HTTPException

from app.utils.conf_utils import get_app_conf
from app import messages

FILE_PATH_USER_CONF = "user_conf.json"


def get_user_usage_bytes(user_path: Path) -> int:
    return sum(f.stat().st_size for f in user_path.rglob("*") if f.is_file())


def get_user_max_mb(user_path: Path, app: str) -> int | None:
    max_mb = get_app_conf(app).get("default_max_mb")
    user_conf_file = user_path / FILE_PATH_USER_CONF
    if user_conf_file.exists():
        with open(user_conf_file) as f:
            try:
                user_conf = json.load(f)
            except json.JSONDecodeError:
                user_conf = {}
        if "max_mb" in user_conf:
            max_mb = user_conf["max_mb"]
    return max_mb


def check_storage_limit(user_path: Path, app: str, incoming_bytes: int = 0):
    max_mb = get_user_max_mb(user_path, app)
    if max_mb is None:
        return
    if get_user_usage_bytes(user_path) + incoming_bytes > max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=messages.storageLimitExceeded)
