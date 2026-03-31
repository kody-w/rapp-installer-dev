# RAPP Brainstem — Release Pipeline Strategy

## Problem

Today, pushing to `main` on `rapp-installer` immediately affects every user who runs the one-liner install. There is no gate between "developer pushes a fix" and "all production users receive it." A broken commit = broken installs worldwide.

## Design Principles

- Users pulling from `main` should always get a known-good build.
- Every change must pass automated tests before it can reach users.
- Canary rollout catches runtime failures that tests miss.
- Rollback is a one-command operation, not a revert commit.

---

## Repo Layout

Three repos, each with a single responsibility:

| Repo | Purpose | Who writes to it |
|------|---------|------------------|
| `rapp-installer-dev` | Active development. All PRs land here. | Developers |
| `rapp-installer-canary` | Nightly pre-release. Opt-in early adopters. | CI only (automated promotion) |
| `rapp-installer` (production) | Stable release. Default install target. | CI only (manual promotion gate) |

```
Developer -> PR -> rapp-installer-dev  (develop)
                        |
                   [nightly CI]
                        |
                        v
                  rapp-installer-canary  (canary)
                        |
                   [manual promote]
                        |
                        v
                  rapp-installer  (production / main)
```

### Why separate repos instead of branches?

The install one-liner fetches from `raw.githubusercontent.com/<repo>/main/install.ps1`. Separate repos mean:
- Production users never need to change their command.
- Canary users just swap the repo name in the URL.
- No risk of accidentally merging a dev branch to main.
- GitHub Pages, permissions, and branch protection are isolated.

---

## Channels

### 1. Dev (`rapp-installer-dev`)

**Who uses it:** Developers testing changes locally.

**Install URL:**
```powershell
irm https://raw.githubusercontent.com/kody-w/rapp-installer-dev/main/install.ps1 | iex
```

**Rules:**
- All work happens here via feature branches + PRs.
- PRs require passing CI (see Test Gates below).
- `main` branch on this repo is "latest dev" — not stable, not shipped.
- VERSION uses pre-release suffix: `0.5.5-dev.3` (patch + commit count since last tag).

### 2. Canary (`rapp-installer-canary`)

**Who uses it:** Internal team, dogfooders, opt-in early adopters.

**Install URL:**
```powershell
irm https://raw.githubusercontent.com/kody-w/rapp-installer-canary/main/install.ps1 | iex
```

**Rules:**
- Populated by nightly CI job that copies from `rapp-installer-dev` main.
- Only promoted if all test gates pass.
- VERSION uses pre-release suffix: `0.5.5-canary.20260401`.
- Runs for at least 24h before eligible for production promotion.
- Canary users see a banner: `[canary] Report issues at <link>`.

### 3. Production (`rapp-installer`)

**Who uses it:** All public users (default install target).

**Install URL (unchanged):**
```powershell
irm https://raw.githubusercontent.com/kody-w/rapp-installer/main/install.ps1 | iex
```

**Rules:**
- Only updated via explicit promotion from canary.
- Promotion is a manual GitHub Action dispatch (human approves).
- VERSION is clean semver: `0.5.5`.
- Tagged with `v0.5.5` on promotion for rollback reference.

---

## Test Gates

Every promotion step must pass all gates. Tests run in CI (GitHub Actions).

### Gate 1 — Static (runs on every PR to dev)

| Test | What it catches |
|------|----------------|
| `bash -n install.sh` | Shell syntax errors |
| PowerShell `Parse` check on `install.ps1` | PS syntax errors |
| `tests/test_installer.sh` | Branding, paths, structure regressions |
| `python -m pytest test_local_agents.py` | Agent logic regressions |
| Shellcheck on `install.sh` | Shell portability issues |

### Gate 2 — Integration (runs nightly before canary promotion)

| Test | What it catches |
|------|----------------|
| Fresh install on Windows (GitHub Actions `windows-latest`) | Windows installer breakage |
| Fresh install on macOS (GitHub Actions `macos-latest`) | macOS installer breakage |
| Fresh install on Ubuntu (GitHub Actions `ubuntu-latest`) | Linux installer breakage |
| Upgrade from previous VERSION to current | Upgrade path breakage |
| `curl localhost:7071/health` after install | Server won't start |
| Python dep check (the `import flask, ...` test) | Dependency resolution failures |

Each integration test runs in an isolated VM with no pre-existing Python/Git — simulating a factory machine.

### Gate 3 — Canary soak (required before production promotion)

| Signal | Threshold |
|--------|-----------|
| Minimum soak time | 24 hours on canary |
| Install success rate (telemetry) | No increase in error rate vs. previous canary |
| Manual smoke test | At least one team member ran it end-to-end |

---

## Nightly Canary Promotion (Automated)

GitHub Actions workflow on `rapp-installer-dev`, scheduled cron `0 6 * * *` (6 AM UTC daily):

```
1. Check if dev/main has new commits since last canary promotion
2. If no new commits → skip
3. Run Gate 1 + Gate 2 tests
4. If all pass:
   a. Clone rapp-installer-canary
   b. Sync files from rapp-installer-dev/main
   c. Stamp VERSION with canary suffix
   d. Commit + push to rapp-installer-canary/main
   e. Post summary to team channel (Slack/Teams webhook)
5. If any fail:
   a. Post failure details to team channel
   b. Do NOT promote
```

## Production Promotion (Manual)

GitHub Actions `workflow_dispatch` on `rapp-installer-canary`:

```
1. Developer triggers "Promote to Production" action
2. CI verifies Gate 3 criteria (soak time, no open blockers)
3. Run Gate 1 + Gate 2 one more time against canary/main
4. If all pass:
   a. Clone rapp-installer (production)
   b. Sync files from rapp-installer-canary/main
   c. Strip pre-release suffix from VERSION
   d. Commit + push to rapp-installer/main
   e. Create git tag v{VERSION}
   f. Post release notification
5. If any fail → abort, notify
```

---

## Rollback

If a bad version reaches production:

**Option A — Fast rollback (< 1 minute):**
```bash
# On rapp-installer (production repo)
git revert HEAD
git push origin main
```
The next user who runs the one-liner gets the reverted version.

**Option B — Pin to known-good tag:**
```bash
git reset --hard v0.5.4
git push --force-with-lease origin main
```

**Option C — VERSION-based:** Because the installer checks `REMOTE_VERSION_URL` on every run, bumping VERSION back to a previous value effectively stops upgrades to the bad version. Users on the bad version will downgrade on next run.

---

## VERSION Flow

```
Dev:        0.5.5-dev.7
                |
Canary:     0.5.5-canary.20260401
                |
Production: 0.5.5
                |
Tag:        v0.5.5
```

The installer's `Compare-SemVer` function already strips pre-release suffixes for comparison, so canary users will correctly upgrade to production when the clean version is released.

---

## What Changes in the Installer

Minimal changes needed to support channels:

1. **Canary banner** — `install.ps1` / `install.sh` on the canary repo should print a one-line notice:
   ```
   [canary] You are running a pre-release build. Report issues: <url>
   ```

2. **Telemetry ping (opt-in)** — On install success/failure, POST a single event to a lightweight endpoint (e.g., GitHub Actions artifact or a simple Azure Function) with: `{version, os, success, error_code}`. No PII. This powers the canary soak gate.

3. **Channel flag in VERSION** — The installer already reads VERSION as a string. No code changes needed to handle `0.5.5-canary.20260401` — `Compare-SemVer` splits on `.` and compares numeric parts.

---

## Migration Path

To adopt this without disrupting current users:

1. **Week 1:** Create `rapp-installer-dev` repo, mirror current `rapp-installer` content. Start developing there.
2. **Week 1:** Create `rapp-installer-canary` repo, mirror current content. Share canary URL with internal team.
3. **Week 2:** Set up GitHub Actions for Gate 1 on `rapp-installer-dev` PRs.
4. **Week 2:** Set up nightly canary promotion workflow.
5. **Week 3:** Set up Gate 2 integration tests (fresh-install VMs).
6. **Week 3:** Set up production promotion workflow with manual gate.
7. **Week 4:** Lock down `rapp-installer` main branch — no direct pushes, CI-only.

Current users notice zero change. Their one-liner still works. The only difference is that `main` on the production repo now updates less frequently and more reliably.
