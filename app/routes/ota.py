import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.auth import Auth
from app.utils.auth_utils import verify_token, FILE_PATH_USER, UserField

from app.utils.conf_utils import get_user_data_path
from app.utils.ota_utils import generate_ota_key, generate_ota_pin, verify_ota_pin
from app import messages

router = APIRouter()


@router.get("/ota", tags=["auth"])
def get_ota_key(auth: Auth = Depends(verify_token)):
    """
    Generate a temporary OTA (One-Time Authentication) key for setup.

    **Authentication Required**: Yes (via headers)

    **Response**:
    ```json
    {
        "ota": "base32-encoded-secret-key"
    }
    ```

    **Response Fields**:
    - **ota**: Base32-encoded secret key for OTA setup (typically used with authenticator apps)

    **Behavior**:
    - Generates a new OTA secret key
    - Stores it as a temporary key in the user's profile
    - Key remains temporary until confirmed via POST /ota
    - Can be used to generate QR code for authenticator apps

    **OTA Setup Flow**:
    1. Call GET /ota to generate a temporary key
    2. Display key or QR code to user
    3. User adds key to authenticator app (Google Authenticator, Authy, etc.)
    4. User submits PIN from authenticator app
    5. Call POST /ota with PIN to confirm and activate OTA

    **Use Cases**:
    - Enable two-factor authentication (2FA)
    - Add extra security layer to user accounts
    - Generate TOTP (Time-based One-Time Password) secrets

    **Error Responses**:
    - **401**: Invalid or missing authentication token
    - **500**: Server error during OTA key generation
    """
    user_path = get_user_data_path(auth.username, auth.app)
    user_file = user_path / FILE_PATH_USER
    with open(user_file) as r:
        stored_user = json.load(r)
    if stored_user.get("ota"):
        raise HTTPException(status_code=400, detail=messages.otaAlreadySetUp)
    ota_key = generate_ota_key()
    stored_user["temp_ota"] = ota_key
    with open(user_file, "w") as w:
        json.dump(stored_user, w)
    return {"ota": ota_key}


class OtaRequest(BaseModel):
    pin: str


@router.post("/ota", tags=["auth"])
def save_ota_key(ota_code: OtaRequest, auth: Auth = Depends(verify_token)):
    """
    Confirm and activate OTA (One-Time Authentication) by verifying the PIN.

    **Authentication Required**: Yes (via headers)

    **Request Body** (JSON):
    ```json
    {
        "pin": "123456"
    }
    ```

    **Request Fields**:
    - **pin**: 6-digit PIN from authenticator app (generated using the temporary OTA key)

    **Response**:
    ```json
    {
        "message": "success"
    }
    ```

    **Behavior**:
    - Verifies the PIN against the temporary OTA key from GET /ota
    - If PIN is correct, activates OTA by moving temp_ota to ota
    - Once activated, future logins will require the OTA PIN
    - Deletes the temporary OTA key after successful activation

    **OTA Setup Flow**:
    1. GET /ota - Generate temporary key
    2. User adds key to authenticator app
    3. POST /ota - Submit PIN to confirm setup
    4. OTA is now active for this account

    **Security Notes**:
    - Must call GET /ota first to generate a temporary key
    - PIN must be current (time-based, typically valid for 30 seconds)
    - Only one OTA setup can be in progress at a time
    - Previous OTA settings are replaced when new OTA is activated

    **Use Cases**:
    - Complete 2FA setup process
    - Verify authenticator app configuration
    - Activate enhanced account security

    **Error Responses**:
    - **400**: No ongoing OTA setup (must call GET /ota first) or wrong PIN
    - **401**: Invalid or missing authentication token
    - **422**: Invalid request body
    - **500**: Server error during OTA activation
    """
    user_path = get_user_data_path(auth.username, auth.app)
    user_file = user_path / FILE_PATH_USER
    with open(user_file) as r:
        stored_user = json.load(r)
        temp_ota = stored_user.get("temp_ota")
        if temp_ota is None:
            raise HTTPException(status_code=400, detail=messages.otaNoOngoingSetup)
        if verify_ota_pin(temp_ota, ota_code.pin):
            stored_user["ota"] = stored_user["temp_ota"]
            del stored_user["temp_ota"]
            with open(user_file, "w") as w:
                json.dump(stored_user, w)
                return {"message": messages.otaConfirmed}

    raise HTTPException(status_code=400, detail=messages.otaWrongPin)


class OtaDeleteRequest(BaseModel):
    password: str
    timestamp: str


@router.delete("/ota", tags=["auth"])
def delete_ota_key(req: OtaDeleteRequest, auth: Auth = Depends(verify_token)):
    user_path = get_user_data_path(auth.username, auth.app)
    user_file = user_path / FILE_PATH_USER
    with open(user_file) as r:
        stored_user = json.load(r)

    if not stored_user.get("ota"):
        raise HTTPException(status_code=400, detail=messages.otaNotSetUp)

    stored_pw = stored_user.get(UserField.PASSWORD)
    if hashlib.sha512((req.timestamp + stored_pw).encode()).hexdigest() != req.password:
        raise HTTPException(status_code=401, detail=messages.invalidCredentials)

    del stored_user["ota"]
    with open(user_file, "w") as w:
        json.dump(stored_user, w)

    return {"message": messages.otaRemoved}
