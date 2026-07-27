from enum import StrEnum
from hashlib import sha1, sha512

from fastapi import Header, HTTPException
from app.models.auth import Auth
from app.utils.conf_utils import get_conf, get_user_data_path
from app.utils.json_store import edit_json, read_json

from app.utils.time_utils import get_utc_timestamp, get_utc_timestamp_ms
from app.utils.validation import is_valid_username
from app import messages

FILE_PATH_TOKENS = "tokens.json"
FILE_PATH_TOKEN_ACTIVITY = "token_activity.json"
FILE_PATH_USER = "user.json"


class UserField(StrEnum):
    TOKEN = "token"
    PASSWORD = "password"
    CREATED_AT = "created_at"
    SEED = "seed"
    PRIVATE_KEY = "private_key"
    PUBLIC_KEY = "public_key"

HEADER_APP = "xApp"
HEADER_USER = "xAuthUser"
HEADER_TOKEN = "xAuthToken"
HEADER_TIMESTAMP = "xTimestamp"


def verify_app(
        x_app: str = Header(..., alias=HEADER_APP, convert_underscores=False),
):
    if x_app not in [app.get("name") for app in get_conf().get("apps", [])]:
        raise HTTPException(status_code=400, detail=messages.appNotSupported)
    return x_app


def verify_token(
        x_auth_user: str = Header(..., alias=HEADER_USER, convert_underscores=False),
        x_auth_token: str = Header(..., alias=HEADER_TOKEN, convert_underscores=False),
        x_app: str = Header(..., alias=HEADER_APP, convert_underscores=False),
        x_timestamp: str = Header(..., alias=HEADER_TIMESTAMP, convert_underscores=False),
):
    verify_app(x_app)

    if not is_valid_username(x_auth_user):
        raise HTTPException(status_code=401, detail=messages.invalidToken)

    user_path = get_user_data_path(x_auth_user, x_app)
    tokens_file = user_path / FILE_PATH_TOKENS

    try:
        ts = int(x_timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail=messages.invalidToken)

    if abs(get_utc_timestamp_ms() - ts) > 3_600_000:
        raise HTTPException(status_code=408, detail=messages.timestampExpired)

    tokens = read_json(tokens_file, default=[])
    for item in tokens:
        token = sha512((x_timestamp + item["token"]).encode()).hexdigest()
        if x_auth_token == token:
            activity_file = user_path / FILE_PATH_TOKEN_ACTIVITY
            with edit_json(activity_file, default={}) as ref:
                entry = ref.data.setdefault(item["id"], {})
                last_timestamps = entry.get("last_timestamps", [])
                if last_timestamps and ts <= min(last_timestamps):
                    raise HTTPException(status_code=408, detail=messages.timestampExpired)
                if ts in last_timestamps:
                    raise HTTPException(status_code=408, detail=messages.timestampExpired)
                last_timestamps.append(ts)
                last_timestamps.sort()
                entry["last_timestamps"] = last_timestamps[-10:]
                entry["last_used_at"] = get_utc_timestamp()
            return Auth(username=x_auth_user, app=x_app, token_id=item["id"])

    raise HTTPException(status_code=401, detail=messages.invalidToken)


def format_tokens_response(tokens: list, activity: dict = None) -> dict:
    """
    Format tokens list to safe response format, excluding token values.

    Args:
        tokens: List of token objects from storage
        activity: Optional token id -> activity dict (see FILE_PATH_TOKEN_ACTIVITY),
            used to fill in last_used_at

    Returns:
        Dictionary with 'tokens' key containing sanitized token information
    """
    activity = activity or {}
    safe_tokens = []
    for token in tokens:
        entry = activity.get(token.get("id"), {})
        safe_token = {
            "id": token.get("id"),
            "name": token.get("name", None),
            UserField.CREATED_AT: token.get(UserField.CREATED_AT),
            "last_used_at": entry.get("last_used_at")
        }
        safe_tokens.append(safe_token)
    return {"tokens": safe_tokens}
