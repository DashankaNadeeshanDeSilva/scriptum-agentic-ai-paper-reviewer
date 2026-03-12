"""Security utilities: AES-256 encryption for API keys and secrets.

Uses cryptography.Fernet (AES-128-CBC under the hood with HMAC-SHA256)
to encrypt sensitive values before writing them to config.yaml.
The encryption key is auto-generated on first run and stored at
~/.scriptum/.key with restricted permissions.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

_KEY_DIR = Path.home() / ".scriptum"
_KEY_PATH = _KEY_DIR / ".key"

# Prefix so we can distinguish encrypted values from plain text in YAML
_ENC_PREFIX = "enc:"


class SecretManager:
    """Encrypt and decrypt sensitive configuration values.

    The encryption key is loaded from ``~/.scriptum/.key``.  If the file does
    not exist, a fresh key is generated and persisted with ``0600`` permissions.
    """

    def __init__(self, key_path: Path = _KEY_PATH) -> None:
        self._key_path = key_path
        self._cipher = Fernet(self._load_or_generate_key())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encrypt(self, value: str) -> str:
        """Encrypt a plain-text string and return it with the ``enc:`` prefix."""
        if not value:
            return ""
        return _ENC_PREFIX + self._cipher.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        """Decrypt a previously encrypted string (with ``enc:`` prefix).

        Returns the original plain text.  If *value* is not prefixed with
        ``enc:`` it is returned as-is (assumed to be plain text).
        """
        if not value:
            return ""
        if not value.startswith(_ENC_PREFIX):
            return value
        try:
            return self._cipher.decrypt(value[len(_ENC_PREFIX) :].encode()).decode()
        except InvalidToken:
            logger.warning("Failed to decrypt value — returning empty string")
            return ""

    def is_encrypted(self, value: str) -> bool:
        """Check whether a string carries the ``enc:`` prefix."""
        return bool(value) and value.startswith(_ENC_PREFIX)

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def _load_or_generate_key(self) -> bytes:
        """Load the Fernet key from disk or generate a new one."""
        if self._key_path.exists():
            key = self._key_path.read_bytes().strip()
            logger.debug("Encryption key loaded from {}", self._key_path)
            return key

        # First run — generate and persist
        key = Fernet.generate_key()
        self._key_path.parent.mkdir(parents=True, exist_ok=True)
        self._key_path.write_bytes(key)
        # Restrict permissions: owner read/write only
        os.chmod(self._key_path, stat.S_IRUSR | stat.S_IWUSR)
        logger.info("Generated new encryption key at {}", self._key_path)
        return key


def mask_secret(value: str, visible: int = 4) -> str:
    """Return a masked version of a secret string.

    Shows the last *visible* characters preceded by asterisks.
    Returns ``""`` for empty values.

    >>> mask_secret("sk-abc123456789")
    '**********6789'
    """
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return "*" * (len(value) - visible) + value[-visible:]


# Module-level singleton — lazily initialised on first import of config module.
_manager: SecretManager | None = None


def get_secret_manager() -> SecretManager:
    """Return the module-level SecretManager singleton."""
    global _manager  # noqa: PLW0603
    if _manager is None:
        _manager = SecretManager()
    return _manager
