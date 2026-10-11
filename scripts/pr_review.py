#!/usr/bin/env python3
"""Pre-merge review stamp: prove /ce-code-review + /findings-review ran on THIS code.

    uv run python scripts/pr_review.py stamp --fixed 3 --deferred 1 --refuted 2
        → prints the "## Code review" block to paste into the PR body.
    uv run python scripts/pr_review.py check --pr 123            # local, via gh
    uv run python scripts/pr_review.py check --body-file body.md  # CI / offline
        → exit 0 if the PR body's stamp matches the PR's current changes.

The stamp carries a patch fingerprint: ``git patch-id --stable`` over the PR's
own diff (merge-base with the base branch → head), generated files excluded.
A clean rebase keeps it; any real code change after the review (new commits,
conflict resolutions) breaks it, so the review must be re-run on the delta and
the stamp regenerated. Docs-only PRs (Markdown files only, outside the agent
instructions CLAUDE.md / .claude/ / .github/) are exempt.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

MARK = "<!-- mm-review"
GENERATED = ("web/openapi.json", "web/src/core/api/", "extension/src/stores.js")
# Markdown that steers agents or CI is code for this rule, never "docs-only".
NOT_DOCS = ("CLAUDE.md", ".claude/", ".github/")
STAMP_RE = re.compile(
    r"<!-- mm-review v1 patch=(?P<patch>[0-9a-f]{40}) -->.*?"
    r"`/ce-code-review`: run.*?`/findings-review`: run",
    re.S,
)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def _changed(base: str, head: str) -> list[str]:
    mb = _git("merge-base", base, head).strip()
    # --no-renames lists both sides of a rename, so code renamed to .md still counts as code.
    return [p for p in _git("diff", "--name-only", "--no-renames", mb, head).splitlines() if p]


def docs_only(base: str, head: str) -> bool:
    files = _changed(base, head)
    return bool(files) and all(f.endswith(".md") and not f.startswith(NOT_DOCS) for f in files)


def patch_id(base: str, head: str) -> str:
    """Fingerprint of the PR's own changes, independent of where it is based."""
    mb = _git("merge-base", base, head).strip()
    excludes = [f":(exclude){g}" for g in GENERATED]
    # -U0: hash only the changed lines, so a rebase that moves neighbouring lines keeps the stamp.
    diff = _git("diff", "--binary", "-U0", mb, head, "--", ".", *excludes)
    if not diff.strip():
        return "0" * 40
    # --verbatim: whitespace counts (an indentation change is a code change in Python).
    out = subprocess.run(["git", "patch-id", "--verbatim"], input=diff, check=True,
                         capture_output=True, text=True).stdout.split()
    return out[0] if out else "0" * 40


def stamp(args) -> int:
    pid = patch_id(args.base, args.head)
    print(f"## Code review\n"
          f"<!-- mm-review v1 patch={pid} -->\n"
          f"- `/ce-code-review`: run\n"
          f"- `/findings-review`: run — fixed {args.fixed} · deferred {args.deferred} · refuted {args.refuted}\n"
          f"- Reviewed changes: `{pid[:12]}` (generated with `scripts/pr_review.py stamp`)")
    return 0


def _pr_body_and_refs(pr: int) -> tuple[str, str, str]:
    data = json.loads(subprocess.run(
        ["gh", "pr", "view", str(pr), "--json", "body,baseRefName,headRefOid"],
        check=True, capture_output=True, text=True).stdout)
    _git("fetch", "-q", "origin", data["baseRefName"], data["headRefOid"])
    return data["body"] or "", f"origin/{data['baseRefName']}", data["headRefOid"]


def check(args) -> int:
    if args.pr:
        body, base, head = _pr_body_and_refs(args.pr)
    else:
        body = open(args.body_file).read() if args.body_file else os.environ.get("PR_BODY", "")
        base, head = args.base, args.head
    if docs_only(base, head):
        print("review check: docs-only PR — exempt")
        return 0
    stamps = list(STAMP_RE.finditer(body))
    m = stamps[-1] if stamps else None  # the newest stamp wins if an old one was left behind
    if not m:
        print("review check: FAIL — the PR body has no '## Code review' stamp. Run /ce-code-review, "
              "then /findings-review, fix what survives, then paste the output of "
              "`uv run python scripts/pr_review.py stamp --fixed N --deferred N --refuted N`.")
        return 1
    want = patch_id(base, head)
    if m.group("patch") != want:
        print(f"review check: FAIL — the stamp was made for different code (stamp {m.group('patch')[:12]}, "
              f"now {want[:12]}). Review what changed since, then regenerate the stamp.")
        return 1
    print(f"review check: OK — reviewed changes {want[:12]}")
    if args.pr:
        # Merge exactly what was checked: refuses if the head moved since.
        print(f"merge with: gh pr merge {args.pr} --squash --match-head-commit {head}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stamp", help="print the Code review block for the PR body")
    for k in ("fixed", "deferred", "refuted"):
        s.add_argument(f"--{k}", type=int, required=True)
    c = sub.add_parser("check", help="verify a PR body's stamp matches its current changes")
    c.add_argument("--pr", type=int)
    c.add_argument("--body-file")
    for sp in (s, c):
        sp.add_argument("--base", default="origin/main")
        sp.add_argument("--head", default="HEAD")
    a = p.parse_args()
    return stamp(a) if a.cmd == "stamp" else check(a)


if __name__ == "__main__":
    sys.exit(main())
