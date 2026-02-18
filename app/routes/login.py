import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
import json
import uuid

from pydantic import BaseModel

from app.models.auth import Auth
from app.models.user import User, Encrypted
from app.utils.auth_utils import verify_app, FILE_PATH_TOKENS, FILE_PATH_USER, UserField, verify_token, format_tokens_response
from app.utils.conf_utils import get_user_data_path
from app.utils.ota_utils import verify_ota_pin
from app.utils.time_utils import get_utc_timestamp, get_utc_timestamp_ms
from app import messages

router = APIRouter()

FILE_LOGIN_ATTEMPTS = "login_attempts.json"
_MAX_15MIN = 3
_MAX_24H = 20
_WINDOW_15MIN_MS = 15 * 60 * 1000
_WINDOW_24H_MS = 24 * 60 * 60 * 1000


def check_and_record_login_attempt(user_path: Path):
    now = get_utc_timestamp_ms()
    attempts_file = user_path / FILE_LOGIN_ATTEMPTS

    attempts = []
    if attempts_file.exists():
        with open(attempts_file) as f:
            attempts = json.load(f)

    cutoff_24h = now - _WINDOW_24H_MS
    attempts = [ts for ts in attempts if ts > cutoff_24h]

    if len([ts for ts in attempts if ts > now - _WINDOW_15MIN_MS]) >= _MAX_15MIN:
        raise HTTPException(status_code=429, detail=messages.tooManyRequests)

    if len(attempts) >= _MAX_24H:
        raise HTTPException(status_code=429, detail=messages.tooManyRequests)

    attempts.append(now)
    with open(attempts_file, "w") as f:
        json.dump(attempts, f)


@router.post("/login", tags=["auth"])
def create_token(user: User, app=Depends(verify_app)):
    """
    Authenticate a user and create a new session token.

    **Authentication Required**: No (public endpoint)

    **Headers Required**:
    - **xApp**: Application name/identifier

    **Request Body** (JSON):
    ```json
    {
        "username": "john_doe",
        "password": "sha512_hash_of_timestamp_plus_stored_password",
        "timestamp": "2024-01-15T10:30:00Z",
        "pin": "123456"  // Optional, required only if OTA is enabled
    }
    ```

    **Note**: `token_name` is not accepted at login. To name the session, use `PUT /token/name`
    with a PGP-encrypted value after a successful login.

    **Note**: The created token will have a Unix timestamp (seconds since epoch) stored internally.

    **Response**:
    ```json
    {
        "token": "uuid-token-string",
        "private_key": {
            "ciphertext": "encrypted_private_key",
            "iv": "initialization_vector",
            "salt": "salt_value"
        },
        "seed": {
            "ciphertext": "encrypted_seed",
            "iv": "initialization_vector",
            "salt": "salt_value"
        },
        "public_key": "user_public_key_string"
    }
    ```

    **Authentication Flow**:
    1. Password is verified using SHA512(timestamp + stored_password)
    2. If OTA (One-Time Authentication) is enabled, PIN is verified
    3. New session token is generated and stored
    4. User's encrypted keys and seed are returned

    **Behavior**:
    - Creates a new authentication token for the session
    - Returns encrypted private key and seed for client-side decryption
    - Supports optional OTA PIN for additional security
    - Token is stored and can be used for subsequent authenticated requests

    **Error Responses**:
    - **400**: Invalid credentials
    - **403**: Wrong PIN, or PIN required but not provided
    - **404**: User not found
    - **422**: Invalid request body or missing required fields
    - **500**: Server error during authentication
    """
    user_path = get_user_data_path(user.username, app)
    user_file = user_path / FILE_PATH_USER
    if not user_file.exists():
        raise HTTPException(status_code=404, detail=messages.userNotFound)

    check_and_record_login_attempt(user_path)

    with open(user_file) as f:
        user_json = json.load(f)
        stored_pw = user_json.get(UserField.PASSWORD)
        stored_ota = user_json.get("ota")

    if stored_ota is not None:
        if user.pin is None:
            raise HTTPException(status_code=403, detail=messages.pinIsRequired)
        if not verify_ota_pin(stored_ota, user.pin):
            raise HTTPException(status_code=403, detail=messages.wrongPin)

    if user.timestamp is None or abs(get_utc_timestamp_ms() - user.timestamp) > 3_600_000:
        raise HTTPException(status_code=408, detail=messages.timestampExpired)

    if user.timestamp <= user_json.get("last_login_timestamp", 0):
        raise HTTPException(status_code=408, detail=messages.timestampExpired)

    if hashlib.sha512((str(user.timestamp) + stored_pw).encode()).hexdigest() != user.password:
        raise HTTPException(status_code=400, detail=messages.invalidCredentials)

    user_json["last_login_timestamp"] = user.timestamp
    with open(user_file, "w") as f:
        json.dump(user_json, f)

    unhashed_token, token_id = add_token(user_path)
    return {
        UserField.TOKEN: unhashed_token,
        "token_id": token_id,
        UserField.PRIVATE_KEY: Encrypted.model_validate_json(user_json.get(UserField.PRIVATE_KEY)),
        UserField.SEED: Encrypted.model_validate_json(user_json.get(UserField.SEED)),
        UserField.PUBLIC_KEY: user_json.get(UserField.PUBLIC_KEY),
    }


def add_token(user_path: Path, token_name: str = None):
    unhashed_token = str(uuid.uuid4())
    token_id = str(uuid.uuid4())
    token = {
        "id": token_id,
        UserField.TOKEN: unhashed_token,
        UserField.CREATED_AT: get_utc_timestamp()
    }
    if token_name:
        token["name"] = token_name
    tokens_file = user_path / FILE_PATH_TOKENS
    tokens = []
    if tokens_file.exists():
        with open(tokens_file) as f:
            tokens = json.load(f)
    tokens.append(token)
    with open(tokens_file, "w") as f:
        json.dump(tokens, f)
    return unhashed_token, token_id


class TokenRequest(BaseModel):
    id: str


@router.delete("/token", tags=["auth"])
def delete_token(token: TokenRequest, auth: Auth = Depends(verify_token)):
    """
    Delete (logout) a specific authentication token by ID.

    **Authentication Required**: Yes (via headers)

    **Request Body** (JSON):
    ```json
    {
        "id": "uuid-token-id-to-delete"
    }
    ```

    **Response**:
    ```json
    {
        "tokens": [
            {
                "id": "uuid-token-id",
                "name": "My iPhone",
                "created_at": 1705315800,
                "last_used_at": 1705320300
            },
            {
                "id": "uuid-token-id",
                "name": "Work Laptop",
                "created_at": 1705402200,
                "last_used_at": 1705402200
            }
        ]
    }
    ```

    **Response Fields**:
    - **tokens**: Array of remaining token objects after deletion (token values are excluded for security)
      - **id**: Unique identifier for the token
      - **name**: Name/label for the session/device (null if not set)
      - **created_at**: Unix timestamp (seconds since epoch) when the token was created
      - **last_used_at**: Unix timestamp when the token was last used (null if never used)

    **Behavior**:
    - Removes the specified token from the user's active tokens list
    - Identifies token by ID only (mandatory field)
    - Token will no longer be valid for authentication after deletion
    - Returns the updated list of remaining active tokens in the same format as /tokens endpoint
    - Can be used to log out a specific session
    - Requires valid authentication to delete a token

    **Use Cases**:
    - Logout from current session
    - Revoke access from a specific device/session
    - Security cleanup after suspected token compromise

    **Error Responses**:
    - **400**: Token not found or invalid authentication
    - **422**: Invalid request body or missing id
    - **500**: Server error during token deletion
    """
    user_path = get_user_data_path(auth.username, auth.app)
    tokens_file = user_path / FILE_PATH_TOKENS
    if tokens_file.exists():
        with open(tokens_file) as f:
            tokens = json.load(f)
            # Find token by id
            found = any(t.get("id") == token.id for t in tokens)
            if found:
                updated_tokens = [t for t in tokens if t.get("id") != token.id]
                with open(tokens_file, "w") as f:
                    json.dump(updated_tokens, f)
                    return format_tokens_response(updated_tokens)
    raise HTTPException(status_code=400, detail=messages.tokenNotFound)
