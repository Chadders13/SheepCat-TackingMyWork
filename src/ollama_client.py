"""
Ollama API client for SheepCat Work Tracker.

Provides helpers for:
  - Testing the connection to an Ollama instance.
  - Listing locally available models.
  - Pulling a model with streaming progress updates.
"""

import json
from dataclasses import dataclass, field
import requests


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

# Curated model recommendations shown in the model-selection dialog.
RECOMMENDED_MODELS = [
    {
        "name": "qwen2.5:3b",
        "label": "Qwen 2.5 3B",
        "description": "Lightning fast, low memory usage. Great for quick summaries.",
    },
    {
        "name": "llama3.2:3b",
        "label": "Llama 3.2 3B",
        "description": "Balanced performance. Good all-round task summaries.",
    },
    {
        "name": "deepseek-r1:8b",
        "label": "DeepSeek-R1 8B",
        "description": "Advanced reasoning and chain-of-thought. Best quality.",
    },
]


@dataclass
class ConnectionResult:
    """Response object for an Ollama connection check."""
    success: bool
    models: list = field(default_factory=list)


def check_connection(base_url: str) -> ConnectionResult:
    """Probe the Ollama /api/tags endpoint.

    Args:
        base_url: Root URL of the Ollama instance, e.g. ``http://localhost:11434``.

    Returns:
        A :class:`ConnectionResult` with ``success`` set to ``True`` when the
        server responded with HTTP 200 and ``models`` containing a list of
        model name strings available on the server.
    """
    try:
        url = base_url.rstrip("/") + "/api/tags"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return ConnectionResult(success=True, models=models)
        return ConnectionResult(success=False)
    except Exception:
        return ConnectionResult(success=False)


def pull_model(base_url: str, model_name: str, progress_callback=None) -> bool:
    """Pull a model from the Ollama registry with streaming progress.

    The ``/api/pull`` endpoint streams newline-delimited JSON objects.  Each
    object may contain ``status``, ``completed`` and ``total`` fields.  When
    *progress_callback* is supplied it is called on every parsed line as::

        progress_callback(status: str, completed: int, total: int)

    Args:
        base_url: Root URL of the Ollama instance.
        model_name: The model tag to pull, e.g. ``"llama3.2:3b"``.
        progress_callback: Optional callable for streaming updates.

    Returns:
        ``True`` when the pull completes successfully, ``False`` otherwise.
    """
    try:
        url = base_url.rstrip("/") + "/api/pull"
        payload = {"name": model_name}
        with requests.post(url, json=payload, stream=True, timeout=None) as response:
            if response.status_code != 200:
                return False
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                try:
                    data = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                status = data.get("status", "")
                completed = data.get("completed", 0)
                total = data.get("total", 0)
                if progress_callback:
                    progress_callback(status, completed, total)
                if status == "success":
                    return True
        return True
    except Exception:
        return False
