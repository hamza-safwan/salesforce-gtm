"""Generate into a temporary sibling directory, publishing only a complete bundle."""

import csv
import hashlib
import json
import tempfile
from collections import Counter
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Any

from gtmdq import __version__
from gtmdq.config import PROJECT_ROOT, GenerationConfig, read_yaml
from gtmdq.generator.accounts import generate_accounts
from gtmdq.generator.common import Record
from gtmdq.generator.contacts import generate_contacts
from gtmdq.generator.corruption import inject_corruption
from gtmdq.generator.enrichment import generate_enrichment
from gtmdq.generator.opportunities import generate_opportunities

TRUTH_FIELDS = [
    "ground_truth_id",
    "entity_type",
    "external_source_id",
    "rule_id",
    "corruption_type",
    "original_value",
    "corrupted_value",
    "related_external_source_id",
]


def generate(
    config: GenerationConfig, rules: dict[str, Any], stages: dict[str, Any]
) -> tuple[dict[str, list[Record]], dict[str, list[Record]], list[Record]]:
    accounts = generate_accounts(config, rules)
    canonical = {
        "accounts": accounts,
        "contacts": generate_contacts(config, accounts),
        "opportunities": generate_opportunities(config, accounts, stages),
        "enrichment_feed": generate_enrichment(accounts),
    }
    dirty, truth = inject_corruption(config, canonical)
    return canonical, dirty, truth


def write_csv(path: Path, rows: list[Record], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_bundle(
    output: Path, config_path: Path, rules_path: Path, stages_path: Path
) -> dict[str, Any]:
    config = GenerationConfig.load(config_path)
    rules, stages = read_yaml(rules_path), read_yaml(stages_path)
    canonical, dirty, truth = generate(config, rules, stages)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "generator_version": __version__,
        "faker_version": version("Faker"),
        "config": asdict(config),
        "segmentation": rules,
        "stage_definitions": stages,
        "counts": {key: len(rows) for key, rows in dirty.items()},
        "ground_truth_count": len(truth),
        "corruption_counts": dict(sorted(Counter(r["corruption_type"] for r in truth).items())),
        "source_kind": "synthetic_local",
        "salesforce_import_ready": False,
    }
    # Existing deterministic output is reusable. Different generation settings get
    # a separate directory, preserving prior input data and baseline evidence.
    with tempfile.TemporaryDirectory(prefix=".gtmdq-generate-", dir=output.parent) as temp:
        staging = Path(temp)
        for name, rows in canonical.items():
            write_csv(staging / "canonical" / f"{name}.csv", rows)
        for name, rows in dirty.items():
            write_csv(staging / f"{name}.csv", rows)
        write_csv(staging / "ground_truth_issues.csv", truth, TRUTH_FIELDS)
        hashes = {
            path.relative_to(staging).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(staging.rglob("*.csv"))
        }
        manifest["files"] = hashes
        rendered = json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n"
        (staging / "manifest.json").write_text(rendered, encoding="utf-8")
        if output.exists():
            existing = output / "manifest.json"
            if not existing.is_file() or existing.read_text(encoding="utf-8") != rendered:
                raise ValueError(f"{output} already exists with different contents; use --output")
            for name, expected_hash in hashes.items():
                path = output / name
                if (
                    not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash
                ):
                    raise ValueError(f"Existing bundle is modified: {path}; use a new --output")
        else:
            staging.rename(output)
    return json.loads(rendered)


def default_paths() -> tuple[Path, Path, Path]:
    return tuple(
        PROJECT_ROOT / "config" / name
        for name in ("generation.yml", "segmentation.yml", "opportunity_stages.yml")
    )
