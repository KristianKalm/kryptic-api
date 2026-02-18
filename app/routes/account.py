import hashlib
import json
import shutil

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.auth import Auth
from app.models.user import Encrypted
from app.utils.auth_utils import verify_token, FILE_PATH_USER, UserField
from app.utils.conf_utils import get_user_data_path
from app import messages

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class AccountDeleteRequest(BaseModel):
    password: str
    timestamp: str


class AccountUpdateRequest(BaseModel):
    old_password: str
    timestamp: str
    password: str
    public_key: str
    seed: Encrypted


@router.put("/account", tags=["auth"])
@limiter.limit("3/15minutes;10/day")
def update_account(request: Request, req: AccountUpdateRequest, auth: Auth = Depends(verify_token)):
    """
    Change account password and re-encrypted key material.

    **Authentication Required**: Yes (token auth)

    **Headers Required**:
    - **xApp**: Application name/identifier
    - **xAuthUser**: Username
    - **xAuthToken**: SHA512(xTimestamp + token)
    - **xTimestamp**: Current UTC timestamp in milliseconds

    **Request Body** (JSON):
    ```json
    {
        "old_password": "sha512(timestamp + stored_password)",
        "timestamp": "utc_timestamp_ms_used_for_old_password",
        "password": "new_hashed_password",
        "public_key": "new_public_key_string",
        "seed": {
            "ciphertext": "encrypted_seed",
            "iv": "initialization_vector",
            "salt": "salt_value"
        }
    }
    ```

    **Response**:
    ```json
    {
        "message": "account_updated"
    }
    ```

    **Behavior**:
    - Verifies old password using SHA512(timestamp + stored_password)
    - Replaces stored password, public key, and seed

    **Error Responses**:
    - **400**: Wrong old password
    - **408**: Timestamp expired
    - **422**: Invalid request body or missing required fields
    - **429**: Rate limit exceeded (3/15min, 10/day)
    """
    user_path = get_user_data_path(auth.username, auth.app)
    user_file = user_path / FILE_PATH_USER
    with open(user_file) as r:
        stored_user = json.load(r)

    stored_pw = stored_user.get(UserField.PASSWORD)
    if hashlib.sha512((req.timestamp + stored_pw).encode()).hexdigest() != req.old_password:
        raise HTTPException(status_code=400, detail=messages.invalidCredentials)

    stored_user[UserField.PASSWORD] = req.password
    stored_user[UserField.PUBLIC_KEY] = req.public_key
    stored_user[UserField.SEED] = req.seed.model_dump_json()

    with open(user_file, "w") as f:
        json.dump(stored_user, f)

    return {"message": messages.accountUpdated}


@router.delete("/account", tags=["auth"])
def delete_account(req: AccountDeleteRequest, auth: Auth = Depends(verify_token)):
    user_path = get_user_data_path(auth.username, auth.app)
    user_file = user_path / FILE_PATH_USER
    with open(user_file) as r:
        stored_user = json.load(r)

    stored_pw = stored_user.get(UserField.PASSWORD)
    if hashlib.sha512((req.timestamp + stored_pw).encode()).hexdigest() != req.password:
        raise HTTPException(status_code=400, detail=messages.invalidCredentials)

    shutil.rmtree(user_path)

    return {"message": messages.accountDeleted}
