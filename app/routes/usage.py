from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.auth import Auth
from app.utils.auth_utils import verify_token
from app.utils.conf_utils import get_user_data_path
from app.utils.usage_utils import get_user_usage_bytes, get_user_max_mb

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/usage", tags=["info"])
@limiter.limit("30/minute")
def total_size(request: Request, auth: Auth = Depends(verify_token)):
    """
    Get the total storage usage for the authenticated user.

    **Authentication Required**: Yes (via headers)

    **Response**:
    ```json
    {
        "usage_size_bytes": 1048576
    }
    ```

    **Response Fields**:
    - **usage_size_bytes**: Total size in bytes of all files in the user's directory

    **Behavior**:
    - Calculates the total size of all files in the user's root directory
    - Only counts files directly in the root directory (using glob("*"))
    - Does not recursively count subdirectories
    - Size is reported in bytes

    **Example Conversions**:
    - 1024 bytes = 1 KB
    - 1048576 bytes = 1 MB
    - 1073741824 bytes = 1 GB

    **Use Cases**:
    - Display storage usage to users
    - Monitor quota limits
    - Storage analytics and reporting

    **Error Responses**:
    - **401**: Invalid or missing authentication token
    - **500**: Server error during size calculation
    """
    user_path = get_user_data_path(auth.username, auth.app)
    return {
        "usage_size_bytes": get_user_usage_bytes(user_path),
        "max_mb": get_user_max_mb(user_path, auth.app),
    }
