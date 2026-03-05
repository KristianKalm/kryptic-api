from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Header, Form, Query, Body, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from pydantic import BaseModel
from starlette.responses import PlainTextResponse

from app.models.auth import Auth
from app.utils.auth_utils import verify_token
from app.utils.conf_utils import get_user_data_path
from app.utils.usage_utils import check_storage_limit
from app import messages

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class TokenRequest(BaseModel):
    file_folder: str
    file_name: str


@router.post("/file/{folder}/{filename}", tags=["file"])
@limiter.limit("120/minute")
def save_file(
        request: Request,
        folder: str,
        filename: str,
        data: str = Body(..., media_type="text/plain"),
        auth: Auth = Depends(verify_token)
):
    """
    Save or overwrite a file in the user's storage.

    **Authentication Required**: Yes (via headers)

    **Path Parameters**:
    - **folder**: Folder path where the file should be saved (e.g., "documents", "data/reports")
    - **filename**: Name of the file to save (e.g., "report.txt", "data.json")

    **Request Body**:
    - Plain text content of the file (media type: text/plain)

    **Response**:
    ```json
    {
        "message": "File saved successfully"
    }
    ```

    **Behavior**:
    - Creates folder structure automatically if it doesn't exist
    - Overwrites existing files with the same name
    - All files are saved in the authenticated user's directory

    **Error Responses**:
    - **401**: Invalid or missing authentication token
    - **500**: Server error during file write operation
    """
    user_path = get_user_data_path(auth.username, auth.app)
    file_location = (user_path / folder / filename).resolve()
    if not str(file_location).startswith(str(user_path.resolve()) + "/"):
        raise HTTPException(status_code=400, detail=messages.invalidPath)

    check_storage_limit(user_path, auth.app, len(data.encode("utf-8")))

    file_location.parent.mkdir(parents=True, exist_ok=True)
    with open(file_location, "w", encoding="utf-8") as f:
        f.write(data)

    return {"message": messages.fileSaved}


@router.get("/file/{folder}/{filename}", tags=["file"])
@limiter.limit("120/minute")
def get_file(
        request: Request,
        folder: str,
        filename: str,
        auth: Auth = Depends(verify_token)
):
    """
    Retrieve the content of a specific file.

    **Authentication Required**: Yes (via headers)

    **Path Parameters**:
    - **folder**: Folder path where the file is located (e.g., "documents", "data/reports")
    - **filename**: Name of the file to retrieve (e.g., "report.txt", "data.json")

    **Response**:
    - Returns file content as plain text (Content-Type: text/plain)

    **Example Usage**:
    ```
    GET /file/documents/report.txt
    ```

    **Behavior**:
    - Returns the complete file content as plain text
    - File is read from the authenticated user's directory

    **Error Responses**:
    - **401**: Invalid or missing authentication token
    - **404**: File or folder not found
    - **500**: Server error during file read operation
    """
    user_path = get_user_data_path(auth.username, auth.app)
    file_path = (user_path / folder / filename).resolve()
    if not str(file_path).startswith(str(user_path.resolve()) + "/"):
        raise HTTPException(status_code=400, detail=messages.invalidPath)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=messages.fileNotFound)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return PlainTextResponse(content)


@router.delete("/file/{folder}/{filename}", tags=["file"])
@limiter.limit("60/minute")
def delete_file(
        request: Request,
        folder: str,
        filename: str,
        auth: Auth = Depends(verify_token)
):
    """
    Delete a specific file from the user's storage.

    **Authentication Required**: Yes (via headers)

    **Path Parameters**:
    - **folder**: Folder path where the file is located (e.g., "documents", "data/reports")
    - **filename**: Name of the file to delete (e.g., "report.txt", "data.json")

    **Response**:
    ```json
    {
        "message": "File deleted successfully"
    }
    ```

    **Example Usage**:
    ```
    DELETE /file/documents/report.txt
    ```

    **Behavior**:
    - Permanently deletes the specified file from the authenticated user's directory
    - Does not delete the folder, only the file
    - File cannot be recovered after deletion

    **Error Responses**:
    - **401**: Invalid or missing authentication token
    - **404**: File or folder not found
    - **500**: Server error during file deletion operation
    """
    user_path = get_user_data_path(auth.username, auth.app)
    file_path = (user_path / folder / filename).resolve()
    if not str(file_path).startswith(str(user_path.resolve()) + "/"):
        raise HTTPException(status_code=400, detail=messages.invalidPath)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=messages.fileNotFound)

    file_path.unlink()

    return {"message": messages.fileDeleted}
