"""Stage fixtures are explicit; org-derived definitions are required for a later import."""

import random
from datetime import timedelta
from typing import Any

from gtmdq.config import GenerationConfig
from gtmdq.generator.common import Record, provenance


def validate_stages(stage_config: dict[str, Any]) -> None:
    stages = stage_config.get("stages", [])
    if not stages or len({s["api_name"] for s in stages}) != len(stages):
        raise ValueError("Stage definitions must be nonempty with unique API names")
    for stage in stages:
        if not 0 <= stage["probability"] <= 100:
            raise ValueError("Stage probability must be between 0 and 100")
        if type(stage["is_closed"]) is not bool or type(stage["is_won"]) is not bool:
            raise ValueError("Stage status must use YAML booleans")
        if stage["is_won"] and not stage["is_closed"]:
            raise ValueError("A won stage must be closed")
    if not any(not s["is_closed"] for s in stages):
        raise ValueError("At least one open stage is required")
    if not any(s["is_won"] for s in stages):
        raise ValueError("At least one closed-won stage is required")
    if not any(s["is_closed"] and not s["is_won"] for s in stages):
        raise ValueError("At least one closed-lost stage is required")


def generate_opportunities(
    config: GenerationConfig, accounts: list[Record], stage_config: dict[str, Any]
) -> list[Record]:
    validate_stages(stage_config)
    rng = random.Random(config.seed + 2)
    open_stages = [s for s in stage_config["stages"] if not s["is_closed"]]
    won_stages = [s for s in stage_config["stages"] if s["is_won"]]
    lost_stages = [s for s in stage_config["stages"] if s["is_closed"] and not s["is_won"]]
    records = []
    for index in range(1, config.opportunities + 1):
        account = accounts[(index - 1) % len(accounts)]
        group = rng.choices([open_stages, won_stages, lost_stages], [70, 20, 10])[0]
        stage = rng.choice(group)
        days = -rng.randint(1, 180) if stage["is_closed"] else rng.randint(1, 180)
        multiplier = {"SMB": 1, "Mid-Market": 5, "Enterprise": 20}[account["segment"]]
        records.append(
            {
                "external_source_id": f"SYN-O-{index:06d}",
                "name": f"Synthetic Opportunity {index:06d}",
                "account_external_id": account["external_source_id"],
                "stage_name": stage["api_name"],
                "probability": stage["probability"],
                "is_closed": stage["is_closed"],
                "is_won": stage["is_won"],
                "amount": rng.randint(5000, 80000) * multiplier,
                "close_date": str(config.as_of + timedelta(days=days)),
                "lead_source": "Web",
                "region": account["region"],
                "sales_segment": account["segment"],
                **provenance(index, config, rng),
            }
        )
    return records
