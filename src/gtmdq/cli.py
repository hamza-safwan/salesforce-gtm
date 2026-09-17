"""Milestone commands expose completed behavior only; later stages are not stubs."""

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

import psycopg

from gtmdq.config import PROJECT_ROOT
from gtmdq.database.migrations import migrate
from gtmdq.generator.pipeline import default_paths, generate_bundle
from gtmdq.salesforce.cli import executable, inspect_org


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="gtmdq", description=__doc__)
    actions = command.add_subparsers(dest="command", required=True)
    actions.add_parser("doctor", help="Check local prerequisites without reading credentials")
    generate = actions.add_parser(
        "generate", help="Generate canonical data, dirty data and evidence"
    )
    config, rules, stages = default_paths()
    generate.add_argument("--config", type=Path, default=config)
    generate.add_argument("--segmentation", type=Path, default=rules)
    generate.add_argument("--stages", type=Path, default=stages)
    generate.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/generated")
    actions.add_parser("db-init", help="Apply checksummed PostgreSQL migrations transactionally")
    inspect = actions.add_parser(
        "sf-inspect", help="Describe standard fields and query active stages"
    )
    inspect.add_argument("--target-org", required=True)
    inspect.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/salesforce/describe")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.command == "generate":
            result = generate_bundle(args.output, args.config, args.segmentation, args.stages)
            print(
                json.dumps(
                    {
                        key: result[key]
                        for key in (
                            "counts",
                            "ground_truth_count",
                            "source_kind",
                            "salesforce_import_ready",
                        )
                    },
                    indent=2,
                )
            )
            print(f"Bundle: {args.output.resolve()}")
        elif args.command == "db-init":
            applied = migrate()
            print("Applied: " + ", ".join(applied) if applied else "Database schema is current.")
        elif args.command == "sf-inspect":
            print(json.dumps(inspect_org(args.target_org, args.output), indent=2))
        elif args.command == "doctor":
            checks = {
                "python": sys.version.split()[0],
                "docker_cli": bool(shutil.which("docker")),
                "local_env_exists": (PROJECT_ROOT / ".env").exists(),
            }
            try:
                executable()
                checks["salesforce_cli_installed"] = True
            except ValueError:
                checks["salesforce_cli_installed"] = False
            print(json.dumps(checks, indent=2))
            print(
                "Installation checks only; database connectivity and org login "
                "require separate checks."
            )
        return 0
    except (ValueError, RuntimeError, OSError, psycopg.Error, subprocess.SubprocessError) as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
