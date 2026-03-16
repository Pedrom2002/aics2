import hashlib
import re
import uuid

import httpx
from fastapi import HTTPException

from src.config import settings

# Only allow safe filename characters
_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and special characters."""
    # Strip any directory components
    name = filename.replace("\\", "/").split("/")[-1]
    # Replace unsafe characters with underscores
    name = _SAFE_FILENAME_RE.sub("_", name)
    # Prevent empty filenames
    return name or "unnamed.dem"


def generate_s3_key(org_id: uuid.UUID, filename: str) -> str:
    """Generate a unique S3 key for a demo file."""
    unique = uuid.uuid4().hex[:8]
    safe_name = _sanitize_filename(filename)
    return f"demos/{org_id}/{unique}_{safe_name}"


async def upload_to_minio(s3_key: str, file_data: bytes) -> str:
    """Upload file bytes to MinIO and return the checksum."""
    checksum = hashlib.sha256(file_data).hexdigest()

    url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{s3_key}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            response = await client.put(
                url,
                content=file_data,
                headers={"Content-Type": "application/octet-stream"},
                auth=(settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY),
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504, detail="Storage service timeout. Please try again."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail="Storage service error. Please try again."
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to connect to storage service."
        ) from exc

    return checksum


async def download_from_minio(s3_key: str) -> bytes:
    """Download file bytes from MinIO."""
    url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{s3_key}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            response = await client.get(
                url,
                auth=(settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY),
            )
            response.raise_for_status()
            return response.content
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Storage service timeout.") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Demo file not found in storage.") from exc
        raise HTTPException(status_code=502, detail="Storage service error.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to connect to storage service."
        ) from exc


async def delete_from_minio(s3_key: str) -> None:
    """Delete a file from MinIO."""
    url = f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{s3_key}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        response = await client.delete(
            url,
            auth=(settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY),
        )
        response.raise_for_status()


async def get_download_url(s3_key: str) -> str:
    """Get a presigned-style URL for downloading from MinIO."""
    return f"{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{s3_key}"
