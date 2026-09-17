"""Shared source contracts and deterministic sampling utilities."""

import random
from datetime import timedelta
from typing import Any

from gtmdq.config import GenerationConfig

Record = dict[str, Any]
SOURCES = ("Web Monitoring", "Enrichment Vendor", "Manual Entry", "Partner Feed")
COUNTRIES = {"US": "United States", "UK": "United Kingdom", "MX": "Mexico"}


def weighted_population(weights: dict[str, float], count: int, rng: random.Random) -> list[str]:
    """Largest remainder allocation avoids drift in small representative datasets."""
    sizes = {key: int(count * weight) for key, weight in weights.items()}
    remainder = sorted(weights, key=lambda k: (-(count * weights[k] - sizes[k]), k))
    for key in remainder[: count - sum(sizes.values())]:
        sizes[key] += 1
    values = [key for key, size in sizes.items() for _ in range(size)]
    rng.shuffle(values)
    return values


def provenance(index: int, config: GenerationConfig, rng: random.Random) -> Record:
    created = config.as_of - timedelta(days=rng.randint(190, 730))
    modified = config.as_of - timedelta(days=rng.randint(1, 30))
    return {
        "source_system": SOURCES[index % len(SOURCES)],
        "ingestion_batch_id": f"{config.batch_prefix}-{config.as_of:%Y%m%d}-{index % 4 + 1:02d}",
        "created_date": f"{created}T09:00:00Z",
        "last_modified_date": f"{modified}T12:00:00Z",
    }


def synthetic_phone(index: int) -> str:
    """Reserved NANP fictional number; unique extension prevents accidental exact matches.

    All regions deliberately use the reserved fictional range instead of inventing
    potentially assigned UK/Mexico numbers. This limitation is documented.
    """
    return f"+1-202-555-{100 + index % 100:04d} ext {index:06d}"
