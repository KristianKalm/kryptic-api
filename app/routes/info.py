from fastapi import APIRouter
from app.utils.conf_utils import get_conf

router = APIRouter()


@router.get("/info", tags=["info"])
def info():
    """
    Get server configuration and information.

    **Authentication Required**: No (public endpoint)

    **Response**:
    ```json
    {
        "conf": {
            // Server configuration object
            // Contains various server settings and metadata
        }
    }
    ```

    **Behavior**:
    - Returns public server configuration information
    - No authentication required
    - Configuration is read from server settings

    **Use Cases**:
    - Check server capabilities before registering/logging in
    - Retrieve API version or supported features
    - Client configuration discovery

    **Error Responses**:
    - **500**: Server error during configuration retrieval
    """
    return {"conf": get_conf()}
