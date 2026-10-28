"""Avatar upload service — save user avatars to local filesystem.

Stores avatar files under ``data/avatars/{user_id}.{ext}``. Validates MIME type
and size to prevent abuse (max 2MB, JPG/PNG/WEBP only).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from integrity_checker.config import PROJECT_ROOT, is_test_runtime

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_BYTES = 2 * 1024 * 1024  # 2MB


class AvatarService:
    """Handle avatar file storage for users.

    Files are stored as ``data/avatars/{user_id}.{ext}``. Each user has at most
    one avatar — re-uploading overwrites the existing file. The relative path
    is persisted in the User.avatar_path column and exposed as ``/api/avatars/...``
    via a StaticFiles mount in main.py.
    """

    def __init__(self, base_dir: Path | None = None, public_prefix: str = "/api/avatars") -> None:
        default_dir = (
            Path(tempfile.gettempdir()) / "integrity_checker_test_avatars"
            if is_test_runtime()
            else (PROJECT_ROOT / "data" / "avatars")
        )
        self.base_dir = (base_dir or default_dir).resolve()
        self.public_prefix = public_prefix.rstrip("/")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _matches_magic_bytes(content: bytes, mime: str) -> bool:
        """Verify that raw bytes match the declared image MIME type."""
        if mime == "image/png":
            return content.startswith(b"\x89PNG\r\n\x1a\n")
        if mime == "image/jpeg":
            return content.startswith(b"\xff\xd8\xff")
        if mime == "image/webp":
            return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
        return False

    def validate(self, mime: str, size: int, content: bytes | None = None) -> None:
        """Raise ValueError if the file is not acceptable."""
        if mime not in ALLOWED_MIME:
            raise ValueError(
                f"Unsupported image type '{mime}'. Allowed: {sorted(ALLOWED_MIME)}"
            )
        if size <= 0:
            raise ValueError("Avatar file is empty")
        if size > MAX_BYTES:
            raise ValueError(
                f"Avatar file too large ({size} bytes). Max size is {MAX_BYTES} bytes (2MB)"
            )
        if content is not None and not self._matches_magic_bytes(content, mime):
            raise ValueError(
                f"Invalid image file: content does not match declared type '{mime}'"
            )

    def save(self, user_id: int, content: bytes, mime: str) -> str:
        """Save avatar bytes for user. Returns the public URL path (e.g. ``/api/avatars/3.jpg``)."""
        self.validate(mime, len(content), content)
        ext = MIME_TO_EXT[mime]
        # Remove any prior avatar for this user (different extension)
        for old_ext in MIME_TO_EXT.values():
            old_path = self.base_dir / f"{user_id}.{old_ext}"
            if old_path.exists() and old_ext != ext:
                try:
                    old_path.unlink()
                except OSError:
                    pass
        target = self.base_dir / f"{user_id}.{ext}"
        target.write_bytes(content)
        return f"{self.public_prefix}/{user_id}.{ext}"

    def delete(self, avatar_url: str | None) -> None:
        """Delete the file referenced by a public URL or path. Safe if missing."""
        if not avatar_url:
            return
        if avatar_url.startswith(("http://", "https://")):
            return
        # Accept either the public URL or a relative path; resolve to local file safely
        name = Path(avatar_url.rsplit("/", 1)[-1]).name
        if not name:
            return
        target = (self.base_dir / name).resolve()
        if target.parent != self.base_dir:
            return
        if target.exists() and target.is_file():
            try:
                target.unlink()
            except OSError:
                pass

    def path_for(self, user_id: int, ext: str) -> Path:
        return self.base_dir / f"{user_id}.{ext}"

    @staticmethod
    def extension_from_url(avatar_url: str | None) -> str:
        if not avatar_url:
            return ""
        return avatar_url.rsplit(".", 1)[-1].lower() if "." in avatar_url else ""


_singleton: AvatarService | None = None
_singleton_dir: Path | None = None


def get_avatar_service() -> AvatarService:
    """Lazy singleton — mirrors the get_settings / get_session pattern."""
    global _singleton, _singleton_dir
    env_dir = os.environ.get("AVATARS_DIR")
    base = (
        Path(env_dir)
        if env_dir
        else (
            Path(tempfile.gettempdir()) / "integrity_checker_test_avatars"
            if is_test_runtime()
            else (PROJECT_ROOT / "data" / "avatars")
        )
    ).resolve()
    if _singleton is None or _singleton_dir != base:
        _singleton = AvatarService(base_dir=base)
        _singleton_dir = base
    return _singleton
