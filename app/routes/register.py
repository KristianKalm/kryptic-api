import hashlib

from fastapi import APIRouter, HTTPException, Depends
import json
from app.models.user import User, Encrypted
from app.routes.login import add_token
from app.utils.auth_utils import verify_app, FILE_PATH_USER, CONST_PASSWORD, CONST_CREATED_AT, CONST_PRIVATE_KEY, \
    CONST_SEED, CONST_PUBLIC_KEY
from app.utils.conf_utils import get_user_data_path
from app.utils.time_utils import get_utc_timestamp
from app import messages

router = APIRouter()


@router.post("/register", tags=["auth"])
def register(user: User, app=Depends(verify_app)):
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
        "token_name": "My Device"  // Optional, name for initial session/device
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
            CONST_PASSWORD: user.password,
            CONST_CREATED_AT: get_utc_timestamp(),
            CONST_PRIVATE_KEY: user.private_key.model_dump_json(),
            CONST_PUBLIC_KEY: user.public_key,
            CONST_SEED: user.seed.model_dump_json(),
        }
        json.dump(data, f)
    unhashed_token, token_id = add_token(user_path, user.token_name)
    return {"token": unhashed_token, "token_id": token_id}
