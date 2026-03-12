"""File upload API endpoints.

Handles PDF and LaTeX file uploads for the review pipeline.
Validates file types, enforces size limits, and stores files locally.

Files are uploaded *before* a review is started. The upload endpoint returns
file IDs which the client passes to ``POST /reviews`` (StartReviewRequest).
Until linked to a review, files exist in a temporary upload area.
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scriptum_ai.backend.api.deps import get_db, get_request_id
from scriptum_ai.backend.models.review import File
from scriptum_ai.backend.schemas.review import FileInfo, FileUploadResponse

router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_EXTENSIONS = {".pdf", ".tex", ".bib"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
UPLOAD_DIR = Path.home() / ".scriptum" / "uploads"


def _validate_extension(filename: str | None) -> str:
    """Validate file extension and return the normalised extension."""
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required.")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


def _file_type_from_ext(ext: str) -> str:
    """Map extension to a simple file type string."""
    return {".pdf": "pdf", ".tex": "latex", ".bib": "bibtex"}.get(ext, "unknown")


@router.post("/upload", response_model=list[FileUploadResponse])
async def upload_files(
    files: list[UploadFile],
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> list[FileUploadResponse]:
    """Upload one or more files for a review.

    Accepts PDF manuscripts (required) and optional LaTeX source files (.tex, .bib).
    Files are validated for type and size before storage.
    Returns a list of FileUploadResponse with file IDs to pass to start_review.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    results: list[FileUploadResponse] = []

    for upload in files:
        ext = _validate_extension(upload.filename)
        file_type = _file_type_from_ext(ext)

        # Read content to check size
        content = await upload.read()
        size_bytes = len(content)

        if size_bytes > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File '{upload.filename}' exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
            )

        if size_bytes == 0:
            raise HTTPException(status_code=400, detail=f"File '{upload.filename}' is empty.")

        # Generate file ID and create storage path
        file_id = uuid4()
        storage_dir = UPLOAD_DIR / str(file_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_path = storage_dir / upload.filename

        # Write to disk
        storage_path.write_bytes(content)

        # Create DB record (review_id will be set when start_review links them)
        # Use a placeholder review_id — will be updated by start_review.
        # Actually, File requires review_id (NOT NULL). We need a workaround.
        # Option: store without review_id by making it nullable temporarily.
        # Better option: create file records with a sentinel and update later.
        # Simplest: the File model already has review_id as non-nullable FK.
        # We'll create the record without committing to DB until start_review.
        # Instead, store metadata and let start_review create DB records.
        #
        # Decision: Create File record now with review_id=None.
        # The model ForeignKey has ondelete CASCADE but is non-nullable.
        # We need to handle this. Looking at the model, review_id is NOT nullable.
        # So we can't create File records before a review exists.
        #
        # Solution: Return file metadata (file_id, path) and defer DB insertion
        # to start_review. Store on disk now, DB record created in start_review.

        logger.info(
            "File uploaded: file_id={} filename={} size={}",
            file_id,
            upload.filename,
            size_bytes,
        )

        results.append(
            FileUploadResponse(
                file_id=file_id,
                filename=upload.filename or "",
                file_type=file_type,
                size_bytes=size_bytes,
            )
        )

    return results


@router.get("/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> FileInfo:
    """Get metadata for a previously uploaded file."""
    # Check DB first (file linked to a review)
    stmt = select(File).where(File.id == file_id)
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if file_record:
        return FileInfo(
            file_id=file_record.id,
            review_id=file_record.review_id,
            filename=file_record.filename or "",
            file_type=file_record.file_type or "",
            size_bytes=file_record.size_bytes or 0,
            created_at=file_record.created_at,
        )

    # Check disk (uploaded but not yet linked to a review)
    storage_dir = UPLOAD_DIR / str(file_id)
    if storage_dir.exists():
        # Find the file inside the directory
        stored_files = list(storage_dir.iterdir())
        if stored_files:
            f = stored_files[0]
            ext = f.suffix.lower()
            return FileInfo(
                file_id=file_id,
                review_id=None,
                filename=f.name,
                file_type=_file_type_from_ext(ext),
                size_bytes=f.stat().st_size,
                created_at=datetime.fromtimestamp(f.stat().st_mtime, tz=UTC),
            )

    raise HTTPException(status_code=404, detail="File not found.")


@router.delete("/{file_id}")
async def delete_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> dict:
    """Delete an uploaded file (only if not yet linked to a review)."""
    # Check if file is linked to a review
    stmt = select(File).where(File.id == file_id)
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if file_record:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a file that is linked to a review.",
        )

    # Remove from disk
    storage_dir = UPLOAD_DIR / str(file_id)
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
        return {"file_id": str(file_id), "status": "deleted"}

    raise HTTPException(status_code=404, detail="File not found.")
