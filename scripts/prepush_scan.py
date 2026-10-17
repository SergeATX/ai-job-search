#!/usr/bin/env python3
"""Pre-push privacy/secret scan. Scans the ADDED lines (and file names) of every commit about to be pushed.

Usage (normally via .githooks/pre-push):  prepush_scan.py <local_sha> <remote_sha>
Personal patterns (your name, email, phone, employers...) live in .git/privacy-patterns.txt - one regex per line,
case-insensitive. That file is inside .git, so it is never committed or pushed. Exit 1 blocks the push.
"""
import re
import subprocess
import sys
from pathlib import Path

ZERO = "0" * 40
SECRETS = [
    ("private key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("AWS key id", r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("GitHub token", r"\b(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("Anthropic/OpenAI key", r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}"),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}\b"),
    ("bearer/auth header", r"(?i)authorization['\"]?\s*[:=]\s*['\"]?(bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"),
    ("secret assignment", r"(?i)\b(api[_-]?key|secret|passwd|password|token|client_secret)\b['\"]?\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
    ("email address", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}\b"),
    ("US phone number", r"(?<!\d)(\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
    ("home directory path", r"(/Users/|/home/)[A-Za-z0-9._-]+/"),
    ("macOS volume path", r"/Volumes/[^/\s]+/Users/"),
]
EMAIL_OK = re.compile(r"(@example\.(com|org)|@users\.noreply\.github\.com|noreply@anthropic\.com|you@|@localhost)")
BAD_PATHS = re.compile(
    r"(^|/)(profiles/|memory/|documents/(cv|linkedin|diplomas|references|applications)/|\.env|.*\.(db|sqlite3?|pem|key|p12|pfx)$|"
    r"cv/main_(?!example)|cover_letters/cover_(?!.*example)|job_search_tracker\.csv|settings\.local\.json|seen_jobs\.json)"
)


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def personal_patterns():
    f = Path(git("rev-parse", "--git-dir").strip()) / "privacy-patterns.txt"
    if not f.exists():
        print("prepush-scan: WARNING no .git/privacy-patterns.txt - personal-name checks are OFF", file=sys.stderr)
        return []
    return [("personal pattern", l.strip()) for l in f.read_text().splitlines() if l.strip() and not l.startswith("#")]


def commits(local, remote):
    if local == ZERO:
        return []
    if remote == ZERO:  # new branch: everything not already on any remote
        return git("rev-list", local, "--not", "--remotes").split()
    return git("rev-list", f"{remote}..{local}").split()


def main():
    local, remote = sys.argv[1], sys.argv[2]
    rules = [(n, re.compile(p, re.I if n == "personal pattern" else 0)) for n, p in SECRETS + personal_patterns()]
    findings = []
    for c in commits(local, remote):
        for path in git("diff-tree", "--no-commit-id", "--name-only", "-r", "--root", c).split("\n"):
            if path and BAD_PATHS.search(path):
                findings.append((c[:8], path, "forbidden path", ""))
        cur = None
        for line in git("show", "--format=", "--unified=0", "--no-color", c).split("\n"):
            if line.startswith("+++ b/"):
                cur = line[6:]
            elif line.startswith("+") and not line.startswith("+++"):
                text = line[1:]
                for name, rx in rules:
                    m = rx.search(text)
                    if not m:
                        continue
                    if name == "email address" and EMAIL_OK.search(m.group(0)):
                        continue
                    findings.append((c[:8], cur, name, text.strip()[:90]))
    if findings:
        print("\nprepush-scan: BLOCKED - possible personal info / secrets in commits being pushed:\n", file=sys.stderr)
        for c, path, name, text in findings[:40]:
            print(f"  {c}  {path}: {name}  {text}", file=sys.stderr)
        print(f"\n{len(findings)} finding(s). Fix them (or rewrite the commits), then push again. "
              "Emergency bypass: git push --no-verify (only if you reviewed every finding).", file=sys.stderr)
        sys.exit(1)
    print("prepush-scan: clean")


if __name__ == "__main__":
    main()
