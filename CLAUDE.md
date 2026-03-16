# Rollout Automated Server

Automated Mexico vacation migration rollout system. Selects tenant batches, generates PRs in `~/rapanui-v2`, and tracks migration progress.

## What this project does

Migrates Mexico tenants through `Vacacion::Mexico::MigrationKillVacationConfigJob` in controlled waves (4 groups). Each session typically involves generating the next batch of tenants to migrate.

## Key commands

```bash
./rollout.sh sheet-data          # Refresh tenant data from Excel source (ALWAYS run before analysis)
python3 generate-rapanui-migration.py \
    -t ai/data/next_batch_tenants.txt \
    -d ai/data/next_batch_pr_description.md   # Create branch + commit + PR in rapanui-v2
```

## Key files

| File | Purpose |
|------|---------|
| `ai/data/rollout_strategy.md` | Groups, advancement criteria, batch size, **Current State** |
| `ai/data/sheet_data/migration_planer.md` | All tenants with complexity metrics and migration status |
| `ai/data/next_batch_tenants.txt` | Output: one tenant slug per line for the migration script |
| `ai/data/next_batch_pr_description.md` | Output: PR body markdown |
| `ai/skills/mexico-rollout-planner/SKILL.md` | Full skill definition for batch selection logic |
| `.claude/agent-memory/tenant-migration-selector/MEMORY.md` | Agent persistent memory (group rules, status meanings) |

## Typical workflow

1. User says "genera el próximo grupo de rollout"
2. Use the `tenant-migration-selector` agent — it handles everything end to end:
   - Runs `./rollout.sh sheet-data` to refresh data
   - Reads strategy + tenant data
   - Selects the next batch (up to 50 tenants)
   - Writes `next_batch_tenants.txt` and `next_batch_pr_description.md`
   - Runs `generate-rapanui-migration.py` to create the PR
3. After the agent finishes, update **Current State** in `rollout_strategy.md`

## Current rollout state

- **Active group:** Group 1 — Demos and test (Fase 0 — Interno)
- **Last batch run:** 2026-03-15 — PR #17535 (35 tenants: 21 retries + 14 pending)
- **Group 1 progress (pre-batch):** 44/79 done (67.7% success rate — below 95% threshold)
- **Next action:** Wait for PR #17535 to merge and job to complete, then refresh and re-run

## Status values in migration_planer.md

| Value | Meaning |
|-------|---------|
| `success` | Done |
| `forced` | Done — needs manual review |
| `skipped` | Done — tenant had 0 employees/assignments |
| `not_found` | Done — tenant is inactive |
| `failed` | Needs retry |
| `desconocido` / `unknown` | Treat as not run |
| blank / null | Not yet migrated |
