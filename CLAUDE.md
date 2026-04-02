# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAPP Brainstem is a local-first AI agent server powered by GitHub Copilot — no API keys needed. It's a progressive platform teaching the Microsoft AI stack through a biological metaphor:

| Tier | Metaphor | What it is |
|------|----------|-----------|
| Brainstem | Survival basics | Local Flask server with tool-calling agent loop (`rapp_brainstem/`) |
| Spinal Cord | Cloud body | Azure deployment via ARM template (`azuredeploy.json`, `deploy.sh`) |
| Nervous System | Enterprise reach | Copilot Studio + Teams/M365 (`MSFTAIBASMultiAgentCopilot_*.zip`) |

Philosophy: "engine, not experience" — infrastructure only, no opinionated UI or workflows (see `rapp_brainstem/CONSTITUTION.md`).

## Commands

```bash
# Start server (creates venv, installs deps, runs on port 7071)
cd rapp_brainstem && ./start.sh          # macOS/Linux
cd rapp_brainstem && powershell .\start.ps1  # Windows
python rapp_brainstem/brainstem.py       # Direct (assumes deps installed)

# Install dependencies
pip install -r rapp_brainstem/requirements.txt

# Run all unit tests
cd rapp_brainstem && python3 -m pytest test_local_agents.py -v

# Run a single test
python3 -m pytest test_local_agents.py::TestLocalStorage::test_write_and_read -v

# Run installer validation suite
bash tests/test_installer.sh

# Health check
curl -s localhost:7071/health | python3 -m json.tool
```

No linter, type checker, or build step is configured.

## Architecture

**Entry point:** `rapp_brainstem/brainstem.py` — a single-file Flask server (~1500 lines) containing auth, routing, agent orchestration, Copilot API integration, and the web UI. All server logic lives here by design.

**Request flow (POST /chat):**
1. Load `soul.md` (system prompt) and fresh-discover agents from `agents/`
2. Build OpenAI-format tool definitions from agent metadata
3. Call GitHub Copilot API with system prompt + conversation history + tools
4. If the LLM returns tool calls, execute agent `.perform()` methods and loop (up to 3 rounds)
5. Return final response + `agent_logs`

**Agent system:** Auto-discovered via glob `agents/*_agent.py` (flat only — `agents/experimental/` excluded). Agents are reloaded from disk on every request (edit and test without restart). Missing pip dependencies are auto-installed at import time via `_PIP_MAP`.

**Import shims:** `_register_shims()` injects fake `sys.modules` so agents written for Azure cloud work locally — `utils.azure_file_storage` → `local_storage.py` (JSON files under `.brainstem_data/`).

**Auth chain** (priority order): `GITHUB_TOKEN` env var → `.copilot_token` file → `gh auth token` CLI (skips `gho_` tokens) → device code OAuth via `/login`. Copilot API tokens are exchanged from the GitHub token with 60s expiry buffer and disk caching.

**Model quirks:** `o1` models don't support `tool_choice`. Claude models return multi-choice responses (text + tool_calls in separate choices); `call_copilot()` merges these automatically.

## Release Pipeline

**Never push directly to `rapp-installer` (production).** See `CONSTITUTION.md` for the full rules.

```
rapp-installer-dev  →  rapp-installer-canary  →  rapp-installer
     (develop)           (24h soak)               (stable/public)
```

| Channel | Repo | One-liner |
|---------|------|-----------|
| Dev | `rapp-installer-dev` | `$env:RAPP_CHANNEL="rapp-installer-dev"; irm .../rapp-installer-dev/main/install.ps1 \| iex` |
| Canary | `rapp-installer-canary` | `$env:RAPP_CHANNEL="rapp-installer-canary"; irm .../rapp-installer-canary/main/install.ps1 \| iex` |
| Production | `rapp-installer` | `irm .../rapp-installer/main/install.ps1 \| iex` (default, no env var) |

**CI gates:** Gate 1 (syntax, unit tests) on every PR → Gate 2 (fresh install on Win/Mac/Linux VMs) nightly → auto-promote to canary → 24h soak → manual promote to production.

**Manual promotion with git CLI** (when `PIPELINE_TOKEN` expires):
```bash
# Dev → Canary
git clone https://github.com/kody-w/rapp-installer-dev.git temp && cd temp
git remote add canary https://github.com/kody-w/rapp-installer-canary.git
git push canary main --force && cd .. && rm -rf temp

# Canary → Production
git clone https://github.com/kody-w/rapp-installer-canary.git temp && cd temp
git remote add prod https://github.com/kody-w/rapp-installer.git
(Get-Content rapp_brainstem/VERSION) -replace '-canary\.\d+','' | Set-Content rapp_brainstem/VERSION
git add rapp_brainstem/VERSION && git commit -m "release: v$(Get-Content rapp_brainstem/VERSION)"
git push prod main --force && cd .. && rm -rf temp
```

**Refresh expired token:**
```bash
gh auth refresh
gh auth token | gh secret set PIPELINE_TOKEN --repo kody-w/rapp-installer-dev
gh auth token | gh secret set PIPELINE_TOKEN --repo kody-w/rapp-installer-canary
```

**Rollback:** Revert HEAD or `git reset --hard v<tag>` on production. Rollback first, fix forward through the pipeline after.

## Repo Layout

| Path | Purpose |
|------|---------|
| `rapp_brainstem/` | Tier 1: Flask server, agents, tests, soul, web UI |
| `rapp_brainstem/agents/` | Auto-discovered agent Python files (`*_agent.py`) |
| `install.ps1`, `install.sh`, `install.cmd` | One-liner installers (Windows, Unix, CMD wrapper) |
| `deploy.ps1`, `deploy.sh`, `azuredeploy.json` | Tier 2: Azure ARM deployment |
| `community_rapp/` | Public skill gateways for CommunityRAPP (Tier 2 backend) |
| `docs/` | GitHub Pages site, release pipeline strategy |
| `tests/test_installer.sh` | Installer validation (branding, paths, structure) |
| `skill.md` | Moltbook-format onboarding skill with ⏸️ pause points |
| `CONSTITUTION.md` | Pipeline governance — the law of how code reaches users |

## Key Conventions

- **Python 3.11** target; venv at `~/.brainstem/venv`
- **Single-file server** — all logic in `brainstem.py`, keep it that way
- **Config via `.env`** — `GITHUB_TOKEN`, `GITHUB_MODEL` (default `gpt-4o`), `SOUL_PATH`, `AGENTS_PATH`, `PORT`, `VOICE_MODE`
- **`RAPP_CHANNEL` env var** controls which repo the installer clones from (defaults to production)
- **VERSION file** at `rapp_brainstem/VERSION` — clean semver in production, suffixed in dev/canary
- **Agents are hot-reloaded** on every request; no restart needed when editing
- **Storage shims** let agents use `from utils.azure_file_storage import AzureFileStorageManager` locally — it resolves to `local_storage.py` writing JSON to `.brainstem_data/`
