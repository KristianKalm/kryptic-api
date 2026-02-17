import hashlib
import json
import shutil

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.auth import Auth
from app.utils.auth_utils import verify_token, FILE_PATH_USER, CONST_PASSWORD
from app.utils.conf_utils import get_user_data_path
from app import messages

router = APIRouter()


class AccountDeleteRequest(BaseModel):
    password: str
    timestamp: str


@router.delete("/account", tags=["auth"])
def delete_account(req: AccountDeleteRequest, auth: Auth = Depends(verify_token)):
    user_path = get_user_data_path(auth.username, auth.app)
    user_file = user_path / FILE_PATH_USER
    with open(user_file) as r:
        stored_user = json.load(r)

    stored_pw = stored_user.get(CONST_PASSWORD)
    if hashlib.sha512((req.timestamp + stored_pw).encode()).hexdigest() != req.password:
        raise HTTPException(status_code=401, detail=messages.invalidCredentials)

    shutil.rmtree(user_path)

    return {"message": messages.accountDeleted}
