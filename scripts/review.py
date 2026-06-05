"""
AI Code Reviewer — powered by Claude
Fetches the PR diff, sends it to Claude, and posts inline review comments.
"""

import os
import sys
import re
import anthropic
from github import Github, Auth

# ── Config ────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GITHUB_TOKEN      = os.environ["GITHUB_TOKEN"]
REPO_NAME         = os.environ["REPO_NAME"]
PR_NUMBER         = int(os.environ["PR_NUMBER"])
BASE_SHA          = os.environ["BASE_SHA"]
HEAD_SHA          = os.environ["HEAD_SHA"]

MODEL             = "claude-sonnet-4-5"
MAX_DIFF_CHARS    = 12_000   # truncate huge diffs to stay within context limits

SYSTEM_PROMPT = """You are an expert Python code reviewer. Your job is to review PR diffs and give concise, actionable feedback.

For each issue you find, output a block in this exact format:

FILE: <filename>
LINE: <line number in the new file>
SEVERITY: <critical | warning | suggestion>
COMMENT: <your review comment, 1-3 sentences>

Severity guide:
- critical   → bugs, security holes, data loss risks
- warning    → performance issues, bad patterns, missing error handling
- suggestion → style, readability, minor improvements

Rules:
- Only comment on lines that were ADDED (starting with +) in the diff.
- Be specific — reference the actual code.
- Skip trivial whitespace or comment-only changes.
- If the code looks great, output: LGTM: <brief praise>
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_pr_diff(repo, pr) -> str:
    """Return the unified diff for all Python files changed in this PR."""
    comparison = repo.compare(BASE_SHA, HEAD_SHA)
    chunks = []
    for f in comparison.files:
        if f.filename.endswith(".py") and f.patch:
            chunks.append(f"### {f.filename}\n{f.patch}")
    return "\n\n".join(chunks)[:MAX_DIFF_CHARS]


def parse_review(text: str) -> list[dict]:
    """Parse Claude's structured output into a list of comment dicts."""
    comments = []
    blocks = re.split(r"(?=FILE:)", text.strip())
    for block in blocks:
        if block.strip().startswith("LGTM"):
            comments.append({"lgtm": True, "message": block.strip()})
            continue
        file_m     = re.search(r"FILE:\s*(.+)",      block)
        line_m     = re.search(r"LINE:\s*(\d+)",     block)
        severity_m = re.search(r"SEVERITY:\s*(\w+)", block)
        comment_m  = re.search(r"COMMENT:\s*(.+)",   block, re.DOTALL)
        if file_m and line_m and severity_m and comment_m:
            comments.append({
                "lgtm":     False,
                "file":     file_m.group(1).strip(),
                "line":     int(line_m.group(1)),
                "severity": severity_m.group(1).strip(),
                "message":  comment_m.group(1).strip(),
            })
    return comments


SEVERITY_EMOJI = {
    "critical":   "🔴",
    "warning":    "🟡",
    "suggestion": "🔵",
}


def post_comments(pr, comments: list[dict], diff: str) -> None:
    """Post inline PR review comments via the GitHub API."""
    posted = 0
    summary_lines = ["## 🤖 AI Code Review\n"]

    for c in comments:
        if c.get("lgtm"):
            summary_lines.append(f"✅ {c['message']}")
            continue

        emoji = SEVERITY_EMOJI.get(c["severity"], "⚪")
        body  = f"{emoji} **{c['severity'].upper()}**\n\n{c['message']}"

        try:
            pr.create_review_comment(
                body=body,
                commit=pr.get_commits().reversed[0],
                path=c["file"],
                line=c["line"],
            )
            posted += 1
            summary_lines.append(f"- {emoji} `{c['file']}` line {c['line']}: {c['message'][:80]}…")
        except Exception as e:
            summary_lines.append(f"- {emoji} `{c['file']}` line {c['line']}: {c['message'][:80]}… *(inline comment failed: {e})*")

    summary_lines.append(f"\n_{posted} inline comment(s) posted._")
    pr.create_issue_comment("\n".join(summary_lines))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    gh = Github(auth=Auth.Token(GITHUB_TOKEN))
    repo = gh.get_repo(REPO_NAME)
    pr   = repo.get_pull(PR_NUMBER)

    print(f"Reviewing PR #{PR_NUMBER}: {pr.title}")

    diff = get_pr_diff(repo, pr)
    if not diff.strip():
        print("No Python changes found — skipping review.")
        pr.create_issue_comment("## 🤖 AI Code Review\n\nNo Python files changed in this PR.")
        sys.exit(0)

    print(f"Sending {len(diff)} chars of diff to Claude…")

    client   = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Please review the following Python PR diff:\n\n{diff}",
            }
        ],
    )

    review_text = response.content[0].text
    print("Claude response:\n", review_text)

    comments = parse_review(review_text)
    print(f"Parsed {len(comments)} comment(s).")

    post_comments(pr, comments, diff)
    print("Done!")


if __name__ == "__main__":
    main()