"""
Tests for the external API service factory.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from external_api_service import (
    JiraAPIService,
    AzureDevOpsAPIService,
    APIServiceFactory,
)


class TestJiraAPIService(unittest.TestCase):
    """Tests for JiraAPIService."""

    def _make_service(self, host="https://example.atlassian.net",
                      email="user@example.com", api_token="token123"):
        return JiraAPIService(host=host, email=email, api_token=api_token)

    def test_name(self):
        self.assertEqual(self._make_service().name, "Jira")

    def test_is_configured_all_fields(self):
        self.assertTrue(self._make_service().is_configured)

    def test_is_configured_missing_host(self):
        svc = self._make_service(host="")
        self.assertFalse(svc.is_configured)

    def test_is_configured_missing_email(self):
        svc = self._make_service(email="")
        self.assertFalse(svc.is_configured)

    def test_is_configured_missing_token(self):
        svc = self._make_service(api_token="")
        self.assertFalse(svc.is_configured)

    def test_verify_ticket_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "summary": "Fix the thing",
                "status": {"name": "In Progress"},
            }
        }
        with patch("external_api_service.requests.get", return_value=mock_response):
            result = self._make_service().verify_ticket("PROJ-1")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "PROJ-1")
        self.assertEqual(result["summary"], "Fix the thing")
        self.assertEqual(result["status"], "In Progress")
        self.assertIn("PROJ-1", result["url"])

    def test_verify_ticket_not_found(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("external_api_service.requests.get", return_value=mock_response):
            result = self._make_service().verify_ticket("PROJ-999")
        self.assertIsNone(result)

    def test_verify_ticket_network_error(self):
        with patch("external_api_service.requests.get", side_effect=Exception("timeout")):
            result = self._make_service().verify_ticket("PROJ-1")
        self.assertIsNone(result)

    def test_verify_ticket_unconfigured(self):
        svc = JiraAPIService(host="", email="", api_token="")
        self.assertIsNone(svc.verify_ticket("PROJ-1"))

    def test_send_comment_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        with patch("external_api_service.requests.post", return_value=mock_response):
            result = self._make_service().send_comment("PROJ-1", "Great progress!")
        self.assertTrue(result)

    def test_send_comment_failure(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        with patch("external_api_service.requests.post", return_value=mock_response):
            result = self._make_service().send_comment("PROJ-1", "Update")
        self.assertFalse(result)

    def test_send_comment_network_error(self):
        with patch("external_api_service.requests.post", side_effect=Exception("refused")):
            result = self._make_service().send_comment("PROJ-1", "Update")
        self.assertFalse(result)

    def test_send_comment_unconfigured(self):
        svc = JiraAPIService(host="", email="", api_token="")
        self.assertFalse(svc.send_comment("PROJ-1", "Update"))

    def test_auth_header_uses_basic(self):
        svc = self._make_service(email="me@test.com", api_token="secret")
        headers = svc._auth_headers()
        self.assertTrue(headers["Authorization"].startswith("Basic "))
        self.assertEqual(headers["Content-Type"], "application/json")


class TestAzureDevOpsAPIService(unittest.TestCase):
    """Tests for AzureDevOpsAPIService."""

    def _make_service(self, org_url="https://dev.azure.com/myorg/myproject",
                      pat="mytoken"):
        return AzureDevOpsAPIService(org_url=org_url, personal_access_token=pat)

    def test_name(self):
        self.assertEqual(self._make_service().name, "Azure DevOps")

    def test_is_configured_all_fields(self):
        self.assertTrue(self._make_service().is_configured)

    def test_is_configured_missing_org_url(self):
        svc = self._make_service(org_url="")
        self.assertFalse(svc.is_configured)

    def test_is_configured_missing_pat(self):
        svc = self._make_service(pat="")
        self.assertFalse(svc.is_configured)

    def test_verify_ticket_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fields": {
                "System.Title": "Implement feature",
                "System.State": "Active",
            },
            "_links": {"html": {"href": "https://dev.azure.com/myorg/_workitems/edit/42"}},
        }
        with patch("external_api_service.requests.get", return_value=mock_response):
            result = self._make_service().verify_ticket("42")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "42")
        self.assertEqual(result["summary"], "Implement feature")
        self.assertEqual(result["status"], "Active")

    def test_verify_ticket_not_found(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("external_api_service.requests.get", return_value=mock_response):
            result = self._make_service().verify_ticket("999")
        self.assertIsNone(result)

    def test_verify_ticket_network_error(self):
        with patch("external_api_service.requests.get", side_effect=Exception("timeout")):
            result = self._make_service().verify_ticket("42")
        self.assertIsNone(result)

    def test_verify_ticket_unconfigured(self):
        svc = AzureDevOpsAPIService(org_url="", personal_access_token="")
        self.assertIsNone(svc.verify_ticket("42"))

    def test_send_comment_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("external_api_service.requests.post", return_value=mock_response):
            result = self._make_service().send_comment("42", "Progress update")
        self.assertTrue(result)

    def test_send_comment_failure(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        with patch("external_api_service.requests.post", return_value=mock_response):
            result = self._make_service().send_comment("42", "Update")
        self.assertFalse(result)

    def test_send_comment_network_error(self):
        with patch("external_api_service.requests.post", side_effect=Exception("refused")):
            result = self._make_service().send_comment("42", "Update")
        self.assertFalse(result)

    def test_send_comment_unconfigured(self):
        svc = AzureDevOpsAPIService(org_url="", personal_access_token="")
        self.assertFalse(svc.send_comment("42", "Update"))

    def test_auth_header_uses_basic_with_empty_username(self):
        import base64
        svc = self._make_service(pat="mytoken")
        headers = svc._auth_headers()
        self.assertTrue(headers["Authorization"].startswith("Basic "))
        # Decode to verify format ":token"
        encoded = headers["Authorization"].split(" ", 1)[1]
        decoded = base64.b64decode(encoded).decode()
        self.assertTrue(decoded.startswith(":"))


class TestAPIServiceFactory(unittest.TestCase):
    """Tests for APIServiceFactory."""

    class _MockSettings:
        def __init__(self, data):
            self._data = data

        def get(self, key, default=""):
            return self._data.get(key, default)

    def _settings(self, **kwargs):
        return self._MockSettings(kwargs)

    def test_create_jira_service(self):
        sm = self._settings(
            jira_host="https://example.atlassian.net",
            jira_email="user@example.com",
            jira_api_token="token",
        )
        svc = APIServiceFactory.create_jira_service(sm)
        self.assertIsInstance(svc, JiraAPIService)
        self.assertTrue(svc.is_configured)

    def test_create_azure_devops_service(self):
        sm = self._settings(
            azure_devops_org_url="https://dev.azure.com/myorg",
            azure_devops_pat="pat",
        )
        svc = APIServiceFactory.create_azure_devops_service(sm)
        self.assertIsInstance(svc, AzureDevOpsAPIService)
        self.assertTrue(svc.is_configured)

    def test_get_configured_services_both(self):
        sm = self._settings(
            jira_host="https://example.atlassian.net",
            jira_email="user@example.com",
            jira_api_token="token",
            azure_devops_org_url="https://dev.azure.com/myorg",
            azure_devops_pat="pat",
        )
        services = APIServiceFactory.get_configured_services(sm)
        self.assertEqual(len(services), 2)
        names = [s.name for s in services]
        self.assertIn("Jira", names)
        self.assertIn("Azure DevOps", names)

    def test_get_configured_services_none(self):
        sm = self._settings()
        services = APIServiceFactory.get_configured_services(sm)
        self.assertEqual(services, [])

    def test_get_configured_services_jira_only(self):
        sm = self._settings(
            jira_host="https://example.atlassian.net",
            jira_email="user@example.com",
            jira_api_token="token",
        )
        services = APIServiceFactory.get_configured_services(sm)
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].name, "Jira")

    def test_get_configured_services_ado_only(self):
        sm = self._settings(
            azure_devops_org_url="https://dev.azure.com/myorg",
            azure_devops_pat="pat",
        )
        services = APIServiceFactory.get_configured_services(sm)
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].name, "Azure DevOps")


if __name__ == "__main__":
    unittest.main()
