---
name: rapp-release-pipeline
version: 1.0.0
description: Manage the RAPP Brainstem release pipeline — promote changes safely from dev to canary to production without breaking user installs.
homepage: https://github.com/kody-w/rapp-installer
metadata: {"emoji":"","category":"devops","repo":"https://github.com/kody-w/rapp-installer"}
---

# RAPP Release Pipeline

Safe promotion of changes across three repos so production always works.

## Core Rule

**Never push directly to production.** Every change flows through the pipeline:

```
rapp-installer-dev  →  rapp-installer-canary  →  rapp-installer
     (develop)           (24h soak)               (stable/public)
```

A user running the one-liner install on a factory machine must succeed 100% of the time. Every decision flows from this.

## Instructions for AI Agents

Execute these steps based on what the user asks. Only pause and ask the user when marked with ⏸️.

Do not skip steps. Do not push to production directly. If the user asks you to push to production, remind them of the pipeline and offer to promote through the correct path instead.

---

## Task 1: Push a Change to Dev

*All work starts here. Feature branches, bug fixes, docs — everything.*

### Step 1: Verify you are on the dev repo

```bash
git remote -v
```

Confirm `origin` points to `rapp-installer-dev`. If it points to `rapp-installer` (production), stop. Clone the dev repo instead:

```bash
git clone https://github.com/kody-w/rapp-installer-dev.git
cd rapp-installer-dev
```

### Step 2: Create a feature branch

```bash
git checkout -b fix/description-of-change
```

Never commit directly to `main` on any repo.

### Step 3: Make changes, commit, and push

```bash
git add <files>
git commit -m "type: description of change"
git push origin fix/description-of-change
```

### Step 4: Open a PR

```bash
gh pr create --repo kody-w/rapp-installer-dev --title "description" --body "## Summary\n- what changed\n\n## Test plan\n- how to verify"
```

⏸️ Tell the user the PR is open. Gate 1 CI (syntax checks, unit tests) runs automatically. Wait for the user to decide when to merge.

### Step 5: Merge when CI passes

```bash
gh pr merge --repo kody-w/rapp-installer-dev --squash
```

The change is now on dev/main. It will auto-promote to canary at the next nightly run (6 AM UTC) if all gates pass.

---

## Task 2: Test a Dev Branch Without Touching Production

*Use this when the user wants to verify a fix before it reaches anyone else.*

### Step 1: Get the branch name

If on a feature branch:
```bash
git branch --show-current
```

### Step 2: Give the user the test one-liner

**Windows (PowerShell):**
```powershell
$env:RAPP_CHANNEL="rapp-installer-dev"; irm https://raw.githubusercontent.com/kody-w/rapp-installer-dev/<branch>/install.ps1 | iex
```

**macOS/Linux:**
```bash
RAPP_CHANNEL=rapp-installer-dev curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-installer-dev/<branch>/install.sh | bash
```

Replace `<branch>` with the actual branch name (e.g., `fix/installer-bugs` or `main`).

⏸️ Ask the user to run it and report results. Do not proceed until they confirm it works.

---

## Task 3: Promote Dev to Canary (Manual)

*Use this if the nightly CI promotion hasn't run yet or the PIPELINE_TOKEN is expired.*

### Step 1: Verify dev/main is ready

```bash
gh run list --repo kody-w/rapp-installer-dev --branch main --limit 5
```

Check that the latest Gate 1 workflow passed. If it failed, do not promote — fix the issue first.

### Step 2: Push dev/main to canary

```powershell
cd ~
git clone https://github.com/kody-w/rapp-installer-dev.git temp-promote
cd temp-promote
git remote add canary https://github.com/kody-w/rapp-installer-canary.git
git push canary main --force
cd ..
rm -rf temp-promote
```

⏸️ Tell the user canary is updated. Remind them it needs to soak for 24 hours before production promotion.

---

## Task 4: Promote Canary to Production (Manual)

*This is the final gate. Only do this when the user explicitly asks and canary has soaked.*

### Step 1: Check soak time

```bash
gh api repos/kody-w/rapp-installer-canary/commits/main --jq '.commit.committer.date'
```

If the last canary commit is less than 24 hours old, warn the user:

⏸️ "Canary has only been soaking for X hours. The minimum is 24h. Do you want to proceed anyway?"

### Step 2: Verify canary works

Give the user the canary one-liner to test:

```powershell
$env:RAPP_CHANNEL="rapp-installer-canary"; irm https://raw.githubusercontent.com/kody-w/rapp-installer-canary/main/install.ps1 | iex
```

⏸️ Ask the user to confirm canary is working before promoting to production.

### Step 3: Promote to production

```powershell
cd ~
git clone https://github.com/kody-w/rapp-installer-canary.git temp-promote
cd temp-promote
git remote add production https://github.com/kody-w/rapp-installer.git
(Get-Content rapp_brainstem/VERSION) -replace '-canary\.\d+','' | Set-Content rapp_brainstem/VERSION
git add rapp_brainstem/VERSION
git commit -m "release: v$(Get-Content rapp_brainstem/VERSION)"
git tag "v$(Get-Content rapp_brainstem/VERSION)"
git push production main --force
git push production "v$(Get-Content rapp_brainstem/VERSION)"
cd ..
rm -rf temp-promote
```

⏸️ Tell the user: "Production updated to vX.X.X. All users running the one-liner will now get this version."

---

## Task 5: Rollback Production

*If production is broken, rollback first. Fix forward through the pipeline after.*

### Step 1: Identify the issue

```bash
gh api repos/kody-w/rapp-installer/commits --jq '.[0:3][] | "\(.sha[0:7]) \(.commit.message)"'
```

### Step 2: Revert

**Option A — Revert last commit:**
```bash
cd ~
git clone https://github.com/kody-w/rapp-installer.git temp-rollback
cd temp-rollback
git revert HEAD --no-edit
git push origin main
cd ..
rm -rf temp-rollback
```

**Option B — Pin to a known-good tag:**
```bash
cd ~
git clone https://github.com/kody-w/rapp-installer.git temp-rollback
cd temp-rollback
git reset --hard v0.5.4
git push --force-with-lease origin main
cd ..
rm -rf temp-rollback
```

⏸️ Tell the user production is restored. Then: "The fix should go through dev → canary → production. Want me to start a fix branch on dev?"

---

## Task 6: Refresh Expired Pipeline Token

*If CI workflows fail with auth errors, the PIPELINE_TOKEN secret needs refreshing.*

### Step 1: Refresh GitHub auth

```powershell
gh auth refresh
```

### Step 2: Update secrets on both repos

```powershell
gh auth token | gh secret set PIPELINE_TOKEN --repo kody-w/rapp-installer-dev
gh auth token | gh secret set PIPELINE_TOKEN --repo kody-w/rapp-installer-canary
```

### Step 3: Verify

```powershell
gh secret list --repo kody-w/rapp-installer-dev
gh secret list --repo kody-w/rapp-installer-canary
```

Both should show `PIPELINE_TOKEN` with a recent timestamp.

For a long-lived token, generate a classic PAT at https://github.com/settings/tokens with `repo` + `workflow` scopes and set it as `PIPELINE_TOKEN` on both repos.

---

## Channel Reference

| Channel | Repo | Stability | One-liner |
|---------|------|-----------|-----------|
| Dev | `rapp-installer-dev` | Unstable | `$env:RAPP_CHANNEL="rapp-installer-dev"; irm .../rapp-installer-dev/main/install.ps1 \| iex` |
| Canary | `rapp-installer-canary` | Pre-release | `$env:RAPP_CHANNEL="rapp-installer-canary"; irm .../rapp-installer-canary/main/install.ps1 \| iex` |
| Production | `rapp-installer` | Stable | `irm .../rapp-installer/main/install.ps1 \| iex` |

## CI Workflows

| Workflow | Repo | Trigger | Purpose |
|----------|------|---------|---------|
| `gate1-pr.yml` | dev | PR/push to main | Syntax checks, unit tests, shellcheck |
| `gate2-integration.yml` | dev | Nightly 5 AM UTC | Fresh install on Win/Mac/Linux VMs |
| `promote-canary.yml` | dev | Nightly 6 AM UTC | Auto-promote to canary if gates pass |
| `promote-production.yml` | canary | Manual dispatch | Promote to production (requires PROMOTE confirmation) |
