# AI Agent Guide

This document is the entry point for any AI agent (Cursor, Claude Code, OpenCode, etc.) working in this repository.

## Repository purpose

Monitors Gmail for tenant migration completion emails, records results, syncs to Google Sheets, and provides tooling to plan the next rollout batch.

---

## Skills

Skills are step-by-step instructions for domain-specific tasks. Read the relevant skill file before acting on the corresponding task.

| Skill | File | When to use |
|-------|------|-------------|
| Mexico Rollout Planner | `ai/skills/mexico-rollout-planner/SKILL.md` | Selecting next tenants to migrate, evaluating rollout progress, planning migration batches |

---

## AI data

The `ai/data/` directory contains files designed to be read by AI agents:

| File | Description |
|------|-------------|
| `ai/data/rollout_strategy.md` | Rollout groups, tenant lists, advancement criteria, and current state. **Edit this manually.** |
| `ai/data/sheet_data/migration_planer.md` | Latest execution status fetched from Google Sheets. **Auto-generated — do not edit.** Refresh with `./rollout.sh sheet-data`. |

---

## CLI

```bash
# Fetch latest sheet data from Google Sheets and save to ai/data/sheet_data/
./rollout.sh sheet-data

# Override sheet or range
./rollout.sh sheet-data --sheet migration_planer --range A1:D500
```

The script starts the Docker server automatically if it is not running, and stops it again when done.

---

## Key files

| File | Description |
|------|-------------|
| `server.py` | FastAPI server — webhook receiver, dashboard, sheet-data endpoint |
| `imap_watcher.py` | IMAP IDLE watcher — parses emails and posts to `/webhook` |
| `sheet_script.gs` | Google Apps Script — `doPost` writes rows, `doGet` reads ranges |
| `generate-rapanui-migration.py` | Generates Ruby mutation files for a given list of tenants |
| `docker-compose.yaml` | Runs `app` (server) and `watcher` services |

---

## Environment variables

See `.env.example` or the **Environment variables** section in `README.md` for the full list.
