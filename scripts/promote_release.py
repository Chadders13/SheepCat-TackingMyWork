#!/usr/bin/env python3
"""
Promote a SheepCat release on Bluesky.

Reads credentials and release context from environment variables and posts
a two-post thread to Bluesky via the atproto SDK:
  1. The main release announcement.
  2. A reply containing a summary of the release notes, or a fun SheepCat
     fact when no release body is available.

Environment variables required:
    BSKY_HANDLE          – Bluesky handle (e.g. your-handle.bsky.social)
    BSKY_PASSWORD        – Bluesky App Password (not your login password)

Environment variables supplied automatically by GitHub Actions:
    GITHUB_REF_NAME      – the release tag / version (e.g. v1.2.0)
    GITHUB_SERVER_URL    – base URL of the GitHub server (e.g. https://github.com)
    GITHUB_REPOSITORY    – owner/repo slug (e.g. Chadders13/SheepCat-TrackingMyWork)

Optional environment variable (mapped in the workflow from the release event):
    GITHUB_RELEASE_BODY  – the body text of the GitHub Release
"""
import os
import sys

from atproto import Client, models

# ── Post templates ────────────────────────────────────────────────────────────

POST_TEMPLATE = (
    "🚀 SheepCat {version} is live! "
    "Our 100% local AI work tracker just got updated. "
    "Zero cloud sync, total privacy. "
    "Check out the latest release notes here: {release_url} "
    "#Python #LocalAI #DevTools"
)

REPLY_NOTES_TEMPLATE = "🧵 What's new in {version}:\n\n{notes}"

REPLY_FUN_FACT = (
    "🐱 Fun fact: SheepCat stores every work log and AI summary entirely on "
    "your own machine — no cloud account, no telemetry, no subscriptions. "
    "Your data is yours, full stop. #PrivacyFirst #LocalAI"
)

# Maximum characters Bluesky allows per post
_BSKY_CHAR_LIMIT = 300


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_release_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    tag = os.environ.get("GITHUB_REF_NAME", "")
    return f"{server}/{repo}/releases/tag/{tag}"


def build_reply_text(version: str) -> str:
    """
    Return the text for the follow-up reply post.

    If GITHUB_RELEASE_BODY is set and non-empty, format a short summary of the
    release notes.  Otherwise fall back to a generic fun fact about SheepCat.
    """
    body = os.environ.get("GITHUB_RELEASE_BODY", "").strip()
    if not body:
        return REPLY_FUN_FACT

    prefix = REPLY_NOTES_TEMPLATE.format(version=version, notes="")
    # Budget for notes: total limit minus the static prefix, minus 1 for the ellipsis
    max_notes_len = _BSKY_CHAR_LIMIT - len(prefix) - 1
    if len(body) > max_notes_len:
        body = body[:max_notes_len] + "…"

    return REPLY_NOTES_TEMPLATE.format(version=version, notes=body)


def _make_strong_ref(
    response: "models.AppBskyFeedPost.CreateRecordResponse",
) -> "models.ComAtprotoRepoStrongRef.Main":
    return models.ComAtprotoRepoStrongRef.Main(cid=response.cid, uri=response.uri)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    handle = os.environ.get("BSKY_HANDLE", "")
    password = os.environ.get("BSKY_PASSWORD", "")

    if not handle or not password:
        print("Error: BSKY_HANDLE and BSKY_PASSWORD must be set.", file=sys.stderr)
        sys.exit(1)

    version = os.environ.get("GITHUB_REF_NAME", "unknown")
    release_url = build_release_url()

    announcement = POST_TEMPLATE.format(version=version, release_url=release_url)
    reply_text = build_reply_text(version)

    try:
        client = Client()
        client.login(handle, password)

        # ── Post 1: main announcement ──────────────────────────────────────
        root_post = client.send_post(text=announcement)
        print(f"Post 1 sent: {announcement}")

        # ── Post 2: reply in the same thread ──────────────────────────────
        root_ref = _make_strong_ref(root_post)
        reply_ref = models.AppBskyFeedPost.ReplyRef(parent=root_ref, root=root_ref)
        client.send_post(text=reply_text, reply_to=reply_ref)
        print(f"Post 2 (reply) sent: {reply_text}")

    except Exception as exc:  # Intentionally broad; KeyboardInterrupt/SystemExit are BaseException
        print(f"Bluesky post failed (non-fatal): {exc}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
