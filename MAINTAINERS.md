# SheepCat — Maintainer Guide

This document contains information for repository maintainers, covering manual setup steps that cannot be automated.

---

## Bluesky Release Promotion

When a new GitHub Release is published, the `Bluesky Release Promotion` workflow (`bluesky-promo.yml`) automatically posts an announcement to Bluesky via the [atproto](https://atproto.com) SDK.

Before this workflow can run you must add two repository secrets.

### Adding the required secrets

1. Navigate to **Settings → Secrets and variables → Actions** in the GitHub repository.

2. Click **New repository secret** and create the following secrets:

   | Secret name     | Value                                                                                   |
   |-----------------|-----------------------------------------------------------------------------------------|
   | `BSKY_HANDLE`   | Your Bluesky handle (e.g. `your-handle.bsky.social`)                                   |
   | `BSKY_PASSWORD` | A dedicated **App Password** generated inside your Bluesky account settings (see below) |

### Generating a Bluesky App Password

> ⚠️ **Important:** Do **not** use your primary Bluesky login password for this secret.  
> Bluesky supports dedicated *App Passwords* that are scoped only to API access and can be revoked independently of your main account password.

Steps to generate an App Password:

1. Log in to [bsky.app](https://bsky.app).
2. Go to **Settings → Privacy and Security → App Passwords**.
3. Click **Add App Password**, give it a descriptive name (e.g. `sheepcat-github-actions`), and confirm.
4. Copy the generated password — it is shown only once.
5. Paste it as the value for the `BSKY_PASSWORD` repository secret.

### Verifying the setup

After adding the secrets, publish a GitHub Release (or re-run the workflow manually from the **Actions** tab) to confirm that the post is sent successfully.  
If the Bluesky API is unavailable, the workflow step exits cleanly with code `0` so the overall release workflow is not marked as failed.
