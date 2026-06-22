import os
from typing import Optional
from fastapi import UploadFile, HTTPException, status

from app.utils.constants import ALLOWED_DOCUMENT_EXTENSIONS, MAX_FILE_SIZE


async def validate_file(file: UploadFile) -> None:
    """Validate uploaded file type and size."""
    # Check extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not supported. Allowed: {', '.join(ALLOWED_DOCUMENT_EXTENSIONS)}",
        )

    # Check size
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed ({MAX_FILE_SIZE // (1024 * 1024)} MB).",
        )