"""Use argument arrays and parse JSON; never obtain or log an access token."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from gtmdq.config import PROJECT_ROOT


def executable() -> list[str]:
    local = PROJECT_ROOT / "node_modules/@salesforce/cli/bin/run.js"
    node = shutil.which("node")
    if local.is_file() and node:
        # Invoking node directly avoids Windows .cmd quoting and shell expansion.
        return [node, str(local)]
    sf = shutil.which("sf")
    if sf:
        return [sf]
    raise ValueError("Salesforce CLI is missing. Run npm.cmd ci in the project root.")


def run_json(arguments: list[str], target_org: str) -> dict[str, Any]:
    command = executable() + arguments + ["--target-org", target_org, "--json"]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Salesforce CLI returned non-JSON output; run the command interactively"
        ) from exc
    if result.returncode or payload.get("status") != 0:
        # Raw command output is deliberately not echoed; it is not needed to
        # diagnose a missing login and may include org-specific information.
        error_name = payload.get("name", "SalesforceCommandError")
        raise RuntimeError(f"Salesforce command failed ({error_name}); verify login and org access")
    return payload["result"]


def inspect_org(target_org: str, output: Path) -> dict[str, Any]:
    """Read standard fields and active stages before any schema or data deployment."""
    descriptions = {}
    for obj in ("Account", "Contact", "Opportunity", "OpportunityStage"):
        description = run_json(["sobject", "describe", "--sobject", obj], target_org)
        descriptions[obj] = {
            "name": description["name"],
            "fields": [
                {
                    key: field.get(key)
                    for key in (
                        "name",
                        "type",
                        "createable",
                        "updateable",
                        "nillable",
                        "picklistValues",
                    )
                }
                for field in description["fields"]
            ],
        }
    fields = {field["name"] for field in descriptions["OpportunityStage"]["fields"]}
    required = {"ApiName", "IsActive", "DefaultProbability", "IsClosed", "IsWon", "SortOrder"}
    if not required <= fields:
        raise ValueError(
            f"OpportunityStage describe lacks expected fields: {sorted(required - fields)}"
        )
    query = (
        "SELECT ApiName, DefaultProbability, IsClosed, IsWon FROM OpportunityStage "
        "WHERE IsActive = true ORDER BY SortOrder"
    )
    stages = run_json(["data", "query", "--query", query], target_org)
    if not stages.get("done", True) or stages.get("totalSize") != len(stages["records"]):
        raise RuntimeError("Stage query was incomplete; resolve pagination before generation")
    stage_config = {
        "source": "salesforce_describe",
        "target_org_alias": target_org,
        "stages": [
            {
                "api_name": row["ApiName"],
                "probability": row["DefaultProbability"],
                "is_closed": row["IsClosed"],
                "is_won": row["IsWon"],
            }
            for row in stages["records"]
        ],
    }
    from gtmdq.generator.opportunities import validate_stages

    validate_stages(stage_config)
    output.mkdir(parents=True, exist_ok=True)
    (output / "org_schema.json").write_text(
        json.dumps(descriptions, indent=2) + "\n", encoding="utf-8"
    )
    (output / "opportunity_stages.yml").write_text(
        yaml.safe_dump(stage_config, sort_keys=False), encoding="utf-8"
    )
    return {
        "objects_described": list(descriptions),
        "active_stages": len(stage_config["stages"]),
        "output": str(output),
    }
