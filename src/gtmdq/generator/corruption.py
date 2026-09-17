"""Audited mutations with field reservations so later defects cannot erase evidence."""

import copy
import json
import random
from datetime import timedelta
from typing import Any

from gtmdq.config import GenerationConfig
from gtmdq.generator.common import Record


class Corruptor:
    def __init__(self, config: GenerationConfig) -> None:
        self.config = config
        self.rng = random.Random(config.seed + 3)
        self.truth: list[Record] = []
        self.reserved: set[tuple[str, str, str]] = set()

    @staticmethod
    def key(row: Record) -> str:
        return row.get("external_source_id", row.get("external_account_id"))

    def reserve(self, entity: str, row: Record, fields: list[str]) -> None:
        self.reserved.update((entity, self.key(row), field) for field in fields)

    def choose(
        self, entity: str, rows: list[Record], fields: list[str], count: int
    ) -> list[Record]:
        available = [
            row
            for row in rows
            if all((entity, self.key(row), field) not in self.reserved for field in fields)
        ]
        if count > len(available):
            raise ValueError(f"Not enough eligible {entity} records for {fields}: need {count}")
        return self.rng.sample(available, count)

    def change(
        self,
        entity: str,
        row: Record,
        rule: str,
        kind: str,
        changes: dict[str, Any],
        related: str | None = None,
    ) -> None:
        original = {field: row[field] for field in changes}
        if original == changes:
            raise ValueError(f"Corruption {kind} would make no change to {self.key(row)}")
        if any((entity, self.key(row), field) in self.reserved for field in changes):
            raise ValueError(f"Corruption {kind} would overwrite earlier evidence")
        self.truth.append(
            {
                "ground_truth_id": f"GT-{len(self.truth) + 1:06d}",
                "entity_type": entity,
                "external_source_id": self.key(row),
                "rule_id": rule,
                "corruption_type": kind,
                "original_value": json.dumps(original, sort_keys=True),
                "corrupted_value": json.dumps(changes, sort_keys=True),
                "related_external_source_id": related,
            }
        )
        row.update(changes)
        self.reserve(entity, row, list(changes))

    def count(self, name: str, rows: list[Record]) -> int:
        return round(self.config.corruption[name] * len(rows))

    def scalar(
        self,
        entity: str,
        rows: list[Record],
        config_key: str,
        field: str,
        value: Any,
        rule: str,
        eligible: list[Record] | None = None,
    ) -> None:
        chosen = self.choose(
            entity, rows if eligible is None else eligible, [field], self.count(config_key, rows)
        )
        for row in chosen:
            changed = value(row) if callable(value) else value
            self.change(entity, row, rule, config_key, {field: changed})

    def accounts(self, rows: list[Record]) -> None:
        fields = ["name", "website", "canonical_domain", "phone", "billing_country", "billing_city"]
        standalone = [
            row
            for row in rows
            if not row["is_subsidiary"] and row["corporate_family_id"] == row["external_source_id"]
        ]
        pairs = self.choose(
            "Account", standalone, fields, self.count("account_duplicate", rows) * 2
        )
        for target, donor in zip(pairs[::2], pairs[1::2], strict=True):
            changes = {field: donor[field] for field in fields}
            changes.update(
                name=f"{donor['name']} LLC",
                website=f"https://www.{donor['canonical_domain']}/",
                phone=donor["phone"].replace("-", " "),
            )
            self.change(
                "Account", target, "A-UNIQ-001", "account_duplicate", changes, self.key(donor)
            )
            self.reserve("Account", donor, fields)
        rules = [
            ("account_missing_industry", "industry", None, "A-COMP-002"),
            ("account_missing_website", "website", None, "A-COMP-001"),
            ("account_invalid_website", "website", "ht!tp://bad domain.invalid", "A-VALID-001"),
            ("account_segment", "segment", lambda r: other_segment(r["segment"]), "A-CONS-002"),
            (
                "account_region",
                "region",
                lambda r: "UK" if r["region"] != "UK" else "US",
                "A-CONS-001",
            ),
            ("account_stale", "last_enriched_date", self.stale_date, "A-ENR-001"),
        ]
        for key, field, value, rule in rules:
            self.scalar("Account", rows, key, field, value, rule)
        self.hierarchies(rows)

    @property
    def stale_date(self) -> str:
        return str(self.config.as_of - timedelta(days=240))

    def hierarchies(self, rows: list[Record]) -> None:
        count = self.count("account_hierarchy", rows)
        group = count // 4
        subsidiaries = [row for row in rows if row["is_subsidiary"]]
        for row in self.choose("Account", subsidiaries, ["parent_external_id"], group):
            self.change(
                "Account",
                row,
                "A-HIER-003",
                "hierarchy_missing_parent",
                {"parent_external_id": None},
            )
        roots = [row for row in rows if not row["is_subsidiary"]]
        # Use standalone Accounts, so self/cycle injection does not create incidental
        # anomalies in all the descendants of a legitimate family.
        referenced = {row["parent_external_id"] for row in rows if row["parent_external_id"]}
        standalone = [row for row in roots if self.key(row) not in referenced]
        for row in self.choose("Account", standalone, ["parent_external_id"], group):
            self.change(
                "Account",
                row,
                "A-HIER-001",
                "hierarchy_self_parent",
                {"parent_external_id": self.key(row)},
            )
        cycle_count = group // 2 * 2
        pairs = self.choose("Account", standalone, ["parent_external_id"], cycle_count)
        for left, right in zip(pairs[::2], pairs[1::2], strict=True):
            self.change(
                "Account",
                left,
                "A-HIER-002",
                "hierarchy_cycle",
                {"parent_external_id": self.key(right)},
                self.key(right),
            )
            self.change(
                "Account",
                right,
                "A-HIER-002",
                "hierarchy_cycle",
                {"parent_external_id": self.key(left)},
                self.key(left),
            )
        remaining = count - group * 2 - cycle_count
        for row in self.choose("Account", subsidiaries, ["parent_external_id"], remaining):
            candidates = [
                r
                for r in roots
                if r["corporate_family_id"] != row["corporate_family_id"]
                and not r["parent_external_id"]
            ]
            parent = self.rng.choice(candidates)
            self.change(
                "Account",
                row,
                "A-HIER-005",
                "hierarchy_wrong_family",
                {"parent_external_id": self.key(parent)},
                self.key(parent),
            )

    def contacts(self, rows: list[Record]) -> None:
        fields = ["email", "phone", "account_external_id", "first_name", "last_name"]
        pairs = self.choose("Contact", rows, fields, self.count("contact_duplicate", rows) * 2)
        for index, (target, donor) in enumerate(zip(pairs[::2], pairs[1::2], strict=True)):
            kind = index % 3
            if kind == 0:
                changes = {"email": donor["email"].upper()}
            elif kind == 1:
                changes = {
                    "phone": donor["phone"].replace("-", " "),
                    "account_external_id": donor["account_external_id"],
                }
            else:
                changes = {
                    "account_external_id": donor["account_external_id"],
                    "first_name": f"{donor['first_name']}a",
                    "last_name": donor["last_name"],
                }
            self.change(
                "Contact",
                target,
                f"C-UNIQ-00{kind + 1}",
                "contact_duplicate",
                changes,
                self.key(donor),
            )
            self.reserve("Contact", donor, fields)
            self.reserve("Contact", target, fields)
        for key, field, value, rule in [
            ("contact_missing_email", "email", None, "C-COMP-001"),
            ("contact_invalid_email", "email", "person@@company.example", "C-VALID-001"),
            ("contact_invalid_phone", "phone", "phone???", "C-VALID-002"),
            ("contact_orphan", "account_external_id", None, "C-COMP-002"),
            ("contact_stale", "last_enriched_date", self.stale_date, "C-ENR-001"),
        ]:
            self.scalar("Contact", rows, key, field, value, rule)

    def opportunities(self, rows: list[Record], accounts: list[Record]) -> None:
        account_map = {self.key(row): row for row in accounts}
        # Child comparisons use the *dirty* parent values. Existing incidental
        # mismatches remain observable, but deliberate injections always fail.
        for key, field, value, rule in [
            ("opportunity_missing_amount", "amount", None, "O-COMP-002"),
            ("opportunity_nonpositive_amount", "amount", 0, "O-VALID-001"),
            (
                "opportunity_segment",
                "sales_segment",
                lambda r: next(
                    s
                    for s in ("SMB", "Mid-Market", "Enterprise")
                    if s
                    not in (r["sales_segment"], account_map[r["account_external_id"]]["segment"])
                ),
                "O-CONS-002",
            ),
            (
                "opportunity_region",
                "region",
                lambda r: next(
                    s
                    for s in ("US", "UK", "MX", "Other")
                    if s not in (r["region"], account_map[r["account_external_id"]]["region"])
                ),
                "O-CONS-003",
            ),
            ("opportunity_source", "source_system", None, "O-COMP-004"),
        ]:
            self.scalar("Opportunity", rows, key, field, value, rule)
        self.scalar(
            "Opportunity",
            rows,
            "opportunity_past_due",
            "close_date",
            str(self.config.as_of - timedelta(days=30)),
            "O-CONS-001",
            eligible=[row for row in rows if not row["is_closed"]],
        )

    def enrichment(self, rows: list[Record]) -> None:
        for key, field, value, rule in [
            ("enrichment_stale", "enriched_at", self.stale_date, "E-ENR-001"),
            ("enrichment_domain", "website", "https://unrelated-company.example", "E-ENR-002"),
            ("enrichment_missing", "industry", None, "E-COMP-001"),
            (
                "enrichment_employees",
                "number_of_employees",
                lambda r: r["number_of_employees"] * 10,
                "E-ENR-003",
            ),
            ("enrichment_country", "billing_country", "Atlantis", "A-ENR-003"),
            ("enrichment_confidence", "vendor_confidence", 0.35, "A-ENR-002"),
        ]:
            self.scalar("Enrichment", rows, key, field, value, rule)


def other_segment(segment: str) -> str:
    return "SMB" if segment != "SMB" else "Enterprise"


def inject_corruption(
    config: GenerationConfig, canonical: dict[str, list[Record]]
) -> tuple[dict[str, list[Record]], list[Record]]:
    dirty = copy.deepcopy(canonical)
    corruptor = Corruptor(config)
    corruptor.accounts(dirty["accounts"])
    corruptor.contacts(dirty["contacts"])
    corruptor.opportunities(dirty["opportunities"], dirty["accounts"])
    corruptor.enrichment(dirty["enrichment_feed"])
    return dirty, corruptor.truth
