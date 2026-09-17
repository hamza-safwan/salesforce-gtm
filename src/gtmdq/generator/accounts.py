"""Generate Accounts first so dependent entities can reference stable external IDs."""

import random
from datetime import timedelta
from typing import Any

from faker import Faker

from gtmdq.config import GenerationConfig
from gtmdq.generator.business import expected_segment
from gtmdq.generator.common import (
    COUNTRIES,
    Record,
    provenance,
    synthetic_phone,
    weighted_population,
)


def generate_accounts(config: GenerationConfig, rules: dict[str, Any]) -> list[Record]:
    rng = random.Random(config.seed)
    fake = Faker("en_US")
    fake.seed_instance(config.seed)
    regions = weighted_population(config.regions, config.accounts, rng)
    segments = weighted_population(config.segments, config.accounts, rng)
    places = {
        "US": [("Austin", "Texas", "78701"), ("Boston", "Massachusetts", "02108")],
        "UK": [("London", "England", "SW1A 1AA"), ("Manchester", "England", "M1 1AD")],
        "MX": [("Mexico City", "Ciudad de Mexico", "06000"), ("Monterrey", "Nuevo Leon", "64000")],
    }
    records = []
    for index, (region, segment) in enumerate(zip(regions, segments, strict=True), start=1):
        if segment == "Enterprise":
            employees = rng.randint(rules["enterprise"]["min_employees"], 12000)
            revenue = rng.randint(rules["enterprise"]["min_revenue"], 900000000)
        elif segment == "Mid-Market":
            employees = rng.randint(
                rules["mid_market"]["min_employees"], rules["enterprise"]["min_employees"] - 1
            )
            revenue = rng.randint(
                rules["mid_market"]["min_revenue"], rules["enterprise"]["min_revenue"] - 1
            )
        else:
            employees = rng.randint(5, rules["mid_market"]["min_employees"] - 1)
            revenue = rng.randint(100000, rules["mid_market"]["min_revenue"] - 1)
        city, state, postcode = rng.choice(places[region])
        domain = f"company-{index:06d}.example"
        external_id = f"SYN-A-{index:06d}"
        records.append(
            {
                "external_source_id": external_id,
                "name": f"Synthetic {fake.company()} {index:06d}",
                "website": f"https://{domain}",
                "canonical_domain": domain,
                "phone": synthetic_phone(index),
                "billing_street": f"{index} Synthetic Example Avenue",
                "billing_city": city,
                "billing_state": state,
                "billing_postal_code": postcode,
                "billing_country": COUNTRIES[region],
                "industry": rng.choice(["Technology", "Manufacturing", "Retail", "Healthcare"]),
                "number_of_employees": employees,
                "annual_revenue": revenue,
                "type": "Prospect",
                "parent_external_id": None,
                "corporate_family_id": external_id,
                "is_subsidiary": False,
                "region": region,
                "segment": expected_segment(employees, revenue, rules),
                "icp_tier": {"Enterprise": "Tier 1", "Mid-Market": "Tier 2", "SMB": "Tier 3"}[
                    segment
                ],
                "enrichment_source": f"Synthetic Vendor {'A' if index % 2 else 'B'}",
                "last_enriched_date": str(config.as_of - timedelta(days=rng.randint(1, 90))),
                **provenance(index, config, rng),
            }
        )
    # Five-member families, at most three parent edges from any Account to its root.
    members = int(config.accounts * config.hierarchy_fraction) // 5 * 5
    for offset in range(0, members, 5):
        family = records[offset : offset + 5]
        for child_index, parent_index in ((1, 0), (2, 1), (3, 2), (4, 0)):
            child, parent = family[child_index], family[parent_index]
            child["parent_external_id"] = parent["external_source_id"]
            child["corporate_family_id"] = family[0]["external_source_id"]
            child["is_subsidiary"] = True
            child["name"] = f"{family[0]['name']} Division {child_index}"
    return records
