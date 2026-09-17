"""Explicit project configuration; generation never depends on wall-clock time."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


@dataclass(frozen=True)
class GenerationConfig:
    seed: int
    as_of: date
    batch_prefix: str
    accounts: int
    contacts: int
    opportunities: int
    hierarchy_fraction: float
    regions: dict[str, float]
    segments: dict[str, float]
    corruption: dict[str, float]

    @classmethod
    def load(cls, path: Path) -> "GenerationConfig":
        values = read_yaml(path)
        values["as_of"] = date.fromisoformat(str(values["as_of"]))
        return cls(**values)

    def __post_init__(self) -> None:
        if self.accounts < 100 or self.contacts < 100 or self.opportunities < 100:
            raise ValueError("Use at least 100 records per object for the corruption scenarios")
        if not 0 <= self.hierarchy_fraction <= 0.5:
            raise ValueError("hierarchy_fraction must be between 0 and 0.5")
        for distribution in (self.regions, self.segments):
            if any(weight < 0 for weight in distribution.values()):
                raise ValueError("Distribution weights must be nonnegative")
            if abs(sum(distribution.values()) - 1.0) > 1e-9:
                raise ValueError("Distribution weights must add up to one")
        if set(self.regions) != {"US", "UK", "MX"}:
            raise ValueError("Supported synthetic regions are US, UK, MX")
        if set(self.segments) != {"SMB", "Mid-Market", "Enterprise"}:
            raise ValueError("Supported segments are SMB, Mid-Market, Enterprise")
        if any(not 0 <= rate <= 0.2 for rate in self.corruption.values()):
            raise ValueError("Corruption rates must be between 0 and 0.2")
        if not self.batch_prefix.startswith("GTMDQ-SYNTH") or len(self.batch_prefix) > 28:
            raise ValueError("batch_prefix must start GTMDQ-SYNTH and be at most 28 characters")
