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
- `done` = Observed in the wild as of 2026-04-14. Treat as equivalent to `success` (Done). Seen in tenants: gmle-semanal (1 emp), ultralaboratorios (0 emp), customereducation (0 emp).

## Group 1 Demo Tenant Identification

Use `Es demo? = True` from the dataset — yields 79 tenants as of 2026-03-11 (was 92 per a prior incorrect count; 13 tenants now have `Es demo? = TEST` and are NOT Group 1).

TEST tenants (`Es demo? = TEST`) are a distinct classification — they are NOT included in Group 1. There are 13 TEST tenants total. As of 2026-04-20:
- 4 `success`: grupowinland-test, hjb-test, hjb-test2, shasau-test
- 3 `skipped`: schwabemexico-test, payrollsdxmexico-test2, payrollsdxmexico-test
- 6 `migrating` (queued in PR #19046): pruebashagalo-test, whitestackmexico, valdezbaluarte-test, rappicardtest, buktest, difarvet-test
- 0 remaining null — ALL TEST tenants have been addressed

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
- Active group as of 2026-04-20: Group 4 (Large/Complex — Fase 3) — ALL 8 batches queued on 2026-04-20, 0 pending remain
- Group 1: 79 tenants (`Es demo? = True`) — 76 done, 3 retrying in PR #19046 (didi-demo, democlientes, demobukvideomx-demo); sac-demo, demosales, lfmata-demo succeeded from PR #18539
- Group 2: 136 tenants — 136/136 done (100% complete)
- Group 3: 724 tenants — 719 done (99.4%), 5 migrating in flight (PR #19027), advancement threshold met
- Group 4 all batches (2026-04-20): 383 migrating, 2 done, 0 pending, 0 failed
  - Batch 1 PR #19031: 50 tenants, ant=1, emp 3–46
  - Batch 2 PR #19033: 50 tenants, ant=1, emp 47–102
  - Batch 3 PR #19040: 50 tenants, ant=1, emp 19–4996 (includes dimpack retry)
  - Batch 4 PR #19041: 50 tenants, ant=2, emp 6–131
  - Batch 5 PR #19042: 50 tenants, ant=2–3, emp 13–1842
  - Batch 6 PR #19043: 50 tenants, ant=3–5, emp 21–1078
  - Batch 7 PR #19044: 50 tenants, ant=5–14, emp 20–2329
  - Batch 8 PR #19045: 33 tenants, ant=15–89, emp 24–1630 (FINAL GROUP 4 BATCH)
- Extra batch PR #19046 (2026-04-20): 9 tenants — 3 Group 1 retries (didi-demo, democlientes, demobukvideomx-demo) + 6 TEST tenants (pruebashagalo-test, whitestackmexico, valdezbaluarte-test, rappicardtest, buktest, difarvet-test)
- clientes15-demo: status `skipped` (processed before PR #18098); excluded from 2026-04-02 batch due to corrupted employee field data — do not include in future batches without resolving the data issue
- pagoni: previously excluded pending `tramo_carrera_docente` DB column migration — blocker cleared as of 2026-04-14. Included in batch 8 (PR #18695). No longer excluded.

## Multi-Batch Queuing Pattern (2026-04-20)

When all remaining pending tenants in a group can be queued in one session (no need to wait for PR results), it is valid to:
- Pre-compute all batches from the current dataset before creating any PRs
- Create all PRs sequentially without re-running sheet-data between them (data was fresh at start)
- Mark all batches as `migrating` in the sheet as PRs are created
- This approach is faster and avoids redundant sheet refreshes when the dataset is stable

## Parallel Group Batching

Users may authorize running Group 2/3 batches in parallel with Group 1 retries — this is an explicit override of the normal sequential advancement rule. When this happens:
- Use migration name `migrar-vacaciones-mx-grupo-2-3-<date>` to distinguish from pure Group 2 batches
- Document clearly in PR description that it is a parallel/authorized batch
- Both Group 1 and Group 2+3 PRs may be open simultaneously

## File Name Conflict Handling

The generate-rapanui-migration.py script fails if `migrar-vacaciones-mx-grupo-N-<date>.rb` already exists. To resolve: pass the migration name explicitly as the first positional argument. This overrides the auto-generated name from the PR description.
- Combined group batches: `migrar-vacaciones-mx-grupo-2-3-<date>`
- Multiple same-group batches on same day: `migrar-vacaciones-mx-grupo-3-batch-8-<date>` (confirmed pattern from 2026-04-14 batch 8, PR #18695)

The script auto-detects the group number from the PR description. For retry batches, the PR description title must explicitly contain the correct group number or the script will default to group 1. To avoid wrong naming: always pass the migration name explicitly as the first positional argument for non-standard batches (retries, multi-group, etc.). Example: `python3 generate-rapanui-migration.py migrar-vacaciones-mx-grupo-3-retry-failed-2026-04-20 -t ... -d ...`

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
- The 50-tenant batch limit does NOT apply to retry batches — include all stuck tenants in one PR.
- Use migration name `migrar-vacaciones-mx-grupo-N-retry-migrating-<date>` for these batches (confirmed pattern from 2026-04-13 PR #18679).
