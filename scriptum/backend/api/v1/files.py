"""File upload API endpoints.

Handles PDF and LaTeX file uploads for the review pipeline.
Validates file types, enforces size limits, and stores files locally.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, UploadFile

from backend.api.deps import get_request_id

router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_EXTENSIONS = {".pdf", ".tex", ".bib"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/upload")
async def upload_files(
    files: list[UploadFile],
    request_id: str = Depends(get_request_id),
) -> dict:
    """Upload one or more files for a review.

    Accepts PDF manuscripts (required) and optional LaTeX source files (.tex, .bib).
    Files are validated for type and size before storage.
    """
    # TODO: Validate each file type against ALLOWED_EXTENSIONS
    # TODO: Validate file size against MAX_FILE_SIZE_BYTES
    # TODO: Store files in ~/.scriptum/uploads/{review_id}/
    # TODO: Create file records in DB
    file_ids = []
    uploaded = []
    for file in files:
        file_id = uuid4()
        file_ids.append(str(file_id))
        uploaded.append({
            "file_id": str(file_id),
            "filename": file.filename,
            "content_type": file.content_type,
            "status": "accepted",
        })

    return {
        "file_ids": file_ids,
        "files": uploaded,
        "message": f"{len(files)} file(s) uploaded successfully.",
    }


@router.get("/{file_id}")
async def get_file_info(
    file_id: UUID,
    request_id: str = Depends(get_request_id),
) -> dict:
    """Get metadata for a previously uploaded file."""
    # TODO: Fetch file record from DB
    # TODO: Return 404 if not found
    return {
        "file_id": str(file_id),
        "filename": None,
        "file_type": None,
        "size_bytes": None,
        "status": "not_found",
        "message": "File lookup not yet implemented.",
    }
