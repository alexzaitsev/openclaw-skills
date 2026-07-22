"""Validation and immutable staging for Telegram images attached to Anki notes."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


INBOUND_ROOTS = tuple(
    Path(value)
    for value in os.environ.get(
        "ANKI_INBOUND_ROOTS",
        "/home/claw/.openclaw/media/inbound:/home/claw/.openclaw/workspaces/anki/media/inbound",
    ).split(":")
    if value
)
STAGING_ROOT = Path(
    os.environ.get(
        "ANKI_STAGING_ROOT", "/home/claw/.openclaw/workspaces/anki/.openclaw/inbound-media"
    )
)
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 12_000_000


class ImageValidationError(ValueError):
    """Raised when an image is outside the reviewed inbound-media contract."""


@dataclass(frozen=True)
class PreparedImage:
    path: Path
    data: bytes
    extension: str
    media_type: str
    width: int
    height: int
    sha256: str

    @property
    def media_filename(self) -> str:
        return f"anki-img-{self.sha256}{self.extension}"


def _resolve_file(path_text: str) -> Path:
    try:
        path = Path(path_text).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ImageValidationError(f"Image path is unavailable: {exc}") from exc
    if not path.is_file():
        raise ImageValidationError(f"Image is not a regular file: {path}")
    return path


def _require_under(path: Path, roots: tuple[Path, ...]) -> None:
    try:
        resolved_roots = tuple(root.resolve(strict=True) for root in roots)
    except OSError as exc:
        raise ImageValidationError(f"Image root is unavailable: {exc}") from exc
    if not any(path.is_relative_to(root) for root in resolved_roots):
        raise ImageValidationError(
            "Image must be under one of: " + ", ".join(str(root) for root in roots) + "."
        )


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise ImageValidationError("Invalid PNG header.")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 4 or not data.startswith(b"\xff\xd8"):
        raise ImageValidationError("Invalid JPEG header.")
    offset = 2
    while offset < len(data):
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset : offset + 2], "big")
        if length < 2 or offset + length > len(data):
            break
        if marker in {
            0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
        }:
            if length < 8:
                break
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            return width, height
        offset += length
    raise ImageValidationError("JPEG dimensions could not be read.")


def _image_details(data: bytes) -> tuple[str, str, int, int]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = _png_dimensions(data)
        return ".png", "image/png", width, height
    if data.startswith(b"\xff\xd8\xff"):
        width, height = _jpeg_dimensions(data)
        return ".jpg", "image/jpeg", width, height
    raise ImageValidationError("Only JPEG and PNG images are supported.")


def validate_image(
    path_text: str,
    *,
    allowed_roots: tuple[Path, ...],
    expected_sha256: str = "",
) -> PreparedImage:
    """Read, validate, and identify one bounded JPEG or PNG from approved roots."""
    path = _resolve_file(path_text)
    _require_under(path, allowed_roots)
    size = path.stat().st_size
    if size <= 0 or size > MAX_BYTES:
        raise ImageValidationError(f"Image size must be between 1 byte and {MAX_BYTES} bytes.")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ImageValidationError(f"Image cannot be read: {exc}") from exc
    extension, media_type, width, height = _image_details(data)
    if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
        raise ImageValidationError(
            f"Image dimensions must be positive and no more than {MAX_PIXELS} pixels."
        )
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 and digest != expected_sha256.lower():
        raise ImageValidationError("Image changed after the reviewed dry run; create a new plan.")
    return PreparedImage(path, data, extension, media_type, width, height, digest)


def stage_inbound_image(source_text: str) -> PreparedImage:
    """Copy a validated inbound image to a content-addressed private staging path."""
    source = validate_image(source_text, allowed_roots=INBOUND_ROOTS)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    STAGING_ROOT.chmod(0o700)
    destination = STAGING_ROOT / f"inbound-{source.sha256}{source.extension}"
    if destination.exists():
        existing = validate_image(str(destination), allowed_roots=(STAGING_ROOT,))
        if existing.sha256 != source.sha256:
            raise ImageValidationError("Staged image path conflicts with different content.")
    else:
        fd, temporary = tempfile.mkstemp(prefix=".incoming-", dir=STAGING_ROOT)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(source.data)
            os.chmod(temporary, 0o600)
            os.replace(temporary, destination)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    staged = validate_image(str(destination), allowed_roots=(STAGING_ROOT,))
    if staged.sha256 != source.sha256:
        raise ImageValidationError("Staged image changed while it was being copied.")
    return staged
