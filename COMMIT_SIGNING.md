# 🔐 Commit Signing Guide

Signed commits are **required** for all contributions to the `main` branch of SheepCat.  
This guide explains what commit signing is, why it matters, and how to set it up on your machine.

---

## 📋 Table of Contents

- [Why Sign Commits?](#why-sign-commits)
- [Choosing a Signing Method](#choosing-a-signing-method)
- [Method 1: GPG Signing](#method-1-gpg-signing)
  - [Windows](#windows-gpg)
  - [macOS](#macos-gpg)
  - [Linux](#linux-gpg)
  - [Add Your GPG Key to GitHub](#add-your-gpg-key-to-github)
  - [Configure Git to Use GPG](#configure-git-to-use-gpg)
- [Method 2: SSH Signing](#method-2-ssh-signing)
  - [Generate or Reuse an SSH Key](#generate-or-reuse-an-ssh-key)
  - [Add Your SSH Key to GitHub](#add-your-ssh-key-to-github)
  - [Configure Git to Use SSH Signing](#configure-git-to-use-ssh-signing)
- [Enable Auto-Signing for Every Commit](#enable-auto-signing-for-every-commit)
- [Verifying a Signed Commit](#verifying-a-signed-commit)
- [GitHub Desktop & GUI Clients](#github-desktop--gui-clients)
- [Troubleshooting](#troubleshooting)

---

## Why Sign Commits?

When you push a commit to GitHub, anyone could claim to be you by setting your name and email in their local Git config.  
**Commit signing** uses cryptographic keys to prove that a commit genuinely came from you:

- 🛡️ **Authenticity** — GitHub shows a green **Verified** badge next to your commits.
- 🔒 **Integrity** — Reviewers and automated tooling can trust the commit has not been tampered with.
- ✅ **Branch protection** — The `main` branch requires signed commits, so unsigned commits will be rejected.

---

## Choosing a Signing Method

| Method | Best for | Notes |
|--------|----------|-------|
| **GPG** | All platforms, traditional approach | Widely supported, more steps to set up |
| **SSH** | Users who already have an SSH key set up | Simpler setup, supported since Git 2.34 |

Both methods produce a **Verified** badge on GitHub. Choose whichever feels easier.

---

## Method 1: GPG Signing

### Windows (GPG)

1. **Download and install [Gpg4win](https://www.gpg4win.org/)** — this includes the `gpg` command-line tool and the Kleopatra GUI.

2. Open **Git Bash** or a regular Command Prompt and confirm GPG is available:

   ```bash
   gpg --version
   ```

3. Continue to [Generate a GPG key](#generate-a-gpg-key).

---

### macOS (GPG)

1. Install GPG via Homebrew:

   ```bash
   brew install gnupg
   ```

2. Optionally install the GPG Suite GUI:

   ```bash
   brew install --cask gpg-suite
   ```

3. Confirm GPG is available:

   ```bash
   gpg --version
   ```

4. Continue to [Generate a GPG key](#generate-a-gpg-key).

---

### Linux (GPG)

GPG is usually pre-installed. If not:

```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install gnupg

# Fedora / RHEL
sudo dnf install gnupg2

# Arch
sudo pacman -S gnupg
```

Confirm GPG is available:

```bash
gpg --version
```

---

### Generate a GPG Key

Run the following command and follow the prompts:

```bash
gpg --full-generate-key
```

Recommended settings when prompted:

| Prompt | Recommended choice |
|--------|--------------------|
| Key type | `RSA and RSA` (option 1) |
| Key size | `4096` |
| Expiry | `0` (does not expire) or `2y` (2 years) |
| Real name | Your name as it appears on GitHub |
| Email | The email address linked to your GitHub account |
| Passphrase | Choose a strong passphrase — you will be asked for it when signing |

> ⚠️ The email address must match a verified email on your GitHub account, otherwise the **Verified** badge will not appear.

List your keys to find the key ID:

```bash
gpg --list-secret-keys --keyid-format=long
```

Example output:

```
sec   rsa4096/3AA5C34371567BD2 2024-01-01 [SC]
      D3B08B9F2A3C4E5F6A7B8C9D3AA5C34371567BD2
uid   [ultimate] Your Name <you@example.com>
```

Your **key ID** is the part after the `/` on the `sec` line — in this example `3AA5C34371567BD2`.

---

### Add Your GPG Key to GitHub

1. Export your public key (replace `<KEY_ID>` with your actual key ID):

   ```bash
   gpg --armor --export <KEY_ID>
   ```

2. Copy the entire output, including the `-----BEGIN PGP PUBLIC KEY BLOCK-----` header and footer.

3. Go to **GitHub → Settings → SSH and GPG keys → New GPG key**.

4. Paste the key and click **Add GPG key**.

---

### Configure Git to Use GPG

Tell Git which key to use and enable signing:

```bash
# Set the signing key (replace <KEY_ID> with yours)
git config --global user.signingkey <KEY_ID>

# Sign all commits automatically
git config --global commit.gpgsign true
```

**Windows only** — tell Git where to find the GPG executable:

```bash
git config --global gpg.program "C:/Program Files (x86)/GnuPG/bin/gpg.exe"
```

> Adjust the path if you installed Gpg4win to a different location.

---

## Method 2: SSH Signing

SSH signing is simpler if you already have an SSH key. Requires **Git 2.34 or later** — check with `git --version`.

### Generate or Reuse an SSH Key

If you already use an SSH key to authenticate with GitHub, you can reuse it for signing.  
To create a new key:

```bash
# Ed25519 (recommended)
ssh-keygen -t ed25519 -C "you@example.com"

# RSA fallback for older systems
ssh-keygen -t rsa -b 4096 -C "you@example.com"
```

Your public key is in `~/.ssh/id_ed25519.pub` (or `~/.ssh/id_rsa.pub`).

---

### Add Your SSH Key to GitHub

1. Copy your public key:

   ```bash
   # macOS
   cat ~/.ssh/id_ed25519.pub | pbcopy

   # Linux
   cat ~/.ssh/id_ed25519.pub | xclip -selection clipboard

   # Windows (Git Bash)
   cat ~/.ssh/id_ed25519.pub | clip
   ```

2. Go to **GitHub → Settings → SSH and GPG keys → New SSH key**.

3. Set the **Key type** to **Signing Key** (not *Authentication Key*) and paste your public key.

4. Click **Add SSH key**.

> If you already added this key as an Authentication Key, you need to add it again as a **Signing Key** — GitHub allows the same key for both purposes.

---

### Configure Git to Use SSH Signing

```bash
# Tell Git to use SSH for signing
git config --global gpg.format ssh

# Set the path to your public key
git config --global user.signingkey ~/.ssh/id_ed25519.pub

# Sign all commits automatically
git config --global commit.gpgsign true
```

Create an **allowed signers** file so Git can verify signatures locally:

```bash
# Create the file (adjust the path and key as needed)
echo "you@example.com $(cat ~/.ssh/id_ed25519.pub)" >> ~/.ssh/allowed_signers

# Register it with Git
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
```

> Replace `you@example.com` with the email address that matches your Git `user.email` setting.

---

## Enable Auto-Signing for Every Commit

Whether you chose GPG or SSH, run this command once to sign **every** future commit automatically:

```bash
git config --global commit.gpgsign true
```

You can verify your global Git settings at any time:

```bash
git config --global --list | grep sign
```

Expected output (GPG example):

```
commit.gpgsign=true
user.signingkey=3AA5C34371567BD2
```

---

## Verifying a Signed Commit

After making a commit you can check it was signed correctly:

```bash
git log --show-signature -1
```

You should see output similar to:

```
commit abc1234...
gpg: Signature made Mon 01 Jan 2024
gpg:                using RSA key 3AA5C34371567BD2
gpg: Good signature from "Your Name <you@example.com>" [ultimate]
Author: Your Name <you@example.com>
Date:   Mon Jan 01 09:00:00 2024 +0000

    Your commit message
```

On GitHub, navigate to the commit and look for the green **Verified** badge next to the commit hash.

---

## GitHub Desktop & GUI Clients

### GitHub Desktop

GitHub Desktop does not currently support commit signing natively. You have two options:

1. **Sign commits from the terminal** alongside GitHub Desktop — use `git commit -S -m "your message"` in a terminal window pointing at the same repository.
2. **Enable GPG agent caching** so that Desktop-initiated commits are signed transparently via the GPG agent running in the background (GPG method only).

For option 2, add the following to `~/.gnupg/gpg-agent.conf`:

```
default-cache-ttl 3600
max-cache-ttl 86400
```

Then restart the agent:

```bash
gpgconf --kill gpg-agent
gpgconf --launch gpg-agent
```

### VS Code / JetBrains / Other IDEs

Most IDEs invoke Git under the hood, so if you have set `commit.gpgsign true` globally they will pick it up automatically. If you are prompted for your GPG passphrase, enter it — it will usually be cached for the duration of your session.

---

## Troubleshooting

### "error: gpg failed to sign the data"

This is the most common error. Try these steps:

1. Make sure `gpg` is on your PATH:

   ```bash
   which gpg    # macOS/Linux
   where gpg    # Windows
   ```

2. Test signing directly:

   ```bash
   echo "test" | gpg --clearsign
   ```

3. If you see `Inappropriate ioctl for device`, add the following to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

   ```bash
   export GPG_TTY=$(tty)
   ```

4. Reload your shell:

   ```bash
   source ~/.bashrc   # or ~/.zshrc
   ```

---

### "No secret key" / "secret key not available"

Your key ID in Git doesn't match any key in your keyring. Verify:

```bash
gpg --list-secret-keys --keyid-format=long
git config --global user.signingkey
```

Make sure both values match.

---

### Commit shows "Unverified" on GitHub

- The email on your GPG/SSH key must match a **verified** email in your GitHub account settings.
- Go to **GitHub → Settings → Emails** and verify the email you used when generating the key.

---

### GPG passphrase prompt doesn't appear (Windows)

Set the GPG TTY and ensure `gpg-agent` is running:

```bash
# In Git Bash
export GPG_TTY=$(tty)
gpg-connect-agent /bye
```

---

### SSH signing: "Signing failed: agent refused operation"

Make sure your key is loaded in the SSH agent:

```bash
ssh-add ~/.ssh/id_ed25519
```

---

## Need More Help?

- [GitHub Docs — Signing commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)
- [GitHub Docs — Generating a new GPG key](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key)
- [GitHub Docs — SSH commit signing](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification#ssh-commit-signature-verification)
- Open an issue in this repository if you get stuck: [GitHub Issues](https://github.com/Chadders13/SheepCat-TrackingMyWork/issues)

---

*Made with 💙 for the neurodivergent community*
