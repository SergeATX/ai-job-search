#!/usr/bin/env python3
"""PII scanner for git. Flags added lines (and commit messages) containing personal data.

Modes:
  --staged                 scan `git diff --cached` (pre-commit)
  --msg FILE               scan a commit message file (commit-msg)
  --push-stdin             read pre-push lines "<lref> <lsha> <rref> <rsha>" from stdin, scan those commits
  --range BASE..HEAD       scan an explicit commit range
  --tracked                scan every tracked file in HEAD (audit; prints counts by kind)

Detects: emails, phone numbers, street addresses, SSN-like and card-like numbers (Luhn), and every term in
~/.config/jobcatalog/pii-terms.txt (override with $PII_TERMS_FILE), matched case-insensitively on word boundaries.
Allowlist: <repo>/.pii-allowlist, lines `path: <glob>` or `literal: <string>`; `#` starts a comment.
Matched values are masked in output. Exit 1 blocks.
"""
import fnmatch
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ZERO = "0" * 40
RULES = [
    ("email", re.compile(r"(?<![\w.%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<![\w.])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?![\w-])")),
    ("phone-intl", re.compile(r"(?<![\w.])\+\d{1,3}[ .-]?\(?\d{1,4}\)?(?:[ .-]?\d{2,4}){2,4}(?![\w-])")),
    ("address", re.compile(r"\b\d{1,6}\s+(?:[A-Z][a-z]+\.?\s+){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\b")),
    ("ssn", re.compile(r"(?<![\w-])\d{3}-\d{2}-\d{4}(?![\w-])")),
    ("card", re.compile(r"(?<![\w.-])\d(?:[ -]?\d){12,18}(?![\w-])")),
]


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def luhn(s):
    d = [int(c) for c in s if c.isdigit()]
    if not 13 <= len(d) <= 19:
        return False
    t = 0
    for i, x in enumerate(reversed(d)):
        if i % 2:
            x *= 2
            if x > 9:
                x -= 9
        t += x
    return t % 10 == 0


def mask(v):
    v = v.strip()
    if len(v) <= 4:
        return "*" * len(v)
    return v[0] + "*" * (len(v) - 2) + v[-1]


def load_terms():
    f = Path(os.environ.get("PII_TERMS_FILE") or Path.home() / ".config/jobcatalog/pii-terms.txt")
    if not f.exists():
        print("pii-scan: WARNING pii-terms.txt missing - term check skipped", file=sys.stderr)
        return []
    out = []
    for l in f.read_text().splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            out.append(("term", re.compile(r"(?<!\w)" + re.escape(l) + r"(?!\w)", re.I)))
    return out


def load_allow(root):
    globs, lits = [], []
    f = Path(root) / ".pii-allowlist"
    if f.exists():
        for l in f.read_text().splitlines():
            l = l.split("  #")[0].strip()
            if l.startswith("path:"):
                globs.append(l[5:].strip())
            elif l.startswith("literal:"):
                lits.append(l[8:].strip())
    return globs, lits


class Scanner:
    def __init__(self, root):
        self.rules = RULES + load_terms()
        self.globs, self.lits = load_allow(root)
        self.findings = []

    def path_ok(self, path):
        return any(fnmatch.fnmatch(path, g) for g in self.globs)

    def line(self, where, ln, text):
        for kind, rx in self.rules:
            for m in rx.finditer(text):
                v = m.group(0)
                if kind == "card" and not luhn(v):
                    continue
                if any(l in v or v in l for l in self.lits):
                    continue
                self.findings.append((where, ln, kind, mask(v)))

    def diff(self, text, label=""):
        path, ln = None, 0
        for raw in text.split("\n"):
            if raw.startswith("+++ "):
                path = raw[4:]
                path = path[2:] if path.startswith("b/") else None if path == "/dev/null" else path
            elif raw.startswith("@@"):
                m = re.search(r"\+(\d+)", raw)
                ln = int(m.group(1)) - 1 if m else 0
            elif raw.startswith("+") and path:
                ln += 1
                if not self.path_ok(path):
                    self.line(f"{label}{path}", ln, raw[1:])
            elif not raw.startswith("-"):
                ln += 1

    def message(self, text, label):
        for i, l in enumerate(text.split("\n"), 1):
            if not l.startswith("#"):
                self.line(f"{label}<commit-message>", i, l)

    def commits(self, shas):
        for c in shas:
            self.message(git("show", "-s", "--format=%B", c), c[:8] + " ")
            self.diff(git("show", "--format=", "--unified=0", "--no-color", c), c[:8] + " ")


def push_commits(stdin):
    out = []
    for l in stdin.splitlines():
        p = l.split()
        if len(p) < 4 or p[1] == ZERO:
            continue
        lsha, rsha = p[1], p[3]
        out += git("rev-list", lsha, "--not", "--remotes").split() if rsha == ZERO else git("rev-list", f"{rsha}..{lsha}").split()
    return list(dict.fromkeys(out))


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    root = git("rev-parse", "--show-toplevel").strip()
    s = Scanner(root)
    if a[0] == "--staged":
        s.diff(git("diff", "--cached", "--unified=0", "--no-color", "--diff-filter=ACMR"))
    elif a[0] == "--msg":
        s.message(Path(a[1]).read_text(), "")
    elif a[0] == "--push-stdin":
        s.commits(push_commits(sys.stdin.read()))
    elif a[0] == "--range":
        s.commits(git("rev-list", a[1]).split())
    elif a[0] == "--tracked":
        for p in git("ls-files").split("\n"):
            if p and not s.path_ok(p):
                try:
                    for i, l in enumerate(Path(root, p).read_text().split("\n"), 1):
                        s.line(p, i, l)
                except (UnicodeDecodeError, OSError):
                    pass
        for k, n in sorted(Counter(f[2] for f in s.findings).items()):
            print(f"{k}: {n}")
        print(f"total: {len(s.findings)}")
        return
    else:
        sys.exit(__doc__)
    if s.findings:
        print("\npii-scan: BLOCKED - possible personal info in what you are committing/pushing:\n", file=sys.stderr)
        for w, ln, k, m in s.findings[:40]:
            print(f"  {w}:{ln}  [{k}]  {m}", file=sys.stderr)
        print(f"\n{len(s.findings)} finding(s). Remove the data, or if it is safe add a reviewed entry to .pii-allowlist. "
              "Bypass (only after review): --no-verify.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
