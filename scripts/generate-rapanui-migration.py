#!/usr/bin/env python3
"""
Genera scripts de mutación para migración de reasignación de vacaciones México.
Crea archivos .rb y .yml, branch, commit y push automáticamente.

Uso:
  python3 scripts/generate-reasignacion-mx.py <nombre> <tenant1> <tenant2> ...

Ejemplo:
  python3 scripts/generate-reasignacion-mx.py migrar-reasignacion-mexico-prod-1 tenant1 tenant2 tenant3
"""

import sys
import os
import subprocess
from datetime import date


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


def run(cmd: list[str], cwd: str | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error ejecutando: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    if result.stdout.strip():
        print(result.stdout.strip())


def main() -> None:
    if len(sys.argv) < 3:
        print("Uso: python3 scripts/generate-reasignacion-mx.py <nombre> <tenant1> <tenant2> ...", file=sys.stderr)
        sys.exit(1)

    name = sys.argv[1]
    tenants = sys.argv[2:]

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    today = date.today()
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

    run(["git", "checkout", "main"], cwd=repo_root)
    run(["git", "pull", "origin", "main"], cwd=repo_root)
    run(["git", "checkout", "-b", branch_name], cwd=repo_root)

    with open(rb_path, "w") as f:
        f.write(generate_rb(description, tenants))

    with open(yml_path, "w") as f:
        f.write(generate_yml())

    rel_rb = os.path.relpath(rb_path, repo_root)
    rel_yml = os.path.relpath(yml_path, repo_root)

    print(f"Creado: {rel_rb}")
    print(f"Creado: {rel_yml}")
    print(f"Tenants: {len(tenants)}")

    run(["git", "add", rel_rb, rel_yml], cwd=repo_root)
    run(["git", "commit", "-m", commit_msg], cwd=repo_root)
    run(["git", "push", "-u", "origin", branch_name], cwd=repo_root)

    print(f"\nBranch '{branch_name}' creada y pusheada exitosamente.")


if __name__ == "__main__":
    main()
