"""
Git MCP Client for SheepCat Work Tracker.

Connects to the official @modelcontextprotocol/server-git server via stdio
to fetch uncommitted changes from a local Git repository, then generates a
context-aware check-in nudge using the local Ollama instance.

Architecture:
  - GitMCPClient.get_git_status()  — async MCP call, run via asyncio.run()
  - GitMCPClient.generate_context_nudge() — Ollama placeholder/integration
  - GitMCPClient.fetch_nudge()     — convenience wrapper (for background thread)

Thread-safety:
  All public methods are safe to call from a background threading.Thread.
  They must NOT be called on the tkinter main thread because asyncio.run()
  blocks until the coroutine completes.  Pass results back to tkinter using
  root.after() as shown in MyWorkTracker.hourly_checkin().
"""

import asyncio

import requests

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GitMCPClient:
    """MCP client that connects to the Git MCP server over stdio.

    Spawns a child process running:
        npx -y @modelcontextprotocol/server-git
    and communicates with it using the Model Context Protocol to call
    the ``git_status`` tool for a given repository path.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_git_status(self, repo_path: str) -> str:
        """Fetch the current git status for *repo_path* via the MCP server.

        Synchronous wrapper around the async MCP handshake.  Runs a fresh
        event loop for each call so it is safe to call from any thread.

        Args:
            repo_path: Absolute (or relative) path to the Git repository.

        Returns:
            A string containing the raw git status output, or an error
            message prefixed with ``"Git MCP error:"`` when the call fails.
        """
        try:
            return asyncio.run(self._async_get_git_status(repo_path))
        except Exception as exc:
            return f"Git MCP error: {exc}"

    def generate_context_nudge(
        self,
        git_status: str,
        ollama_api_url: str,
        ollama_model: str,
        timeout: int = 30,
    ) -> str:
        """Generate a friendly, single-sentence check-in nudge using Ollama.

        Sends the raw git status to the local Ollama instance and asks it to
        produce a developer-friendly nudge.  This is the clean integration
        point for LLM generation — replace the body with any other backend
        as required.

        If Ollama is unreachable or returns an error, a safe fallback string
        is returned so the check-in dialog always shows something useful.

        Args:
            git_status: Raw output from the ``git_status`` MCP tool call.
            ollama_api_url: Full URL to the Ollama ``/api/generate`` endpoint,
                e.g. ``http://localhost:11434/api/generate``.
            ollama_model: Name of the Ollama model to use, e.g. ``"deepseek-r1:8b"``.
            timeout: HTTP request timeout in seconds (not milliseconds).

        Returns:
            A single friendly sentence, e.g.
            ``"I see you've been editing auth.py — should I log this?"``
        """
        # If no meaningful status was retrieved, return a generic fallback.
        if not git_status or git_status.startswith("Git MCP error"):
            return "Time to check in — what have you been working on?"

        prompt = (
            "Based on the following git status output, write a single friendly "
            "sentence asking the developer what they have been working on and "
            "whether they want to log it against their current ticket. "
            "Mention the changed files if they are visible. Be warm and concise.\n\n"
            f"Git status:\n{git_status[:1500]}"
        )

        payload = {
            "model": ollama_model,
            "prompt": prompt,
            "stream": False,
        }

        try:
            response = requests.post(ollama_api_url, json=payload, timeout=timeout)
            if response.status_code == 200:
                text = response.json().get("response", "").strip()
                if text:
                    return text
        except Exception:
            # Ollama is unavailable — fall through to the static fallback.
            pass

        # Static fallback used when Ollama cannot be reached.
        return (
            "I see you have uncommitted changes — "
            "should I log this against your current ticket?"
        )

    def fetch_nudge(
        self,
        repo_path: str,
        ollama_api_url: str,
        ollama_model: str,
        timeout: int = 30,
    ) -> str:
        """Fetch git status then generate a context-aware Ollama nudge.

        Convenience method that combines :meth:`get_git_status` and
        :meth:`generate_context_nudge` into a single blocking call.
        Designed to be run inside a ``threading.Thread`` so it does not
        freeze the tkinter main loop.

        Args:
            repo_path: Absolute path to the Git repository to inspect.
            ollama_api_url: Full URL to the Ollama ``/api/generate`` endpoint.
            ollama_model: Name of the Ollama model to use for generation.
            timeout: HTTP request timeout for the Ollama call, in seconds.

        Returns:
            A single-sentence nudge string ready for display in the check-in
            dialog.
        """
        git_status = self.get_git_status(repo_path)
        return self.generate_context_nudge(
            git_status, ollama_api_url, ollama_model, timeout
        )

    # ------------------------------------------------------------------
    # Private async implementation
    # ------------------------------------------------------------------

    async def _async_get_git_status(self, repo_path: str) -> str:
        """Async MCP session: spawn server, initialise, call git_status.

        Args:
            repo_path: Path to the Git repository passed to the tool call.

        Returns:
            The text content of the ``git_status`` tool response.
        """
        # Define the stdio server process to spawn.
        # npx downloads and runs the official @modelcontextprotocol/server-git
        # package on demand (no separate install step required).
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-git"],
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # MCP handshake: exchange capabilities with the server.
                await session.initialize()

                # Call the git_status tool, passing the target repository path.
                result = await session.call_tool(
                    "git_status", {"repo_path": repo_path}
                )

                # Extract plain-text content from the tool result.
                for content_block in result.content:
                    if hasattr(content_block, "text"):
                        return content_block.text

                return "No git status output received from MCP server."
