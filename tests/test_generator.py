import copy
import hashlib
import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import date
from urllib.parse import urlsplit

import pytest
import yaml

from gtmdq.generator.business import expected_region, expected_segment
from gtmdq.generator.pipeline import default_paths, generate, generate_bundle


def test_exact_counts_identity_and_relationships(dataset):
    canonical, dirty, truth = dataset
    assert {key: len(rows) for key, rows in dirty.items()} == {
        "accounts": 2500,
        "contacts": 5000,
        "opportunities": 2500,
        "enrichment_feed": 2500,
    }
    assert len(truth) == 3800
    account_ids = {row["external_source_id"] for row in canonical["accounts"]}
    for entity in ("accounts", "contacts", "opportunities"):
        original_ids = {row["external_source_id"] for row in canonical[entity]}
        assert len(original_ids) == len(canonical[entity])
        assert original_ids == {row["external_source_id"] for row in dirty[entity]}
    for entity in ("contacts", "opportunities"):
        assert all(row["account_external_id"] in account_ids for row in canonical[entity])


def test_deterministic_for_same_seed_and_changes_for_new_seed(
    dataset, configuration, rules, stages
):
    assert generate(configuration, rules, stages) == dataset
    changed = generate(replace(configuration, seed=43), rules, stages)
    assert changed != dataset
    assert [r["external_source_id"] for r in changed[0]["accounts"]] == [
        r["external_source_id"] for r in dataset[0]["accounts"]
    ]


def test_clean_business_fields_and_distributions(dataset, rules, configuration):
    canonical = dataset[0]
    accounts = {row["external_source_id"]: row for row in canonical["accounts"]}
    assert Counter(row["region"] for row in accounts.values()) == {"US": 1625, "UK": 500, "MX": 375}
    assert Counter(row["segment"] for row in accounts.values()) == {
        "SMB": 1250,
        "Mid-Market": 750,
        "Enterprise": 500,
    }
    for row in accounts.values():
        assert row["segment"] == expected_segment(
            row["number_of_employees"], row["annual_revenue"], rules
        )
        assert row["region"] == expected_region(row["billing_country"], rules)
    for row in canonical["opportunities"]:
        assert row["amount"] > 0
        assert row["sales_segment"] == accounts[row["account_external_id"]]["segment"]
        assert row["region"] == accounts[row["account_external_id"]]["region"]
        if not row["is_closed"]:
            assert date.fromisoformat(row["close_date"]) >= configuration.as_of


def test_synthetic_contact_endpoints_and_markers(dataset):
    canonical = dataset[0]
    for row in canonical["accounts"]:
        assert row["name"].startswith("Synthetic ")
        assert "Synthetic" in row["billing_street"]
        assert urlsplit(row["website"]).hostname.endswith(".example")
        assert row["phone"].startswith("+1-202-555-01")
    for row in canonical["contacts"]:
        assert row["last_name"].endswith("-Synthetic")
        assert row["email"].endswith(".example")
        assert row["phone"].startswith("+1-202-555-01")
        assert row["mobile_phone"].startswith("+1-202-555-01")
    for entity in ("accounts", "contacts", "opportunities"):
        assert all(
            row["ingestion_batch_id"].startswith("GTMDQ-SYNTH-") for row in dataset[1][entity]
        )


def test_ledger_replays_every_mutation_without_overwritten_evidence(dataset):
    canonical, dirty, truth = dataset
    replay = copy.deepcopy(canonical)
    names = {
        "Account": "accounts",
        "Contact": "contacts",
        "Opportunity": "opportunities",
        "Enrichment": "enrichment_feed",
    }
    indexes = {
        entity: {row.get("external_source_id", row.get("external_account_id")): row for row in rows}
        for entity, rows in replay.items()
    }
    touched = set()
    for finding in truth:
        entity, key = names[finding["entity_type"]], finding["external_source_id"]
        row = indexes[entity][key]
        before, after = (
            json.loads(finding["original_value"]),
            json.loads(finding["corrupted_value"]),
        )
        assert before != after
        assert {field: row[field] for field in before} == before
        for field in after:
            assert (entity, key, field) not in touched
            touched.add((entity, key, field))
        row.update(after)
    assert replay == dirty


def test_intentional_opportunity_mismatches_still_fail_final_parent(dataset):
    _, dirty, truth = dataset
    accounts = {r["external_source_id"]: r for r in dirty["accounts"]}
    opportunities = {r["external_source_id"]: r for r in dirty["opportunities"]}
    for issue in truth:
        if issue["rule_id"] in ("O-CONS-002", "O-CONS-003"):
            row = opportunities[issue["external_source_id"]]
            parent = accounts[row["account_external_id"]]
            if issue["rule_id"] == "O-CONS-002":
                assert row["sales_segment"] != parent["segment"]
            else:
                assert row["region"] != parent["region"]


def test_bundle_is_identical_and_detects_tampering(tmp_path, configuration):
    values = asdict(replace(configuration, accounts=100, contacts=200, opportunities=100))
    values["as_of"] = str(values["as_of"])
    config = tmp_path / "generation.yml"
    config.write_text(yaml.safe_dump(values), encoding="utf-8")
    _, rules, stages = default_paths()
    output = tmp_path / "bundle"
    first = generate_bundle(output, config, rules, stages)
    second = generate_bundle(output, config, rules, stages)
    assert first == second
    other = tmp_path / "other"
    assert generate_bundle(other, config, rules, stages) == first
    for name, checksum in first["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == checksum
        assert (output / name).read_bytes() == (other / name).read_bytes()
    accounts = output / "accounts.csv"
    accounts.write_text("modified", encoding="utf-8")
    with pytest.raises(ValueError, match="modified"):
        generate_bundle(output, config, rules, stages)
    assert accounts.read_text() == "modified"  # The user's modification was not overwritten.
