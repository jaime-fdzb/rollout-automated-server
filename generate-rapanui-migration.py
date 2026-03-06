#!/usr/bin/env python3
"""
Genera scripts de mutación para migración de reasignación de vacaciones México.
Crea archivos .rb y .yml, branch, commit, push y PR automáticamente.

Uso con archivos (recomendado):
  python3 generate-rapanui-migration.py -t <tenants.txt> -d <pr_description.md>

Uso clásico (posicional):
  python3 generate-rapanui-migration.py <nombre> <tenant1> <tenant2> ...

Opciones útiles:
  -r / --repo   Ruta al repositorio destino donde se crean los archivos de mutación.
                Por defecto: ~/rapanui-v2

Ejemplos:
  python3 generate-rapanui-migration.py \\
      -t ai/data/next_batch_tenants.txt \\
      -d ai/data/next_batch_pr_description.md

  python3 generate-rapanui-migration.py \\
      -t ai/data/next_batch_tenants.txt \\
      -d ai/data/next_batch_pr_description.md \\
      -r ~/projects/rapanui-v2

  python3 generate-rapanui-migration.py \\
      migrar-reasignacion-mexico-prod-1 tenant1 tenant2 tenant3
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import date as date_type



# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def snake_to_description(name: str) -> str:
    return name.replace("-", " ").capitalize()


def generate_rb(description: str, tenants: list[str]) -> str:
    tenant_block = "\n".join(f"  {t}" for t in tenants)
    return f"""\
#
# {description}
#

TENANTS = %w[
{tenant_block}
].freeze

Admin::ConsoleAction.call(
  client_email: 'jmfernandez@buk.cl',
  what: '{description}'
) do
  TENANTS.each do |tenant|
    Apartment::Tenant.switch!(tenant)
    Vacacion::Mexico::MigrationKillVacationConfigJob.perform_now
  end
end
"""


def generate_yml() -> str:
    return """\
---
tenant: public
country: Mexico
"""


# ---------------------------------------------------------------------------
# PR description parser
# ---------------------------------------------------------------------------

def parse_pr_description(path: str) -> dict:
    """Extract metadata from the first section of a PR description markdown file."""
    with open(path) as f:
        content = f.read()

    meta: dict = {}

    # ## Mexico Vacation Migration — Batch 2026-03-06
    title_match = re.search(r"^##\s+(.+)$", content, re.MULTILINE)
    if title_match:
        meta["title"] = title_match.group(1).strip()

    # Batch date: YYYY-MM-DD anywhere in the title line
    date_match = re.search(r"Batch\s+(\d{4}-\d{2}-\d{2})", content)
    if date_match:
        meta["batch_date"] = date_match.group(1)

    # **Group:** Group 1 — Demos and test (Fase 0 — Interno)
    group_match = re.search(r"\*\*Group:\*\*\s+Group\s+(\d+)", content)
    if group_match:
        meta["group_number"] = group_match.group(1)

    # **Overall group progress:** 0 / 92 complete (0% — no migrations run yet)
    progress_match = re.search(r"\*\*Overall group progress:\*\*\s+(.+)", content)
    if progress_match:
        meta["group_progress"] = progress_match.group(1).strip()

    # **Tenants in this batch:** 50
    batch_size_match = re.search(r"\*\*Tenants in this batch:\*\*\s+(\d+)", content)
    if batch_size_match:
        meta["tenants_in_batch"] = int(batch_size_match.group(1))

    return meta


def build_name_from_meta(meta: dict) -> str:
    """Build a kebab-case migration name from PR description metadata."""
    batch_date = meta.get("batch_date", date_type.today().isoformat())
    group = meta.get("group_number", "1")
    return f"migrar-vacaciones-mx-grupo-{group}-{batch_date}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_tenants_file(path: str) -> list[str]:
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def run(cmd: list[str], cwd: str | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error ejecutando: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    if result.stdout.strip():
        print(result.stdout.strip())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera archivos de mutación Ruby para migración de vacaciones México.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-r", "--repo",
        metavar="DIR",
        default=os.path.expanduser("~/rapanui-v2"),
        help="Ruta al repositorio destino (default: ~/rapanui-v2).",
    )
    parser.add_argument(
        "-t", "--tenants-file",
        metavar="FILE",
        help="Archivo con un tenant por línea.",
    )
    parser.add_argument(
        "-d", "--pr-description",
        metavar="FILE",
        help="Archivo markdown con descripción del PR (extrae nombre, fecha, grupo y tenants del batch).",
    )
    # Legacy positional interface kept for backward compatibility
    parser.add_argument(
        "name",
        nargs="?",
        help="Nombre kebab-case de la migración (se auto-genera si se usa --pr-description).",
    )
    parser.add_argument(
        "tenants",
        nargs="*",
        help="Tenants (se ignora si se usa --tenants-file).",
    )

    args = parser.parse_args()

    # ---- Resolve tenants -----------------------------------------------
    if args.tenants_file:
        tenants = read_tenants_file(args.tenants_file)
    elif args.tenants:
        tenants = list(args.tenants)
    else:
        parser.error(
            "Debes proporcionar tenants con --tenants-file o como argumentos posicionales."
        )

    if not tenants:
        parser.error("La lista de tenants está vacía.")

    # ---- Resolve name & PR metadata ------------------------------------
    pr_body: str | None = None
    pr_title: str | None = None

    if args.pr_description:
        meta = parse_pr_description(args.pr_description)
        name = args.name or build_name_from_meta(meta)
        pr_title = meta.get("title")
        with open(args.pr_description) as f:
            pr_body = f.read()

        print(f"Metadata del PR:")
        print(f"  Título:          {meta.get('title', '—')}")
        print(f"  Fecha del batch: {meta.get('batch_date', '—')}")
        print(f"  Grupo:           {meta.get('group_number', '—')}")
        print(f"  Progreso grupo:  {meta.get('group_progress', '—')}")
        print(f"  Tenants batch:   {meta.get('tenants_in_batch', '—')}")
        print()
    elif args.name:
        name = args.name
    else:
        parser.error(
            "Debes proporcionar el nombre con --pr-description (auto-generado) "
            "o como primer argumento posicional."
        )

    # ---- Paths ---------------------------------------------------------
    repo_root = os.path.realpath(os.path.expanduser(args.repo))
    if not os.path.isdir(repo_root):
        parser.error(f"El repositorio no existe: {repo_root}")

    today = date_type.today()
    month_dir = os.path.join(repo_root, "mutations", str(today.year), f"{today.month:02d}")
    os.makedirs(month_dir, exist_ok=True)

    rb_path = os.path.join(month_dir, f"{name}.rb")
    yml_path = os.path.join(month_dir, f"{name}.yml")

    description = snake_to_description(name)
    branch_name = f"mutation/{name}"
    commit_msg = f"mutation: {name.replace('-', ' ')}"

    if os.path.exists(rb_path) or os.path.exists(yml_path):
        print(f"Error: ya existen archivos para '{name}' en {month_dir}", file=sys.stderr)
        sys.exit(1)

    # ---- Git: branch ---------------------------------------------------
    run(["git", "checkout", "main"], cwd=repo_root)
    run(["git", "pull", "origin", "main"], cwd=repo_root)
    run(["git", "checkout", "-b", branch_name], cwd=repo_root)

    # ---- Write files ---------------------------------------------------
    with open(rb_path, "w") as f:
        f.write(generate_rb(description, tenants))

    with open(yml_path, "w") as f:
        f.write(generate_yml())

    rel_rb = os.path.relpath(rb_path, repo_root)
    rel_yml = os.path.relpath(yml_path, repo_root)

    print(f"Creado: {rel_rb}")
    print(f"Creado: {rel_yml}")
    print(f"Tenants: {len(tenants)}")

    # ---- Git: commit & push --------------------------------------------
    run(["git", "add", rel_rb, rel_yml], cwd=repo_root)
    run(["git", "commit", "-m", commit_msg], cwd=repo_root)
    run(["git", "push", "-u", "origin", branch_name], cwd=repo_root)

    print(f"\nBranch '{branch_name}' creada y pusheada exitosamente.")

    # ---- GitHub PR -----------------------------------------------------
    if pr_body is not None:
        gh_cmd = [
            "gh", "pr", "create",
            "--title", pr_title or description,
            "--body", pr_body,
            "--head", branch_name,
        ]
        run(gh_cmd, cwd=repo_root)
        print("PR creado exitosamente.")

    # ---- Batch: mark tenants as 'migrando' --------------------------------
    rollout_dir = os.path.dirname(os.path.abspath(__file__))
    run(["./rollout.sh", "batch"], cwd=rollout_dir)
    print("Tenants marked as 'migrando' in the sheet.")

if __name__ == "__main__":
    main()
