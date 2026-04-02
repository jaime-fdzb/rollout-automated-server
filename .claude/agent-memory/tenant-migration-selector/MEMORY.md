# Tenant Migration Selector — Persistent Memory

## Data Source Patterns

### migration_planer.md (ai/data/sheet_data/)

- Contains ~1,200 tenant rows (header at row 1, data from row 11 onward; range A1:Q1201).
- Columns (17 total): Tenant, Total Asignaciones Anterior al Ingreso, Total Asignaciones Posterior al Ingreso, Total Asignaciones en el Ingreso, Total Asignaciones, Promedio Posterior, Desv Posterior, Promedio Anterior, Desv Anterior, Promedio Nula o Igual, Desv Nula o Igual, Empleados con Asignaciones Anterior al Ingreso, Empleados con Asignaciones Posterior al Ingreso, Empleados con Asignaciones Nula o Igual al Ingreso, Total Empleados, Es demo?, Status Mail Migración.
- The "Es demo?" column has these values: `True` (79 tenants as of 2026-03-11), `False` (~1,108), `TEST` (13 tenants), and blank/`---` (header rows).
- The path `data/sheet_data/migration_planer.md` does NOT exist. Status is embedded in `ai/data/sheet_data/migration_planer.md`.

### Execution status values

Defined in SKILL.md: `success` = Done, `forced` = Done but needs manual review, `failed` = Needs retry, `desconocido` = Unknown (treat as not run), absent/`null` = not yet migrated.

Additional statuses observed in the wild (not in SKILL.md):
- `skipped` = Migration intentionally skipped — all affected tenants have 0 employees/assignments. Treat as done (equivalent to success for advancement calculation).
- `not_found` = Tenant not found on the platform. Treat as **Done** (inactive tenant) — do NOT include in next batch. Counts toward `done` in the success rate calculation. May mean tenant was renamed or decommissioned; worth flagging for investigation but not a blocker.
- `migrating` = PR has been created and tenants are queued, but job has not completed yet. Set automatically by `generate-rapanui-migration.py` via `./rollout.sh batch` after PR creation. Treat as **in-flight** — do NOT include in the next batch and do NOT count as done or failed. If all remaining tenants in a group are `migrating`, there is nothing left to batch: wait for PR results and sheet refresh.

## Group 1 Demo Tenant Identification

Use `Es demo? = True` from the dataset — yields 79 tenants as of 2026-03-11 (was 92 per a prior incorrect count; 13 tenants now have `Es demo? = TEST` and are NOT Group 1).

TEST tenants (`Es demo? = TEST`) are a distinct classification — they are NOT included in Group 1. As of 2026-03-11 there are 13 TEST tenants, all with `null` status.

Notable large tenants with `Es demo? = TEST` (high employee count, need careful handling if included in future batches):
- `shasau-test`: 1,891 employees
- `payrollsdxmexico-test2`: 4,768 employees
- `payrollsdxmexico-test`: 4,797 employees

## Key File Paths

- Strategy: `ai/data/rollout_strategy.md`
- Tenant data + status: `ai/data/sheet_data/migration_planer.md`
- Skill definition: `ai/skills/mexico-rollout-planner/SKILL.md`
- Refresh command: `./rollout.sh sheet-data`
- Tenant list output: `ai/data/next_batch_tenants.txt`
- PR description output: `ai/data/next_batch_pr_description.md`
- Migration script: `generate-rapanui-migration.py`

## Rollout Strategy Summary

- Batch size: 50 tenants per execution
- Advancement threshold: >= 95% success rate, 0 failed tenants, forced tenants reviewed
- Active group as of 2026-03-27: Group 1 (Demos and test — Fase 0)
- Group 1: 79 tenants (`Es demo? = True`)
- Group 1 progress as of 2026-04-02 (sheet refresh): 45 done, 34 migrating, 0 failed, 0 pending — all Group 1 tenants are done or in-flight; waiting for PR #18241 to complete before advancing to Group 2
- Last batch: 2026-04-02 — PR bukhr/rapanui-v2#18241 (34 tenants: third attempt re-run after PR #18007 and #18098 both failed to execute the migration job)
- clientes15-demo: status `skipped` (processed before PR #18098); excluded from 2026-04-02 batch due to corrupted employee field data — do not include in future batches without resolving the data issue

## Prioritization Logic (from rollout_strategy.md)

Easier tenants first, harder tenants later:

1. Tenants with fewer "Anterior al Ingreso" assignments (complexity indicator)
2. Tenants with fewer total employees (lower blast radius)
3. Tenants with fewer total vacation config definitions

## Batch Composition Pattern

When the group has not yet reached the advancement threshold:
- Include all pending (null) tenants first, sorted by priority.
- Include all failed tenants next (for retry), sorted by priority. NOT not_found — those are done.
- If combined count <= batch_size (50), include all in one batch.
- Do not skip failed tenants — they must be retried before the group can advance.

### Re-run batches (failed PR execution)

When a PR failed to execute its migration job, the affected tenants remain in `migrating` status after a sheet refresh. In this case:
- Select all tenants with `migrating` status in the active group.
- Apply any manual exclusions the user specifies (e.g., a tenant with corrupted data).
- Verify each excluded tenant's actual current status in the sheet before treating the exclusion as "already done" — a tenant might show `skipped`/`success` if it was processed by a prior batch, even if the user thinks it was in the failed PR.
- Document exclusions prominently in the PR description with the reason.
