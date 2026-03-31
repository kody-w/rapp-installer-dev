# RAPP Installer — Constitution

This document defines the non-negotiable rules for how code reaches users. Every contributor and AI agent working in this repo must follow these principles. No exceptions.

## North Star

**Production must always work.** A user running the one-liner install on a factory machine should succeed 100% of the time. Every decision flows from this.

## The Pipeline Is the Only Path to Production

```
rapp-installer-dev  →  rapp-installer-canary  →  rapp-installer
     (develop)            (nightly soak)           (production)
```

1. **All changes land in `rapp-installer-dev`.** No exceptions. Not "just a small fix." Not "just docs." Everything.
2. **Canary is promoted automatically.** Every night, CI runs Gate 1 (syntax, unit tests) and Gate 2 (fresh install on Windows, macOS, Linux). If both pass, dev/main is pushed to canary.
3. **Production is promoted manually.** A human triggers the "Promote to Production" workflow on the canary repo. It requires typing PROMOTE to confirm. Canary must have soaked for at least 24 hours.
4. **Direct pushes to production are forbidden.** The `rapp-installer` main branch is protected. Only CI can write to it.

## What This Means in Practice

- **"Can I just push this one fix to production?"** No. Push it to dev, let it flow through canary, promote when it soaks.
- **"The fix is tested and verified."** Good. It will reach production in ~48 hours (nightly promotion + 24h soak). That's the price of stability.
- **"It's an emergency — users are broken right now."** Use rollback (see below) to restore the last known-good version immediately. Then fix forward through the pipeline.
- **"It's just a README change."** Still goes through the pipeline. The pipeline is cheap. Broken installs are expensive.

## Rollback Over Hotfix

If production is broken, the first response is always rollback — not a rushed fix:

```bash
# Revert to last known-good state
git clone https://github.com/kody-w/rapp-installer.git && cd rapp-installer
git revert HEAD && git push origin main
```

Or pin to a tagged release:
```bash
git reset --hard v0.5.4 && git push --force-with-lease origin main
```

Then fix forward through dev → canary → production at normal pace.

## The Three Repos

| Repo | Purpose | Who writes | Who reads |
|------|---------|-----------|-----------|
| `rapp-installer-dev` | Active development | Developers via PRs | Developers |
| `rapp-installer-canary` | Pre-release soak | CI only | Internal team, dogfooders |
| `rapp-installer` | Stable release | CI only | All public users |

## Install Channels

The `RAPP_CHANNEL` env var selects which repo the installer clones from:

```powershell
# Development (latest, possibly broken)
$env:RAPP_CHANNEL="rapp-installer-dev"; irm https://raw.githubusercontent.com/kody-w/rapp-installer-dev/main/install.ps1 | iex

# Canary (nightly pre-release, soaking)
$env:RAPP_CHANNEL="rapp-installer-canary"; irm https://raw.githubusercontent.com/kody-w/rapp-installer-canary/main/install.ps1 | iex

# Production (default — no env var needed)
irm https://raw.githubusercontent.com/kody-w/rapp-installer/main/install.ps1 | iex
```

Omitting `RAPP_CHANNEL` always defaults to production. Existing users never need to change anything.

## Manual Promotion (When CI Is Down)

If the `PIPELINE_TOKEN` expires or GitHub Actions is unavailable:

**Dev → Canary:**
```powershell
git clone https://github.com/kody-w/rapp-installer-dev.git temp && cd temp
git remote add canary https://github.com/kody-w/rapp-installer-canary.git
git push canary main --force && cd .. && rm -rf temp
```

**Canary → Production:**
```powershell
git clone https://github.com/kody-w/rapp-installer-canary.git temp && cd temp
git remote add prod https://github.com/kody-w/rapp-installer.git
(Get-Content rapp_brainstem/VERSION) -replace '-canary\.\d+','' | Set-Content rapp_brainstem/VERSION
git add rapp_brainstem/VERSION && git commit -m "release: v$(Get-Content rapp_brainstem/VERSION)"
git push prod main --force && cd .. && rm -rf temp
```

**Refresh expired token:**
```powershell
gh auth refresh
gh auth token | gh secret set PIPELINE_TOKEN --repo kody-w/rapp-installer-dev
gh auth token | gh secret set PIPELINE_TOKEN --repo kody-w/rapp-installer-canary
```

## Test Gates

Changes must pass these before reaching users:

| Gate | When | What |
|------|------|------|
| Gate 1 | Every PR to dev | Shell/PS syntax, test_installer.sh, unit tests, shellcheck |
| Gate 2 | Nightly before canary | Fresh install on Windows/macOS/Linux VMs, health check, dep verify |
| Gate 3 | Before production | 24h canary soak, manual smoke test |

## Amendments

This constitution can be amended by pushing changes through the pipeline — like everything else.
