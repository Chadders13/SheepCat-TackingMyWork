"""
Unit tests for the GitMCPClient class.

Tests cover:
  - generate_context_nudge: Ollama integration (mocked requests)
  - get_git_status: MCP async plumbing (mocked ClientSession / stdio_client)
  - fetch_nudge: end-to-end convenience wrapper (fully mocked)
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path so imports work without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from git_mcp_client import GitMCPClient


# ---------------------------------------------------------------------------
# generate_context_nudge tests (Ollama, synchronous)
# ---------------------------------------------------------------------------

class TestGenerateContextNudge(unittest.TestCase):
    """Tests for GitMCPClient.generate_context_nudge()."""

    def setUp(self):
        self.client = GitMCPClient()
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "test-model"

    def test_returns_ollama_response_on_success(self):
        """When Ollama returns 200, the response text is returned."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "I see you've been editing auth.py — shall I log this?"
        }
        with patch("git_mcp_client.requests.post", return_value=mock_resp):
            result = self.client.generate_context_nudge(
                "M auth.py", self.api_url, self.model
            )
        self.assertEqual(result, "I see you've been editing auth.py — shall I log this?")

    def test_fallback_when_ollama_unreachable(self):
        """When requests raises an exception, the static fallback is returned."""
        with patch("git_mcp_client.requests.post", side_effect=Exception("refused")):
            result = self.client.generate_context_nudge(
                "M db.py", self.api_url, self.model
            )
        self.assertIn("uncommitted changes", result)

    def test_fallback_when_ollama_returns_non_200(self):
        """When Ollama returns a non-200 status, the static fallback is returned."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("git_mcp_client.requests.post", return_value=mock_resp):
            result = self.client.generate_context_nudge(
                "M db.py", self.api_url, self.model
            )
        self.assertIn("uncommitted changes", result)

    def test_fallback_when_git_status_empty(self):
        """When git_status is empty, a generic nudge is returned without calling Ollama."""
        with patch("git_mcp_client.requests.post") as mock_post:
            result = self.client.generate_context_nudge(
                "", self.api_url, self.model
            )
        mock_post.assert_not_called()
        self.assertIn("check in", result.lower())

    def test_fallback_when_git_status_is_mcp_error(self):
        """When git_status contains a 'Git MCP error:' prefix, Ollama is not called."""
        with patch("git_mcp_client.requests.post") as mock_post:
            result = self.client.generate_context_nudge(
                "Git MCP error: process not found", self.api_url, self.model
            )
        mock_post.assert_not_called()
        self.assertIn("check in", result.lower())

    def test_ollama_called_with_correct_payload(self):
        """The correct payload (model, prompt, stream) is sent to Ollama."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Looks good!"}
        with patch("git_mcp_client.requests.post", return_value=mock_resp) as mock_post:
            self.client.generate_context_nudge("M foo.py", self.api_url, self.model, timeout=15)

        mock_post.assert_called_once()
        _, call_kwargs = mock_post.call_args
        payload = call_kwargs["json"]
        self.assertEqual(payload["model"], self.model)
        self.assertFalse(payload["stream"])
        self.assertIn("foo.py", payload["prompt"])


# ---------------------------------------------------------------------------
# get_git_status tests (async MCP, mocked)
# ---------------------------------------------------------------------------

class TestGetGitStatus(unittest.TestCase):
    """Tests for GitMCPClient.get_git_status() using a mocked MCP session."""

    def setUp(self):
        self.client = GitMCPClient()

    def _make_tool_result(self, text: str):
        """Build a mock tool-call result with a single text content block."""
        content_block = MagicMock()
        content_block.text = text
        result = MagicMock()
        result.content = [content_block]
        return result

    def test_returns_status_text_on_success(self):
        """git_status tool result text is returned correctly."""
        tool_result = self._make_tool_result("On branch main\nModified: auth.py")

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=tool_result)

        # Patch both the context manager layers used inside _async_get_git_status.
        with patch(
            "git_mcp_client.stdio_client",
            return_value=_async_cm((AsyncMock(), AsyncMock())),
        ), patch(
            "git_mcp_client.ClientSession",
            return_value=_async_cm(mock_session),
        ):
            result = self.client.get_git_status("/repo")

        self.assertEqual(result, "On branch main\nModified: auth.py")
        mock_session.call_tool.assert_called_once_with(
            "git_status", {"repo_path": "/repo"}
        )

    def test_returns_error_message_on_exception(self):
        """When the MCP call raises, a 'Git MCP error:' prefix is returned."""
        with patch(
            "git_mcp_client.stdio_client",
            side_effect=Exception("npx not found"),
        ):
            result = self.client.get_git_status("/repo")

        self.assertTrue(result.startswith("Git MCP error:"))
        self.assertIn("npx not found", result)

    def test_fallback_when_no_text_content(self):
        """When the tool result has no text attribute, fallback message is returned."""
        content_block = MagicMock(spec=[])  # No 'text' attribute
        tool_result = MagicMock()
        tool_result.content = [content_block]

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=tool_result)

        with patch(
            "git_mcp_client.stdio_client",
            return_value=_async_cm((AsyncMock(), AsyncMock())),
        ), patch(
            "git_mcp_client.ClientSession",
            return_value=_async_cm(mock_session),
        ):
            result = self.client.get_git_status("/repo")

        self.assertIn("No git status", result)


# ---------------------------------------------------------------------------
# fetch_nudge integration tests (both layers mocked)
# ---------------------------------------------------------------------------

class TestFetchNudge(unittest.TestCase):
    """Tests for the convenience GitMCPClient.fetch_nudge() method."""

    def setUp(self):
        self.client = GitMCPClient()

    def test_fetch_nudge_combines_status_and_nudge(self):
        """fetch_nudge calls get_git_status then generate_context_nudge."""
        with patch.object(
            self.client, "get_git_status", return_value="M auth.py"
        ) as mock_status, patch.object(
            self.client,
            "generate_context_nudge",
            return_value="Looks like you edited auth.py!",
        ) as mock_nudge:
            result = self.client.fetch_nudge(
                "/repo",
                "http://localhost:11434/api/generate",
                "test-model",
                timeout=5,
            )

        mock_status.assert_called_once_with("/repo")
        mock_nudge.assert_called_once_with(
            "M auth.py",
            "http://localhost:11434/api/generate",
            "test-model",
            5,
        )
        self.assertEqual(result, "Looks like you edited auth.py!")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _async_cm:
    """Minimal async context manager that yields a fixed value."""

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *_):
        pass


if __name__ == "__main__":
    unittest.main()
