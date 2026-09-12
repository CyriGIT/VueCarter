from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from backend_etl.core.config import settings


ALLOWED_FILE_TYPES = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".gif": {"image/gif"},
    ".webp": {"image/webp"},
    ".mp3": {"audio/mpeg"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".ogg": {"audio/ogg", "video/ogg"},
    ".mp4": {"video/mp4"},
    ".webm": {"video/webm"},
    ".mov": {"video/quicktime"},
    ".txt": {"text/plain"},
    ".csv": {"text/csv", "application/vnd.ms-excel"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
}


def _signature_matches(extension: str, header: bytes) -> bool:
    signatures = {
        ".pdf": (b"%PDF-",),
        ".png": (b"\x89PNG\r\n\x1a\n",),
        ".jpg": (b"\xff\xd8\xff",),
        ".jpeg": (b"\xff\xd8\xff",),
        ".gif": (b"GIF87a", b"GIF89a"),
        ".webp": (b"RIFF",),
        ".wav": (b"RIFF",),
        ".ogg": (b"OggS",),
        ".docx": (b"PK\x03\x04",),
        ".xlsx": (b"PK\x03\x04",),
        ".pptx": (b"PK\x03\x04",),
    }
    if extension == ".webp":
        return header.startswith(b"RIFF") and header[8:12] == b"WEBP"
    if extension == ".wav":
        return header.startswith(b"RIFF") and header[8:12] == b"WAVE"
    if extension in (".mp4", ".mov"):
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if extension == ".webm":
        return header.startswith(b"\x1aE\xdf\xa3")
    if extension == ".mp3":
        return header.startswith(b"ID3") or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0)
    expected = signatures.get(extension)
    return True if expected is None else any(header.startswith(signature) for signature in expected)


def _managed_path(url: str | None) -> Path | None:
    if not url:
        return None
    prefix = f"{settings.ASSET_PUBLIC_BASE_URL}/"
    if not url.startswith(prefix):
        return None
    relative = url.removeprefix(prefix)
    root = settings.ASSET_STORAGE_DIR.resolve()
    candidate = (root / relative).resolve()
    return candidate if candidate.is_relative_to(root) else None


async def store_upload(project_id: int, upload: UploadFile) -> str:
    original_name = Path(upload.filename or "").name
    extension = Path(original_name).suffix.lower()
    allowed_mimes = ALLOWED_FILE_TYPES.get(extension)
    if not allowed_mimes or upload.content_type not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format de fichier non pris en charge.",
        )

    project_dir = (settings.ASSET_STORAGE_DIR / str(project_id)).resolve()
    root = settings.ASSET_STORAGE_DIR.resolve()
    if not project_dir.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Chemin de stockage invalide.")
    project_dir.mkdir(parents=True, exist_ok=True)
    destination = project_dir / f"{uuid4().hex}{extension}"
    temporary = destination.with_suffix(f"{destination.suffix}.part")
    total_size = 0
    header = b""
    try:
        with temporary.open("xb") as target:
            while chunk := await upload.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > settings.ASSET_MAX_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Le fichier dépasse la limite de {settings.ASSET_MAX_BYTES // (1024 * 1024)} Mo.",
                    )
                if len(header) < 16:
                    header += chunk[: 16 - len(header)]
                target.write(chunk)
        if total_size == 0 or not _signature_matches(extension, header):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Le contenu du fichier ne correspond pas à son format.",
            )
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return f"{settings.ASSET_PUBLIC_BASE_URL}/{project_id}/{destination.name}"


def delete_managed_file(url: str | None) -> None:
    managed_path = _managed_path(url)
    if managed_path is not None:
        managed_path.unlink(missing_ok=True)


def stage_managed_file(url: str | None) -> tuple[Path, Path] | None:
    managed_path = _managed_path(url)
    if managed_path is None or not managed_path.exists():
        return None
    staged_path = managed_path.with_suffix(f"{managed_path.suffix}.deleting")
    managed_path.replace(staged_path)
    return managed_path, staged_path


def restore_staged_file(staged: tuple[Path, Path] | None) -> None:
    if staged is not None and staged[1].exists():
        staged[1].replace(staged[0])


def finalize_staged_file(staged: tuple[Path, Path] | None) -> None:
    if staged is not None:
        staged[1].unlink(missing_ok=True)