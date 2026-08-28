#!/usr/bin/env python3
"""build_status_snapshot.py — Article XXIV (Static Data Covenant, kody-w/RAR CONSTITUTION.md).

Harvests, once, here in CI: the latest commit and the last 20 Actions runs for
each pipeline channel (dev / canary / production repo). Writes
docs/state/status_snapshot.json with each repo's data nested exactly as the
GitHub API returns it (`GET /repos/{repo}/commits?per_page=1` is a bare list;
`GET /repos/{repo}/actions/runs?per_page=20` is `{workflow_runs: [...]}`),
trimmed to only the fields docs/status.html actually reads (avatar URLs, node
IDs, etc. from the raw response would otherwise bloat the committed file for
no purpose). Parsing (`commits[0].sha`, `runs.workflow_runs[i].status`, ...)
is unchanged — only the fetch source moves from api.github.com to this file.

Replaces: docs/status.html's ghFetch() calls for commits and workflow runs
(6 unauthenticated api.github.com calls per visitor, every 2-minute auto-refresh).
getVersion() already reads raw.githubusercontent.com and is untouched — that's
already covenant-compliant.
"""

import datetime
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "state" / "status_snapshot.json"

REPOS = [
    "kody-w/rapp-installer",
    "kody-w/rapp-installer-canary",
    "kody-w/rapp-installer-dev",
]


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "rapp-installer-dev-status-build",
        "Accept": "application/vnd.github+json",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ! {url}: {e}", file=sys.stderr)
        return None


def slim_commit(c):
    """Keep only the fields status.html's getLatestCommit() reads, same nesting."""
    return {
        "sha": c.get("sha"),
        "commit": {
            "message": c.get("commit", {}).get("message"),
            "committer": {"date": c.get("commit", {}).get("committer", {}).get("date")},
            "author": {"name": c.get("commit", {}).get("author", {}).get("name")},
        },
    }


def slim_run(r):
    """Keep only the fields status.html's getWorkflowRuns() reads, same nesting."""
    return {
        "name": r.get("name"),
        "status": r.get("status"),
        "conclusion": r.get("conclusion"),
        "updated_at": r.get("updated_at"),
        "html_url": r.get("html_url"),
    }


def main():
    repos = {}
    for repo in REPOS:
        commits = fetch_json(f"https://api.github.com/repos/{repo}/commits?per_page=1")
        runs = fetch_json(f"https://api.github.com/repos/{repo}/actions/runs?per_page=20")
        commits = [slim_commit(c) for c in commits] if isinstance(commits, list) else []
        run_list = runs.get("workflow_runs", []) if isinstance(runs, dict) else []
        repos[repo] = {
            "commits": commits,
            "workflow_runs": {"workflow_runs": [slim_run(r) for r in run_list]},
        }
        print(f"  ✓ {repo}: {len(repos[repo]['commits'])} commit(s), "
              f"{len(repos[repo]['workflow_runs']['workflow_runs'])} run(s)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "schema": "rapp-installer-dev-status-snapshot/1",
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repos": repos,
    }, indent=2, sort_keys=True) + "\n")
    print(f"✓ {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
