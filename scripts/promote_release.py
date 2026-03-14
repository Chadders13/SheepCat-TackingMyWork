#!/usr/bin/env python3
"""
Promote a SheepCat release on Bluesky.

Reads credentials and release context from environment variables and posts
a short announcement to Bluesky via the atproto SDK.

Environment variables required:
    BSKY_HANDLE       – Bluesky handle (e.g. your-handle.bsky.social)
    BSKY_PASSWORD     – Bluesky App Password (not your login password)

Environment variables supplied automatically by GitHub Actions:
    GITHUB_REF_NAME   – the release tag / version (e.g. v1.2.0)
    GITHUB_SERVER_URL – base URL of the GitHub server (e.g. https://github.com)
    GITHUB_REPOSITORY – owner/repo slug (e.g. Chadders13/SheepCat-TrackingMyWork)
"""
import os
import sys

from atproto import Client

POST_TEMPLATE = (
    "🚀 SheepCat {version} is live! "
    "Our 100% local AI work tracker just got updated. "
    "Zero cloud sync, total privacy. "
    "Check out the latest release notes here: {release_url} "
    "#Python #LocalAI #DevTools"
)


def build_release_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    tag = os.environ.get("GITHUB_REF_NAME", "")
    return f"{server}/{repo}/releases/tag/{tag}"


def main() -> None:
    handle = os.environ.get("BSKY_HANDLE", "")
    password = os.environ.get("BSKY_PASSWORD", "")

    if not handle or not password:
        print("Error: BSKY_HANDLE and BSKY_PASSWORD must be set.", file=sys.stderr)
        sys.exit(1)

    version = os.environ.get("GITHUB_REF_NAME", "unknown")
    release_url = build_release_url()

    post_text = POST_TEMPLATE.format(version=version, release_url=release_url)

    try:
        client = Client()
        client.login(handle, password)
        client.send_post(text=post_text)
        print(f"Successfully posted to Bluesky: {post_text}")
    except Exception as exc:  # Intentionally broad; KeyboardInterrupt/SystemExit are BaseException
        print(f"Bluesky post failed (non-fatal): {exc}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
