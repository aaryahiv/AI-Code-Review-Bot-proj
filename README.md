# 🤖 AI Code Review Bot

A GitHub Action that automatically reviews Python pull requests using Claude (Anthropic). On every PR touching `.py` files, it fetches the diff, sends it to Claude, and posts inline review comments with severity labels.

---

## Features

- 🔴 **Critical** — bugs, security holes, data loss risks
- 🟡 **Warning** — performance issues, bad patterns, missing error handling
- 🔵 **Suggestion** — style, readability, minor improvements
- Posts **inline comments** on the exact lines changed
- Posts a **summary comment** on the PR for quick scanning

---

## Setup (5 minutes)

### 1. Clone / copy into your repo

Copy `.github/workflows/code-review.yml` and `scripts/review.py` into your repository.

### 2. Add your Anthropic API key as a GitHub Secret

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your key from [console.anthropic.com](https://console.anthropic.com)

> `GITHUB_TOKEN` is provided automatically by GitHub Actions — no setup needed.

### 3. Push and open a PR

Any PR that modifies `.py` files will trigger the workflow. You'll see review comments appear within ~30 seconds.

---

## Project Structure
