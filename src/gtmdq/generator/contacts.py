"""Generate synthetic people with reserved email domains and fictional phone numbers."""

import random
from datetime import timedelta

from faker import Faker

from gtmdq.config import GenerationConfig
from gtmdq.generator.common import Record, provenance, synthetic_phone


def generate_contacts(config: GenerationConfig, accounts: list[Record]) -> list[Record]:
    rng = random.Random(config.seed + 1)
    fake = Faker("en_US")
    fake.seed_instance(config.seed + 1)
    records = []
    roles = [
        ("Analyst", "Individual Contributor"),
        ("Sales Manager", "Manager"),
        ("Director of Operations", "Director"),
        ("VP Sales", "VP"),
        ("CEO", "C-Level"),
    ]
    for index in range(1, config.contacts + 1):
        account = accounts[(index - 1) % len(accounts)]
        title, seniority = rng.choice(roles)
        records.append(
            {
                "external_source_id": f"SYN-C-{index:06d}",
                "account_external_id": account["external_source_id"],
                "first_name": fake.first_name(),
                "last_name": f"{fake.last_name()}-Synthetic",
                "email": f"person-{index:06d}@{account['canonical_domain']}",
                "phone": synthetic_phone(100000 + index),
                "mobile_phone": synthetic_phone(200000 + index),
                "title": title,
                "department": "Revenue Operations",
                "seniority": seniority,
                "mailing_country": account["billing_country"],
                "contact_status": rng.choices(["Active", "Inactive", "Unknown"], [85, 10, 5])[0],
                "last_enriched_date": str(config.as_of - timedelta(days=rng.randint(1, 90))),
                **provenance(index, config, rng),
            }
        )
    return records
