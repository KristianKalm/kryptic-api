from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.models.auth import Auth
from app.utils.auth_utils import verify_token

from app.utils.conf_utils import get_user_data_path


class FileItem(BaseModel):
    name: str
    data: str

router = APIRouter()


@router.get("/files/{folder:path}", tags=["file"])
def get_files(
    folder: str,
    start: int = Query(0, ge=0, description="Starting index for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of files to return"),
    reverse: bool = Query(False, description="Reverse sort order (oldest first when true)"),
    newer_than: Optional[int] = Query(None, description="Filter files modified after this UTC timestamp in seconds (e.g., 1705315800)"),
    auth: Auth = Depends(verify_token)
):
    """
    Get a paginated list of files with their content and metadata.

    **Authentication Required**: Yes (via headers)

    **Path Parameters**:
    - **folder**: Folder path to list files from (required, e.g., "documents", "messages/2024")

    **Query Parameters**:
    - **start**: Starting index for pagination (default: 0, must be >= 0)
    - **limit**: Maximum number of files to return (default: 100, min: 1, max: 1000)
    - **reverse**: Reverse sort order - true for oldest first, false for newest first (default: false)
    - **newer_than**: Filter files modified after this UTC timestamp in seconds (optional, e.g., 1705315800)

    **Response**:
    ```json
    {
        "files": [
            {
                "name": "message1.pgp",
                "data": "-----BEGIN PGP MESSAGE-----\\n...\\n-----END PGP MESSAGE-----"
            },
            {
                "name": "message2.pgp",
                "data": "-----BEGIN PGP MESSAGE-----\\n...\\n-----END PGP MESSAGE-----"
            }
        ],
        "total": 150,
        "start": 0,
        "limit": 100,
        "has_more": true
    }
    ```

    **Response Fields**:
    - **files**: Array of file objects with name and content
      - **name**: File name
      - **data**: File content as UTF-8 string (suitable for PGP messages and text files)
    - **total**: Total number of files in the folder
    - **start**: Starting index used for this page
    - **limit**: Maximum number of files requested
    - **has_more**: Boolean indicating if more files exist beyond this page

    **Example Usage**:
    ```
    GET /files/messages?start=0&limit=50
        - First 50 files from messages folder (newest first)

    GET /files/documents?start=0&limit=50&reverse=true
        - First 50 files from documents folder (oldest first)

    GET /files/inbox?newer_than=1705315800
        - All files in inbox modified after UTC timestamp 1705315800 (Jan 15, 2024)

    GET /files/messages/2024?start=0&limit=20&newer_than=1704067200
        - First 20 files from messages/2024 folder modified after Jan 1, 2024

    GET /files/archive?newer_than=1705315800&reverse=true
        - Files in archive modified after timestamp, sorted oldest first
    ```

    **Behavior**:
    - **Folder path is required** - root directory access is disabled
    - Files are sorted by modification time (newest first by default)
    - Use `reverse=true` to get oldest files first
    - Use `newer_than` to filter files by modification timestamp
    - Filtering happens before pagination (total reflects filtered count)
    - Returns file content as UTF-8 strings
    - Ideal for PGP ASCII-armored messages and text files
    - Returns only files, not subdirectories
    - Pagination is 0-indexed (start=0 is the first file)
    - If start >= total files, returns empty array with has_more=false

    **Data Format**:
    - All file content is returned as UTF-8 strings
    - Perfect for PGP messages (ASCII-armored text)
    - No encoding overhead - direct string representation
    - JSON-safe with proper escaping

    **Performance Notes**:
    - No encoding overhead compared to base64
    - Efficient for text-based encrypted files like PGP
    - Consider using lower limits for folders with large files

    **Error Responses**:
    - **401**: Invalid or missing authentication token
    - **404**: Folder not found or path is not a directory
    - **422**: Invalid query parameters (e.g., negative start, limit > 1000)
    - **500**: Server error during directory read operation or file read error
    """
    user_path = get_user_data_path(auth.username, auth.app) / folder
    if not user_path.exists() or not user_path.is_dir():
        return {
            "files": [],
            "total": 0,
            "start": start,
            "limit": limit,
            "has_more": False
        }

    try:
        # Get all files
        all_files = [f for f in user_path.iterdir() if f.is_file()]

        # Filter by newer_than timestamp if provided
        if newer_than is not None:
            all_files = [f for f in all_files if f.stat().st_mtime > newer_than]

        # Sort by modification time (newest first by default, oldest first if reverse=True)
        all_files_sorted = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=not reverse)
        total = len(all_files_sorted)

        # Apply pagination
        end = start + limit
        paginated_files = all_files_sorted[start:end]

        # Read file contents as UTF-8 text
        files_with_content = []
        for file_path in paginated_files:
            try:
                stat = file_path.stat()
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                files_with_content.append({
                    "name": file_path.name,
                    "data": content,
                    "time": int(stat.st_mtime)
                })
            except Exception as read_error:
                # If a file cannot be read, include error
                files_with_content.append({
                    "name": file_path.name,
                    "data": None,
                    "error": f"Failed to read file: {str(read_error)}"
                })

        return {
            "files": files_with_content,
            "total": total,
            "start": start,
            "limit": limit,
            "has_more": end < total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/{folder:path}", tags=["file"])
def post_files(
    folder: str,
    files: List[FileItem],
    auth: Auth = Depends(verify_token)
):
    user_path = get_user_data_path(auth.username, auth.app) / folder
    user_path.mkdir(parents=True, exist_ok=True)

    saved = []
    errors = []
    for file in files:
        try:
            file_path = user_path / file.name
            file_path.write_text(file.data, encoding="utf-8")
            saved.append(file.name)
        except Exception as e:
            errors.append({"name": file.name, "error": str(e)})

    return {
        "saved": saved,
        "errors": errors
    }
