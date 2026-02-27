"""
Tests for the ollama_client module.

These tests mock the ``requests`` library so no real Ollama server is required.
"""
import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call
from typing import List, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import ollama_client
from ollama_client import check_connection, pull_model, RECOMMENDED_MODELS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(status_code: int, json_data: Dict):
    """Build a minimal mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


def _make_streaming_response(lines: List[Dict]):
    """Build a mock streaming response whose iter_lines yields JSON strings."""
    resp = MagicMock()
    resp.status_code = 200
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.iter_lines.return_value = [json.dumps(line).encode() for line in lines]
    return resp


# ---------------------------------------------------------------------------
# check_connection
# ---------------------------------------------------------------------------

class TestCheckConnection(unittest.TestCase):

    @patch('ollama_client.requests.get')
    def test_success_returns_true_and_model_names(self, mock_get):
        mock_get.return_value = _make_response(200, {
            "models": [
                {"name": "llama3.2:3b"},
                {"name": "deepseek-r1:8b"},
            ]
        })
        result = check_connection("http://localhost:11434")
        self.assertTrue(result.success)
        self.assertEqual(result.models, ["llama3.2:3b", "deepseek-r1:8b"])
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags", timeout=5
        )

    @patch('ollama_client.requests.get')
    def test_non_200_returns_false(self, mock_get):
        mock_get.return_value = _make_response(503, {})
        result = check_connection("http://localhost:11434")
        self.assertFalse(result.success)
        self.assertEqual(result.models, [])

    @patch('ollama_client.requests.get', side_effect=ConnectionError("refused"))
    def test_exception_returns_false(self, _mock_get):
        result = check_connection("http://localhost:11434")
        self.assertFalse(result.success)
        self.assertEqual(result.models, [])

    @patch('ollama_client.requests.get')
    def test_trailing_slash_stripped_from_base_url(self, mock_get):
        mock_get.return_value = _make_response(200, {"models": []})
        check_connection("http://localhost:11434/")
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags", timeout=5
        )

    @patch('ollama_client.requests.get')
    def test_empty_models_list(self, mock_get):
        mock_get.return_value = _make_response(200, {"models": []})
        result = check_connection("http://localhost:11434")
        self.assertTrue(result.success)
        self.assertEqual(result.models, [])


# ---------------------------------------------------------------------------
# pull_model
# ---------------------------------------------------------------------------

class TestPullModel(unittest.TestCase):

    @patch('ollama_client.requests.post')
    def test_successful_pull_calls_progress_and_returns_true(self, mock_post):
        stream_lines = [
            {"status": "pulling manifest"},
            {"status": "downloading", "completed": 512, "total": 1024},
            {"status": "downloading", "completed": 1024, "total": 1024},
            {"status": "success"},
        ]
        mock_post.return_value = _make_streaming_response(stream_lines)

        progress_calls = []
        result = pull_model(
            "http://localhost:11434",
            "llama3.2:3b",
            progress_callback=lambda s, c, t: progress_calls.append((s, c, t)),
        )

        self.assertTrue(result)
        # All four lines should have triggered the callback
        self.assertEqual(len(progress_calls), 4)
        self.assertEqual(progress_calls[-1][0], "success")

    @patch('ollama_client.requests.post')
    def test_non_200_returns_false(self, mock_post):
        resp = MagicMock()
        resp.status_code = 404
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_post.return_value = resp

        result = pull_model("http://localhost:11434", "unknown:model")
        self.assertFalse(result)

    @patch('ollama_client.requests.post', side_effect=OSError("network error"))
    def test_exception_returns_false(self, _mock_post):
        result = pull_model("http://localhost:11434", "llama3.2:3b")
        self.assertFalse(result)

    @patch('ollama_client.requests.post')
    def test_no_progress_callback_does_not_raise(self, mock_post):
        stream_lines = [{"status": "success"}]
        mock_post.return_value = _make_streaming_response(stream_lines)
        result = pull_model("http://localhost:11434", "llama3.2:3b")
        self.assertTrue(result)

    @patch('ollama_client.requests.post')
    def test_malformed_json_line_skipped(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        resp.iter_lines.return_value = [
            b"not json at all",
            json.dumps({"status": "success"}).encode(),
        ]
        mock_post.return_value = resp

        result = pull_model("http://localhost:11434", "llama3.2:3b")
        self.assertTrue(result)


# ---------------------------------------------------------------------------
# RECOMMENDED_MODELS constant
# ---------------------------------------------------------------------------

class TestRecommendedModels(unittest.TestCase):

    def test_at_least_one_model_defined(self):
        self.assertGreater(len(RECOMMENDED_MODELS), 0)

    def test_all_models_have_required_keys(self):
        for model in RECOMMENDED_MODELS:
            with self.subTest(model=model):
                self.assertIn("name", model)
                self.assertIn("label", model)
                self.assertIn("description", model)

    def test_model_names_are_non_empty_strings(self):
        for model in RECOMMENDED_MODELS:
            self.assertIsInstance(model["name"], str)
            self.assertTrue(model["name"].strip())


if __name__ == '__main__':
    unittest.main()
