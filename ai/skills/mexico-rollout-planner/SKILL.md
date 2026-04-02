---
name: mexico-rollout-planner
description: Plans the next batch of Mexico tenant migrations by reading the rollout strategy and current execution status. Use when asked about which tenants to migrate next, rollout planning, selecting the next migration group, or checking migration progress for Mexico.
---

# Mexico Rollout Planner

## Data sources

1. **Strategy** — `ai/data/rollout_strategy.md`
   - Groups and their tenant lists
   - Advancement criteria and batch size
   - Exclusions and current active group

2. **Tenant data + execution status** — `ai/data/sheet_data/migration_planer.md`
   - One row per tenant with complexity metrics, `Es demo?` flag, and `Status Mail Migración`
   - Always refreshed at the start of the workflow (see Step 0 below)

---

## Group classification

Tenants are not listed explicitly in the strategy file. Derive group membership from `migration_planer.md` using these rules, applied in order (first match wins):

| Group | Rule |
|-------|------|
| **Group 1 — Demos and test** | `Es demo? = True` |
| **Group 2 — Small tenants** | `Es demo? = False` AND `Total Asignaciones = 0` |
| **Group 3 — Main wave** | `Es demo? = False` AND `Total Asignaciones Anterior al Ingreso = 0` AND (`Total Asignaciones Posterior al Ingreso = 0` OR most assignments are equal-to-entry) |
| **Group 4 — Large / complex** | `Es demo? = False` AND `Total Asignaciones Anterior al Ingreso > 0` (majority of assignments predate company entry) |

> "Most assignments are equal-to-entry" means `Total Asignaciones en el Ingreso` is the largest of the three assignment-type columns.

---

## Analysis workflow

### Step 0 — Refresh the data

Before any analysis, always fetch the latest sheet data:

```bash
./rollout.sh sheet-data
```

This updates `ai/data/sheet_data/migration_planer.md` with current tenant statuses from Google Sheets. Do not skip this step — stale data will produce incorrect batch recommendations.

### Step 1 — Build the status map

From `migration_planer.md`, build a per-tenant summary using the `Status Mail Migración` column. Keep only the **most recent** row per tenant if duplicates exist.

### Step 2 — Classify all tenants into groups

Apply the **Group classification** rules above to every row in `migration_planer.md`. This produces the tenant list for each group.

### Step 3 — Identify the active group

From `rollout_strategy.md`, find the **Active group** in the Current State section.

### Step 4 — Evaluate the active group

For each tenant in the active group:

| State | Meaning |
|-------|---------|
| `success` | Done ✅ |
| `forced` | Done but flag for manual review ⚠️ |
| `not_found` | Done but tenant is inactive |
| `skipped` | Done but tenant has to be skipped |
| `failed` | Needs retry or investigation ❌ |
| `unknown` / `desconocido` | Unknown — treat as not run |
| not in status file / `null` | Not yet migrated |

Compute:

- **total** = number of tenants in the group
- **done** = tenants with `success`, `forced`, `not_found` or `skipped`
- **failed** = tenants with `failed`
- **pending** = tenants not yet run or `unknown`
- **success_rate** = done / (done + failed), ignoring pending

### Step 5 — Decide whether to advance

Apply the criteria from `rollout_strategy.md`:

- If `success_rate < threshold` → **do not advance**. Report failures and stop.
- If `failed > 0` → flag them but still check if threshold is met.
- If all tenants in the group are done and criteria met → **advance to next group** and use that group's pending tenants.

### Step 6 — Select the next batch

From the active (or newly advanced) group, pick up to **batch_size** tenants that are still pending — excluding any tenant already done (`success`, `forced`, `not_found`, `skipped`) and any tenant in the Exclusions list.

---

## Output format

Always respond with this structure:

```text
## Rollout recommendation — <date>

**Active group:** Group N — <name>
**Progress:** X / Y tenants complete (Z% success rate)

### ⚠️ Issues  (omit section if none)
- tenant_foo: failed — needs investigation

### ✅ Next batch (<N> tenants)
tenant_a
tenant_b
tenant_c
...

### Reasoning
<One short paragraph explaining why these tenants were selected and whether the group is on track.>
```

---

## Output files

After producing the recommendation, write two files:

### 1. Tenant list — `ai/data/next_batch_tenants.txt`

One tenant slug per line, no extra formatting. This file is consumed directly by migration scripts.

```text
tenant_a
tenant_b
tenant_c
```

### 2. PR description — `ai/data/next_batch_pr_description.md`

Markdown suitable for use as a pull request description. Include:

```markdown
## Mexico Vacation Migration — Batch <date>

**Group:** Group N — <name>
**Tenants in this batch:** <N>
**Overall group progress:** X / Y complete (<Z>% success rate)

### Tenants
- `tenant_a`
- `tenant_b`
- `tenant_c`

### Why these tenants
<Same reasoning paragraph from the recommendation. Explain group classification criteria, current progress, and why it is safe to proceed.>

### Issues to watch
<List any failed or forced tenants flagged in the recommendation, or omit this section if none.>
```

---

## Generate the PR

After writing the two output files, run the migration script to create the branch, commit, and PR automatically:

```bash
python3 generate-rapanui-migration.py \
    -t ai/data/next_batch_tenants.txt \
    -d ai/data/next_batch_pr_description.md
```

The script will:

1. Parse the PR description to extract the migration name, batch date, and group number
2. Create a branch `mutation/migrar-vacaciones-mx-grupo-<N>-<date>` in `~/rapanui-v2`
3. Write the `.rb` and `.yml` mutation files
4. Commit, push, and open the GitHub PR using the PR description file as the body

If the `~/rapanui-v2` repository is in a different location, pass `-r <path>` to the script.

---

## After output

Suggest updating the **Current State** section in `rollout_strategy.md` with the active group and any observations. Do not update it automatically — ask the user to confirm first.
