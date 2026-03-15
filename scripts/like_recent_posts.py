#!/usr/bin/env python3
"""
Like recent posts from a Bluesky account.

Authenticates using the project's Bluesky credentials and likes the most
recent posts from a target account, skipping any posts that are already
liked by the authenticated user.

Environment variables required:
    BSKY_HANDLE          – Bluesky handle of the account to authenticate as
                           (e.g. your-handle.bsky.social)
    BSKY_PASSWORD        – Bluesky App Password (not your login password)

Optional environment variables:
    BSKY_LIKE_ACCOUNT    – Handle of the account whose posts will be liked
                           (default: sheep-cat.bsky.social)
    BSKY_LIKE_LIMIT      – Maximum number of recent posts to like (default: 10)
"""
import os
import sys

from atproto import Client

_DEFAULT_LIKE_ACCOUNT = "sheep-cat.bsky.social"
_DEFAULT_LIKE_LIMIT = 10


def main() -> None:
    handle = os.environ.get("BSKY_HANDLE", "")
    password = os.environ.get("BSKY_PASSWORD", "")

    if not handle or not password:
        print("Error: BSKY_HANDLE and BSKY_PASSWORD must be set.", file=sys.stderr)
        sys.exit(1)

    like_account = os.environ.get("BSKY_LIKE_ACCOUNT", _DEFAULT_LIKE_ACCOUNT)
    try:
        like_limit = int(os.environ.get("BSKY_LIKE_LIMIT", _DEFAULT_LIKE_LIMIT))
    except ValueError:
        like_limit = _DEFAULT_LIKE_LIMIT

    try:
        client = Client()
        client.login(handle, password)

        response = client.get_author_feed(actor=like_account, limit=like_limit)
        feed_items = response.feed

        if not feed_items:
            print(f"No posts found for {like_account}.")
            return

        liked = 0
        skipped = 0
        for item in feed_items:
            post = item.post
            # Skip if already liked by the authenticated user
            if post.viewer and post.viewer.like:
                skipped += 1
                continue
            client.like(uri=post.uri, cid=post.cid)
            liked += 1

        print(
            f"Liked {liked} post(s) from {like_account} "
            f"(skipped {skipped} already-liked)."
        )

    except Exception as exc:  # Intentionally broad; KeyboardInterrupt/SystemExit are BaseException
        print(f"Like action for {like_account} failed (non-fatal): {exc}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
