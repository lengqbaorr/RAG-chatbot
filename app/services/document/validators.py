from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from app.core.exceptions import BadRequestError


def safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
    name = name.replace("..", "_")
    if not name:
        raise BadRequestError("Invalid filename")
    return name


def validate_extension(filename: str, allowed_extensions: tuple[str, ...]) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if not suffix:
        raise BadRequestError("Uploaded file must have an extension")
    if suffix not in allowed_extensions:
        raise BadRequestError(
            f"Unsupported file extension: .{suffix}",
            details={"allowed_extensions": list(allowed_extensions)},
        )
    return suffix


def validate_http_url(url: str) -> str:
    clean = url.strip()
    parsed = urlparse(clean)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise BadRequestError("URL must start with http:// or https://")
    return clean
