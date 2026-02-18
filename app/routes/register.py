import hashlib

from fastapi import APIRouter, HTTPException, Depends, Request
import json
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.user import User, Encrypted
from app.routes.login import add_token
from app.utils.auth_utils import verify_app, FILE_PATH_USER, UserField
from app.utils.conf_utils import get_user_data_path
from app.utils.time_utils import get_utc_timestamp
from app import messages

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", tags=["auth"])
@limiter.limit("3/15minutes;10/day")
def register(request: Request, user: User, app=Depends(verify_app)):
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
        "token_name": "PGP"  // Optional, pgp encrypted session/device name
    }
    ```

    **Response**:
    ```json
    {
        "token": "uuid-token-string"
    }
    ```

    **Behavior**:
    - Creates a new user directory structure
    - Stores encrypted private key and seed
    - Stores public key in plain text
    - Automatically generates and returns an authentication token
    - Records account creation timestamp (UTC)

    **Error Responses**:
    - **400**: User already exists
    - **422**: Invalid request body or missing required fields
    - **500**: Server error during user creation
    """
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
