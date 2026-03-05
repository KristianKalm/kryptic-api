import hashlib

from fastapi import APIRouter, HTTPException, Depends, Request
import json
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.user import RegisterRequest, Encrypted
from app.routes.login import add_token
from app.utils.auth_utils import verify_app, FILE_PATH_USER, UserField
from app.utils.captcha_utils import create_captcha, verify_captcha
from app.utils.conf_utils import get_user_data_path
from app.utils.time_utils import get_utc_timestamp
from app import messages

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/register", tags=["auth"])
@limiter.limit("20/minute")
def get_register_captcha(request: Request, app=Depends(verify_app)):
    """
    Get a CAPTCHA challenge required for registration.

    **Authentication Required**: No (public endpoint)

    **Headers Required**:
    - **xApp**: Application name/identifier

    **Response**:
    ```json
    {
        "captcha_id": "uuid",
        "captcha_image": "base64-encoded PNG image"
    }
    ```

    The `captcha_id` and the solved `captcha_text` must be included in the
    POST /register request body. The captcha expires after 5 minutes.
    """
    captcha_id, captcha_image = create_captcha()
    return {"captcha_id": captcha_id, "captcha_image": captcha_image}


@router.post("/register", tags=["auth"])
@limiter.limit("3/15minutes;10/day")
def register(request: Request, user: RegisterRequest, app=Depends(verify_app)):
    """
    Register a new user account.

    **Authentication Required**: No (public endpoint)

    **Headers Required**:
    - **xApp**: Application name/identifier

    **Request Body** (JSON):
    ```json
    {
        "username": "john_doe",
        "password": "hashed_password",
        "public_key": "user_public_key_string",
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
        "token_name": "PGP",
        "captcha_id": "uuid-from-get-register",
        "captcha_text": "ABCD"
    }
    ```

    **Response**:
    ```json
    {
        "token": "uuid-token-string"
    }
    ```

    **Error Responses**:
    - **400**: User already exists or invalid/expired captcha
    - **422**: Invalid request body or missing required fields
    - **500**: Server error during user creation
    """
    if not verify_captcha(user.captcha_id, user.captcha_text):
        raise HTTPException(status_code=406, detail=messages.invalidCaptcha)

    user_path = get_user_data_path(user.username, app)
    if not user_path.exists():
        user_path.mkdir(parents=True)
    user_file = user_path / FILE_PATH_USER
    if user_file.exists():
        raise HTTPException(status_code=400, detail=messages.userAlreadyExists)
    with open(user_file, "w") as f:
        data = {
            UserField.PASSWORD: user.password,
            UserField.CREATED_AT: get_utc_timestamp(),
            UserField.PRIVATE_KEY: user.private_key.model_dump_json(),
            UserField.PUBLIC_KEY: user.public_key,
            UserField.SEED: user.seed.model_dump_json(),
        }
        json.dump(data, f)
    unhashed_token, token_id = add_token(user_path, user.token_name)
    return {"token": unhashed_token, "token_id": token_id}
