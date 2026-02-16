from fastapi import APIRouter, Depends

from app.models.auth import Auth
from app.utils.auth_utils import verify_token, verify_app
from app.utils.conf_utils import get_user_data_path, get_conf

router = APIRouter()


@router.get("/usage", tags=["info"])
def total_size(auth: Auth = Depends(verify_token)):
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
    total = sum(f.stat().st_size for f in user_path.rglob("*") if f.is_file())
    conf = get_conf()
    default_max_mb = next((a["default_max_mb"] for a in conf.get("apps", []) if a["name"] == auth.app), None)
    return {"usage_size_bytes": total, "default_max_mb": default_max_mb}
