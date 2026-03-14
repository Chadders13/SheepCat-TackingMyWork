"""
External API service factory for SheepCat Work Tracker.

Provides a factory pattern for interacting with external systems (Jira, Azure
DevOps).  The SheepCat privacy philosophy requires that **no data is ever sent
to an external system without explicit user consent**.  Every write operation
in the concrete service classes must only be called after the user has
confirmed the action in the Send Updates dialog.
"""
import base64
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict

import requests


# ---------------------------------------------------------------------------
# Abstract base class
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
# Factory
# ---------------------------------------------------------------------------

class APIServiceFactory:
    """Factory that creates :class:`ExternalAPIService` instances from
    a :class:`~settings_manager.SettingsManager`.
    """

    @staticmethod
    def create_jira_service(settings_manager) -> JiraAPIService:
        """Create a :class:`JiraAPIService` from saved settings."""
        return JiraAPIService(
            host=settings_manager.get("jira_host", ""),
            email=settings_manager.get("jira_email", ""),
            api_token=settings_manager.get("jira_api_token", ""),
        )

    @staticmethod
    def create_azure_devops_service(settings_manager) -> AzureDevOpsAPIService:
        """Create an :class:`AzureDevOpsAPIService` from saved settings."""
        return AzureDevOpsAPIService(
            org_url=settings_manager.get("azure_devops_org_url", ""),
            personal_access_token=settings_manager.get("azure_devops_pat", ""),
        )

    @staticmethod
    def get_configured_services(settings_manager) -> list:
        """Return a list of service instances that are fully configured.

        Only services whose :attr:`~ExternalAPIService.is_configured` property
        returns ``True`` are included.
        """
        services = []

        jira = APIServiceFactory.create_jira_service(settings_manager)
        if jira.is_configured:
            services.append(jira)

        ado = APIServiceFactory.create_azure_devops_service(settings_manager)
        if ado.is_configured:
            services.append(ado)

        return services
