"""
External API service factory for SheepCat Work Tracker.

Provides a factory pattern for interacting with external systems (Jira, Azure
DevOps, Obsidian, Notable).  The SheepCat privacy philosophy requires that
**no data is ever sent to an external system without explicit user consent**.
Every write operation in the concrete service classes must only be called
after the user has confirmed the action in the Send Updates / Send Notes
dialog.
"""
import base64
import json
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict

import requests


# ---------------------------------------------------------------------------
# Abstract base class — ticket systems
# ---------------------------------------------------------------------------

class ExternalAPIService(ABC):
    """Abstract base class for all external API service adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for the service (e.g. "Jira")."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when the service has sufficient credentials to be used."""

    @abstractmethod
    def verify_ticket(self, ticket_id: str) -> Optional[Dict]:
        """Check whether *ticket_id* exists in the external system.

        Args:
            ticket_id: The ticket / work-item identifier string.

        Returns:
            A dictionary with at least ``id``, ``summary``, ``status`` and
            ``url`` keys when the ticket is found, or ``None`` otherwise.
        """

    @abstractmethod
    def send_comment(self, ticket_id: str, comment: str) -> bool:
        """Post *comment* as a comment/note on the ticket identified by
        *ticket_id*.

        This method must only be called after the user has given explicit
        consent in the Send Updates dialog.

        Args:
            ticket_id: The external ticket identifier.
            comment: Plain-text comment body to post.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """


# ---------------------------------------------------------------------------
# Abstract base class — note-taking apps
# ---------------------------------------------------------------------------

class NoteExportService(ABC):
    """Abstract base class for note-taking application adapters.

    Note export services receive formatted Markdown notes or summaries from
    SheepCat and store them in the target application.  Like
    :class:`ExternalAPIService`, all write operations must only be triggered
    after explicit user confirmation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for the service (e.g. "Obsidian")."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return ``True`` when the service has sufficient config to operate."""

    @abstractmethod
    def send_note(self, title: str, content: str) -> bool:
        """Create or update a note in the target application.

        This method must only be called after the user has given explicit
        consent in the Send Notes dialog.

        Args:
            title:   Note title (used as filename / note heading).
            content: Note body in Markdown format.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """


# ---------------------------------------------------------------------------
# Jira Cloud API v3
# ---------------------------------------------------------------------------

class JiraAPIService(ExternalAPIService):
    """Jira Cloud REST API v3 using HTTP Basic authentication.

    Reference:
        https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/

    Credentials are read directly from the :class:`~settings_manager.SettingsManager`
    via the factory — they are never hard-coded or stored in source files.
    """

    def __init__(self, host: str, email: str, api_token: str):
        self._host = host.rstrip("/") if host else ""
        self._email = email or ""
        self._api_token = api_token or ""

    # -- ExternalAPIService interface ----------------------------------------

    @property
    def name(self) -> str:
        return "Jira"

    @property
    def is_configured(self) -> bool:
        return bool(self._host and self._email and self._api_token)

    def verify_ticket(self, ticket_id: str) -> Optional[Dict]:
        """Fetch an issue from Jira Cloud API v3.

        Returns a summary dict or ``None`` if the ticket cannot be found or
        the request fails.
        """
        if not self.is_configured:
            return None
        try:
            url = f"{self._host}/rest/api/3/issue/{ticket_id}"
            response = requests.get(url, headers=self._auth_headers(), timeout=10)
            if response.status_code == 200:
                data = response.json()
                fields = data.get("fields", {})
                return {
                    "id": ticket_id,
                    "summary": fields.get("summary", ""),
                    "status": fields.get("status", {}).get("name", ""),
                    "url": f"{self._host}/browse/{ticket_id}",
                }
        except Exception:
            pass
        return None

    def send_comment(self, ticket_id: str, comment: str) -> bool:
        """Add a comment to a Jira issue using the Atlassian Document Format
        (ADF) required by API v3.
        """
        if not self.is_configured:
            return False
        try:
            url = f"{self._host}/rest/api/3/issue/{ticket_id}/comment"
            # Jira API v3 requires the body in Atlassian Document Format (ADF).
            payload = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": comment}],
                        }
                    ],
                }
            }
            response = requests.post(
                url, headers=self._auth_headers(), json=payload, timeout=10
            )
            return response.status_code in (200, 201)
        except Exception:
            return False

    # -- Internal helpers ----------------------------------------------------

    def _auth_headers(self) -> Dict:
        credentials = base64.b64encode(
            f"{self._email}:{self._api_token}".encode()
        ).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


# ---------------------------------------------------------------------------
# Azure DevOps REST API
# ---------------------------------------------------------------------------

class AzureDevOpsAPIService(ExternalAPIService):
    """Azure DevOps REST API service using a Personal Access Token (PAT).

    Reference:
        https://learn.microsoft.com/en-us/azure/devops/integrate/how-to/call-rest-api

    The organization URL must include the project path when work-item
    operations are scoped to a specific project, e.g.
    ``https://dev.azure.com/myorg/myproject``.
    """

    def __init__(self, org_url: str, personal_access_token: str):
        self._org_url = org_url.rstrip("/") if org_url else ""
        self._pat = personal_access_token or ""

    # -- ExternalAPIService interface ----------------------------------------

    @property
    def name(self) -> str:
        return "Azure DevOps"

    @property
    def is_configured(self) -> bool:
        return bool(self._org_url and self._pat)

    def verify_ticket(self, ticket_id: str) -> Optional[Dict]:
        """Fetch a work item from Azure DevOps.

        Returns a summary dict or ``None`` if the item cannot be found.
        """
        if not self.is_configured:
            return None
        try:
            url = (
                f"{self._org_url}/_apis/wit/workitems/{ticket_id}"
                "?api-version=7.1"
            )
            response = requests.get(url, headers=self._auth_headers(), timeout=10)
            if response.status_code == 200:
                data = response.json()
                fields = data.get("fields", {})
                html_url = (
                    data.get("_links", {}).get("html", {}).get("href", "")
                )
                return {
                    "id": str(ticket_id),
                    "summary": fields.get("System.Title", ""),
                    "status": fields.get("System.State", ""),
                    "url": html_url,
                }
        except Exception:
            pass
        return None

    def send_comment(self, ticket_id: str, comment: str) -> bool:
        """Add a comment to an Azure DevOps work item."""
        if not self.is_configured:
            return False
        try:
            url = (
                f"{self._org_url}/_apis/wit/workitems/{ticket_id}/comments"
                "?api-version=7.1-preview.3"
            )
            payload = {"text": comment}
            response = requests.post(
                url, headers=self._auth_headers(), json=payload, timeout=10
            )
            return response.status_code in (200, 201)
        except Exception:
            return False

    # -- Internal helpers ----------------------------------------------------

    def _auth_headers(self) -> Dict:
        # Azure DevOps Basic auth uses an empty username and the PAT as password.
        credentials = base64.b64encode(f":{self._pat}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


# ---------------------------------------------------------------------------
# Obsidian Local REST API
# ---------------------------------------------------------------------------

class ObsidianAPIService(NoteExportService):
    """Sends formatted notes to Obsidian via the *Local REST API* plugin.

    The plugin is available at https://github.com/coddingtonbear/obsidian-local-rest-api
    and runs a local HTTP server (default: ``http://localhost:27123``) secured
    with an API key the user generates inside Obsidian.

    Reference:
        https://coddingtonbear.github.io/obsidian-local-rest-api/

    Credentials are obtained from the :class:`~settings_manager.SettingsManager`
    via the factory — the API key is stored in the OS keychain, never in
    plain-text settings files.
    """

    def __init__(self, host: str, api_key: str, notes_folder: str = "SheepCat"):
        self._host = host.rstrip("/") if host else ""
        self._api_key = api_key or ""
        self._notes_folder = notes_folder.strip("/") if notes_folder else "SheepCat"

    # -- NoteExportService interface -----------------------------------------

    @property
    def name(self) -> str:
        return "Obsidian"

    @property
    def is_configured(self) -> bool:
        return bool(self._host and self._api_key)

    def send_note(self, title: str, content: str) -> bool:
        """Create or overwrite a note in the configured Obsidian vault folder.

        The note is stored at ``<vault>/<notes_folder>/<title>.md``.

        Args:
            title:   Note title; used as the filename (invalid path characters
                     are replaced with underscores).
            content: Markdown body for the note.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        if not self.is_configured:
            return False
        safe_title = _safe_filename(title)
        path = f"{self._notes_folder}/{safe_title}.md"
        url = f"{self._host}/vault/{path}"
        try:
            response = requests.put(
                url,
                headers=self._auth_headers(),
                data=content.encode("utf-8"),
                timeout=10,
            )
            return response.status_code in (200, 201, 204)
        except Exception:
            return False

    # -- Internal helpers ----------------------------------------------------

    def _auth_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "text/markdown",
        }


# ---------------------------------------------------------------------------
# Notable (file-based)
# ---------------------------------------------------------------------------

class NotableService(NoteExportService):
    """Writes formatted Markdown notes directly to a Notable notes directory.

    Notable stores notes as individual ``.md`` files inside a single
    directory (the user's configured *Notes* folder).  This adapter writes
    a note file into that directory — no API or network connection is needed.

    Because no external network call is made the user's data never leaves the
    local machine at all; the usual explicit-confirmation step is still
    presented so the user remains in full control.
    """

    def __init__(self, notes_directory: str):
        self._notes_directory = notes_directory or ""

    # -- NoteExportService interface -----------------------------------------

    @property
    def name(self) -> str:
        return "Notable"

    @property
    def is_configured(self) -> bool:
        return bool(self._notes_directory and os.path.isdir(self._notes_directory))

    def send_note(self, title: str, content: str) -> bool:
        """Write *content* to a Markdown file in the Notable notes directory.

        Args:
            title:   Note title; used as the filename.
            content: Markdown body for the note.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        if not self.is_configured:
            return False
        safe_title = _safe_filename(title)
        file_path = os.path.join(self._notes_directory, f"{safe_title}.md")
        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                fh.write(content)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(title: str) -> str:
    """Replace characters that are invalid in file/path names with ``_``."""
    invalid = r'\/:*?"<>|'
    result = title
    for ch in invalid:
        result = result.replace(ch, "_")
    return result.strip() or "note"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class APIServiceFactory:
    """Factory that creates :class:`ExternalAPIService` and
    :class:`NoteExportService` instances from a
    :class:`~settings_manager.SettingsManager`.
    """

    @staticmethod
    def create_jira_service(settings_manager) -> JiraAPIService:
        """Create a :class:`JiraAPIService` from saved settings."""
        return JiraAPIService(
            host=settings_manager.get("jira_host", ""),
            email=settings_manager.get("jira_email", ""),
            api_token=settings_manager.get_credential("jira_api_token"),
        )

    @staticmethod
    def create_azure_devops_service(settings_manager) -> AzureDevOpsAPIService:
        """Create an :class:`AzureDevOpsAPIService` from saved settings."""
        return AzureDevOpsAPIService(
            org_url=settings_manager.get("azure_devops_org_url", ""),
            personal_access_token=settings_manager.get_credential("azure_devops_pat"),
        )

    @staticmethod
    def create_obsidian_service(settings_manager) -> ObsidianAPIService:
        """Create an :class:`ObsidianAPIService` from saved settings."""
        return ObsidianAPIService(
            host=settings_manager.get("obsidian_host", "http://localhost:27123"),
            api_key=settings_manager.get_credential("obsidian_api_key"),
            notes_folder=settings_manager.get("obsidian_notes_folder", "SheepCat"),
        )

    @staticmethod
    def create_notable_service(settings_manager) -> NotableService:
        """Create a :class:`NotableService` from saved settings."""
        return NotableService(
            notes_directory=settings_manager.get("notable_notes_directory", ""),
        )

    @staticmethod
    def get_configured_services(settings_manager) -> list:
        """Return ticket-system service instances that are configured **and**
        enabled in settings.

        A service is included only when both its
        :attr:`~ExternalAPIService.is_configured` property returns ``True``
        *and* the corresponding ``<service>_enabled`` setting is truthy.
        """
        services = []

        if settings_manager.get("jira_enabled", True):
            jira = APIServiceFactory.create_jira_service(settings_manager)
            if jira.is_configured:
                services.append(jira)

        if settings_manager.get("azure_devops_enabled", True):
            ado = APIServiceFactory.create_azure_devops_service(settings_manager)
            if ado.is_configured:
                services.append(ado)

        return services

    @staticmethod
    def get_configured_note_services(settings_manager) -> list:
        """Return note-export service instances that are configured **and**
        enabled in settings.

        A service is included only when both its
        :attr:`~NoteExportService.is_configured` property returns ``True``
        *and* the corresponding ``<service>_enabled`` setting is truthy.
        """
        services = []

        if settings_manager.get("obsidian_enabled", False):
            obsidian = APIServiceFactory.create_obsidian_service(settings_manager)
            if obsidian.is_configured:
                services.append(obsidian)

        if settings_manager.get("notable_enabled", False):
            notable = APIServiceFactory.create_notable_service(settings_manager)
            if notable.is_configured:
                services.append(notable)

        return services
