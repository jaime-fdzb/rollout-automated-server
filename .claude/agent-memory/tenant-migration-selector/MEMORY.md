# Tenant Migration Selector — Persistent Memory

## Data Source Patterns

### migration_planer.md (ai/data/sheet_data/)

- Contains ~1,200 tenant rows (header at row 1, data from row 11 onward; range A1:Q1201 as of 2026-03-06).
- Columns (17 total): Tenant, Total Asignaciones Anterior al Ingreso, Total Asignaciones Posterior al Ingreso, Total Asignaciones en el Ingreso, Total Asignaciones, Promedio Posterior, Desv Posterior, Promedio Anterior, Desv Anterior, Promedio Nula o Igual, Desv Nula o Igual, Empleados con Asignaciones Anterior al Ingreso, Empleados con Asignaciones Posterior al Ingreso, Empleados con Asignaciones Nula o Igual al Ingreso, Total Empleados, Es demo?, Status Mail Migración.
- **CORRECTED (2026-03-06):** The "Es demo?" column IS properly populated — 92 tenants carry `True`. Rely on this column for Group 1 classification.
- "Status Mail Migración" was null for all 1,200 tenants as of 2026-03-06 — no migrations had executed yet.
- The file has only 17 columns (no "Status Datawarehouse Migración" column in the refreshed sheet).
- The path `data/sheet_data/migration_planer.md` does NOT exist. Status is embedded in `ai/data/sheet_data/migration_planer.md`.

### Execution status values (per SKILL.md)

- `success` = Done
- `forced` = Done but needs manual review
- `failed` = Needs retry
- `desconocido` = Unknown, treat as not run
- absent = not yet migrated

## Group 1 Demo Tenant Identification

Use `Es demo? = True` directly from the dataset — the column is reliably populated (92 tenants as of 2026-03-06). No name-convention fallback needed.

Notable large demo/test tenants to treat with care (high employee count despite being demos):

- `shasau-test`: 1,891 employees
- `payrollsdxmexico-test2`: 4,768 employees
- `payrollsdxmexico-test`: 4,797 employees

These have 0 Anterior al Ingreso assignments, so they sort early by the priority rules. Flag them for sequential/last execution within the batch to limit blast radius.

## Key File Paths

- Strategy: `ai/data/rollout_strategy.md`
- Tenant data + status: `ai/data/sheet_data/migration_planer.md`
- Skill definition: `ai/skills/mexico-rollout-planner/SKILL.md`
- Refresh command: `./rollout.sh sheet-data`

## Rollout Strategy Summary

- Batch size: 50 tenants per execution
- Advancement threshold: >= 95% success rate, 0 failed tenants, forced tenants reviewed
- Active group as of 2026-03-06: Group 1 (Demos and test — Fase 0)
- Total dataset: ~1,200 tenants across Groups 1-4; Group 1 has 92 demo tenants

## Prioritization Logic (from rollout_strategy.md)

Easier tenants first, harder tenants later:

1. Tenants with fewer "Anterior al Ingreso" assignments (complexity indicator)
2. Tenants with fewer total employees (lower blast radius)
3. Tenants with fewer total vacation config definitions

For Group 1 specifically: use `Es demo? = True` from the dataset — the column is populated.
