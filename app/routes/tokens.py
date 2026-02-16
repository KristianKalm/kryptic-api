import json

from fastapi import APIRouter, Depends, HTTPException

from app.models.auth import Auth
from app.utils.auth_utils import verify_token, FILE_PATH_TOKENS, format_tokens_response
from app.utils.conf_utils import get_user_data_path
from app import messages

router = APIRouter()


@router.get("/tokens", tags=["auth"])
def get_tokens(auth: Auth = Depends(verify_token)):
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
      - **name**: Name/label for the session/device (null if not set)
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
