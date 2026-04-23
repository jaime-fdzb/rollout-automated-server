# Mexico Vacation Migration — Rollout Strategy

## Overview

- **Migration:** `Vacacion::Mexico::MigrationKillVacationConfigJob`
- **Country:** Mexico
- **Responsible:** jmfernandez@buk.cl
- **Goal:** Migrate all Mexico tenants in controlled waves, validating stability before advancing.

---

## Advancement Criteria

A group is considered **complete** and the next one can proceed when:

- Success rate of the current group is **≥ 95%**
- No tenant has status failed, the ones with status failed have to be migrated again before proceeding to the next group
- Tenants with `forced` status have been manually reviewed and signed off

If a group has failures above the threshold, **stop and investigate** before continuing.

---

## Batch Size

Run at most **50 tenants per execution** within a group.  
This limits blast radius and keeps execution times manageable.

---

## Priorization

Tenants with vacation config definitions that were asigned before the company entry date are more complex cases and could rise more failures.
Tenants with more employees are more risky therefore more prone to raise failures.
Tenants with more vacation config definitions are more risky.
We should build the groups on the easier to migrate tenants firsts and the hardest ones later

---

## Groups

Each group lists the tenants to migrate in order. Tenants not yet migrated in a group are candidates for the next batch.

### Group 1 — Demos and test (Fase 0 — Interno)

**Objective:** Validate the backfill and refactors in a controlled environment; detect edge cases not covered by the test suite.

**Actions:**
- Run the migration script on demo MX tenants.
- Enable `core_vacaciones_eliminar_vacation_config`, `core_vacacion_feature_mantener_proporcion_mx`, and `habilitar_fecha_reconocimiento_antiguedad` on the demo MX tenant.
- Validate short-term success criteria and run the full test suite.

**Advancement milestone:** 0 Sentry errors, backfill without inconsistencies.
**Estimated time in internal:** 1 sprint (~2 weeks) to receive feedback and fix issues.

---

### Group 2 — Small tenants (Fase 1 — Ola de activación 1: Clientes sin asignaciones de vacaciones)

**Objective:** Measure success criteria with real data; detect edge cases not covered by the test suite.

**Segment:** 136 MX clients whose employees have 0 vacation assignments.

**Notes:** Small-sized tenants, below 100 employees total. Advance only after Group 1 completes.

**Advancement criteria:** No increase in Sentry errors or vacation-related tickets for 7 days. Migration script results without inconsistencies.

**Monitoring:** Immediate review after running the script; daily Sentry monitoring for active tenants.

---

### Group 3 — Main wave (Fase 2 — Clientes Beta y Ola de activación 2: Clientes con configuraciones simples)

**Objective:** Measure success criteria with real data; detect edge cases not covered by previous waves.

**Segment:** 429 MX clients whose employees either have 0 assignments with a calculation start date before the company entry date and 0 with a date after entry, or a small number where most calculation start dates equal the entry date.

**Notes:** Medium-sized tenants, between 100 and 500 employees total. Advance only after Group 2 completes.

**Advancement criteria:** No increase in Sentry errors or vacation-related tickets for 7 days. Migration script results without inconsistencies.

**Monitoring:** Immediate review after running the script; daily Sentry monitoring for active tenants.

---

### Group 4 — Large (Fase 3 — Ola de activación 3: Clientes con configuraciones complejas)

**Objective:** Migrate the most complex group; continue measuring success criteria and detecting edge cases from previous waves.

**Segment (moderately complex):** 158 clients with 0 assignments with a calculation start date before entry, and most assignments with a calculation start date after or equal to the entry date.

**Segment (highly complex):** 222 clients where most assignments have a calculation start date before the company entry date.

**Notes:** Large tenants, above 500 employees total. Advance only after Group 3 completes.

**Advancement criteria:** Migration script results without inconsistencies and no related Sentry errors.

**Additional preparation:** Manual review of a representative sample of migration results before activating. Wait for the corresponding payroll period close to validate success criteria.

**Post-Group-4:** Once completed without incidents, activate feature flags to 100% for all MX clients and notify the MX Items, MX Certificates, and MX Finiquitos teams.

---

## Exclusions

Tenants listed with errors that must be retried when told to.

---

## Current State

- **Active group:** Group 4 — Large/Complex (Fase 3 — Clientes con configuraciones complejas)
- **Last batch run:** 2026-04-20 — Extra batch for remaining Group 1 retries + TEST tenants (PR #19046)
- **Group 1 progress as of 2026-04-20:** 76/79 done (sac-demo, demosales, lfmata-demo succeeded), 3 retrying in PR #19046 (didi-demo, democlientes, demobukvideomx-demo)
- **Group 2 progress as of 2026-04-13:** 136/136 done (100% complete)
- **Group 3 progress as of 2026-04-20:** 719/724 done (99.4%), 5 migrating in flight (PR #19027 retry), 0 failed, 0 pending — advancement threshold met
- **Group 4 progress as of 2026-04-20 (post all batches):** 383 migrating (all pending + failed queued), 2 done, 0 pending, 0 failed
- **Group 4 PRs (all in-flight):**
  - Batch 1 — PR #19031: 50 tenants, ant=1, emp 3–46
  - Batch 2 — PR #19033: 50 tenants, ant=1, emp 47–102
  - Batch 3 — PR #19040: 50 tenants, ant=1, emp 19–4996 (includes dimpack retry)
  - Batch 4 — PR #19041: 50 tenants, ant=2, emp 6–131
  - Batch 5 — PR #19042: 50 tenants, ant=2–3, emp 13–1842
  - Batch 6 — PR #19043: 50 tenants, ant=3–5, emp 21–1078
  - Batch 7 — PR #19044: 50 tenants, ant=5–14, emp 20–2329
  - Batch 8 — PR #19045: 33 tenants, ant=15–89, emp 24–1630 (FINAL GROUP 4 BATCH)
- **Extra batch — PR #19046:** 9 tenants — 3 Group 1 retries (didi-demo, democlientes, demobukvideomx-demo) + 6 TEST tenants (pruebashagalo-test, whitestackmexico, valdezbaluarte-test, rappicardtest, buktest, difarvet-test)
- **Observations:** All Group 4 tenants queued. Extra batch covers remaining Group 1 failures and all TEST (Es demo?=TEST) tenants that had never been migrated. After PR #19046 completes, the only remaining items are the 5 Group 3 tenants in PR #19027. Next action: wait for all PRs to complete, refresh sheet, verify advancement thresholds.
- **Pending activation batches (2026-04-21):** 71 additional tenants with `activado: false` not previously queued, split into 2 batches:
  - Batch 1 — PR #19193: 50 tenants (13 known-zero-complexity + 37 new tenants not in sheet)
  - Batch 2 — PR #19194: 21 tenants (15 new tenants + 6 known: demopartners, schwabemexico-test, wireco, sodexopruebasint, payrollsdxmexico-test2, payrollsdxmexico-test)
