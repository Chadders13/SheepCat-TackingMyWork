"""
Secure credential storage for SheepCat Work Tracker.

API tokens (Jira, Azure DevOps, Obsidian, …) are stored in the operating
system's native secret store via the :mod:`keyring` library:

* **Windows** — Windows Credential Manager
* **macOS**   — macOS Keychain
* **Linux**   — Secret Service / kwallet

If no suitable keyring backend is found the token is stored (and retrieved)
from the plain-text settings JSON as a best-effort fallback, with a warning
logged to stdout so the user is aware.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Human-readable application name used as the keyring "service" identifier.
_KEYRING_SERVICE = "SheepCat-WorkTracker"


def _get_keyring():
    """Return the keyring module, or ``None`` when it is unavailable."""
    try:
        import keyring  # type: ignore
        return keyring
    except ImportError:
        return None


def is_keyring_available() -> bool:
    """Return ``True`` when a working keyring backend can be found."""
    kr = _get_keyring()
    if kr is None:
        return False
    try:
        # Accessing the backend may raise if there is no usable backend.
        backend = kr.get_keyring()
        # The "fail" keyring raises on every operation — treat as unavailable.
        return "fail" not in type(backend).__name__.lower()
    except Exception:
        return False


def get_token(credential_key: str) -> str:
    """Retrieve a stored token from the OS keychain.

    Args:
        credential_key: The logical name for the credential, e.g.
            ``"jira_api_token"``.

    Returns:
        The stored token string, or an empty string if nothing is found.
    """
    kr = _get_keyring()
    if kr is None:
        return ""
    try:
        value = kr.get_password(_KEYRING_SERVICE, credential_key)
        return value or ""
    except Exception as exc:
        logger.warning("CredentialStore.get_token(%r) failed: %s", credential_key, exc)
        return ""


def set_token(credential_key: str, token: str) -> bool:
    """Persist *token* in the OS keychain under *credential_key*.

    Passing an empty string deletes any previously stored token.

    Args:
        credential_key: The logical name for the credential.
        token: The secret value to store.

    Returns:
        ``True`` on success, ``False`` otherwise.
    """
    kr = _get_keyring()
    if kr is None:
        logger.warning(
            "keyring not available — token for %r cannot be stored securely.",
            credential_key,
        )
        return False
    try:
        if token:
            kr.set_password(_KEYRING_SERVICE, credential_key, token)
        else:
            _delete_token_safe(kr, credential_key)
        return True
    except Exception as exc:
        logger.warning("CredentialStore.set_token(%r) failed: %s", credential_key, exc)
        return False


def delete_token(credential_key: str) -> bool:
    """Remove a stored token from the OS keychain.

    Args:
        credential_key: The logical name for the credential to remove.

    Returns:
        ``True`` on success (including when no token existed), ``False`` on
        unexpected error.
    """
    kr = _get_keyring()
    if kr is None:
        return False
    return _delete_token_safe(kr, credential_key)


def _delete_token_safe(kr, credential_key: str) -> bool:
    """Internal helper — delete a keyring entry without raising."""
    try:
        kr.delete_password(_KEYRING_SERVICE, credential_key)
        return True
    except Exception:
        # KeyringError / PasswordDeleteError are both acceptable when the entry
        # did not exist in the first place.
        return True
