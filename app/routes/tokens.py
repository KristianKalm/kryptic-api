import json

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.auth import Auth
from app.utils.auth_utils import verify_token, FILE_PATH_TOKENS, format_tokens_response
from app.utils.conf_utils import get_user_data_path
from app import messages

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/tokens", tags=["auth"])
@limiter.limit("30/minute")
def get_tokens(request: Request, auth: Auth = Depends(verify_token)):
    """
    Get all active authentication tokens for the current user.

    **Authentication Required**: Yes (via headers)

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
            },
            {
                "id": "uuid-token-id",
                "name": null,
                "created_at": 1705488900,
                "last_used_at": null
            }
        ]
    }
    ```

    **Response Fields**:
    - **tokens**: Array of token objects (token values are excluded for security)
      - **id**: Unique identifier for the token
      - **name**: PGP-encrypted name/label for the session/device (null if not set)
      - **created_at**: Unix timestamp (seconds since epoch) when the token was created
      - **last_used_at**: Unix timestamp when the token was last used (null if never used)

    **Behavior**:
    - Returns all active tokens for the authenticated user
    - Token values are NOT returned for security reasons
    - Includes optional name and creation timestamp for each token
    - Useful for session management and security auditing
    - Can help identify and revoke unknown sessions

    **Use Cases**:
    - View all active sessions with their names
    - Audit login history
    - Identify sessions by device/name for revocation
    - Session management dashboard

    **Error Responses**:
    - **401**: Invalid or missing authentication token
    - **404**: Tokens file not found (should not occur under normal circumstances)
    - **500**: Server error during token retrieval
    """
    user_path = get_user_data_path(auth.username, auth.app)
    tokens_file = user_path / FILE_PATH_TOKENS
    if tokens_file.exists():
        with open(tokens_file) as f:
            all_tokens = json.load(f)
            return format_tokens_response(all_tokens)
    raise HTTPException(status_code=404, detail=messages.somethingWentWrong)


@router.put("/token/name", tags=["auth"])
@limiter.limit("30/minute")
async def set_token_name(request: Request, auth: Auth = Depends(verify_token)):
    """
    Set or update the name of an authentication token.

    **Authentication Required**: Yes (via headers)

    **Request Body** (plain text):
    ```
    PGP-encrypted device name
    ```

    **Headers**: `Content-Type: text/plain`

    **Note**: The body is a PGP-encrypted string sent as plain text. The server stores
    it as-is without decryption. Only the currently authenticated token can be renamed.
    This endpoint exists because `token_name` is intentionally excluded from the
    `/login` request to avoid sending plaintext device names over the wire.

    **Typical flow after login**:
    1. POST /login → receive `token` and `token_id`
    2. Encrypt the device name with the user's PGP key client-side
    3. PUT /token/name → plain text body `<pgp-encrypted>`

    **Response**:
    ```json
    {
        "tokens": [...]
    }
    ```
    Returns the updated token list (same format as GET /tokens).

    **Error Responses**:
    - **401**: Invalid or missing authentication, or token id not found
    """
    user_path = get_user_data_path(auth.username, auth.app)
    tokens_file = user_path / FILE_PATH_TOKENS
    name = (await request.body()).decode("utf-8")
    if tokens_file.exists():
        with open(tokens_file) as f:
            tokens = json.load(f)
        for t in tokens:
            if t.get("id") == auth.token_id:
                t["name"] = name
                with open(tokens_file, "w") as f:
                    json.dump(tokens, f)
                return format_tokens_response(tokens)
    raise HTTPException(status_code=400, detail=messages.tokenNotFound)
