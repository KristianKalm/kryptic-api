from enum import StrEnum
from hashlib import sha1, sha512

from fastapi import Header, HTTPException
from app.models.auth import Auth
from app.utils.conf_utils import get_conf, get_user_data_path
import json

from app.utils.time_utils import get_utc_timestamp, get_utc_timestamp_ms
from app import messages

FILE_PATH_TOKENS = "tokens.json"
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
        raise HTTPException(status_code=401, detail=messages.appNotSupported)
    return x_app


def verify_token(
        x_auth_user: str = Header(..., alias=HEADER_USER, convert_underscores=False),
        x_auth_token: str = Header(..., alias=HEADER_TOKEN, convert_underscores=False),
        x_app: str = Header(..., alias=HEADER_APP, convert_underscores=False),
        x_timestamp: str = Header(..., alias=HEADER_TIMESTAMP, convert_underscores=False),
):
    verify_app(x_app)

    user_path = get_user_data_path(x_auth_user, x_app)
    tokens_file = user_path / FILE_PATH_TOKENS

    try:
        ts = int(x_timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail=messages.invalidToken)

    if abs(get_utc_timestamp_ms() - ts) > 3_600_000:
        raise HTTPException(status_code=408, detail=messages.timestampExpired)

    if tokens_file.exists():
        with open(tokens_file) as f:
            tokens = json.load(f)
            for item in tokens:
                token = sha512((x_timestamp + item["token"]).encode()).hexdigest()
                if x_auth_token == token:
                    if ts <= item.get("last_timestamp", 0):
                        raise HTTPException(status_code=408, detail=messages.timestampExpired)
                    item["last_timestamp"] = ts
                    item["last_used_at"] = get_utc_timestamp()
                    with open(tokens_file, "w") as f:
                        json.dump(tokens, f)
                    return Auth(username=x_auth_user, app=x_app, token_id=item["id"])

    raise HTTPException(status_code=401, detail=messages.invalidToken)


def format_tokens_response(tokens: list) -> dict:
    """
    Format tokens list to safe response format, excluding token values.

    Args:
        tokens: List of token objects from storage

    Returns:
        Dictionary with 'tokens' key containing sanitized token information
    """
    safe_tokens = []
    for token in tokens:
        safe_token = {
            "id": token.get("id"),
            "name": token.get("name", None),
            UserField.CREATED_AT: token.get(UserField.CREATED_AT),
            "last_used_at": token.get("last_used_at")
        }
        safe_tokens.append(safe_token)
    return {"tokens": safe_tokens}
