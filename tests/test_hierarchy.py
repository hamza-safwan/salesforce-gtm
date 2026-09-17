from collections import Counter


def test_clean_families_are_acyclic_and_have_bounded_depth(dataset):
    rows = {row["external_source_id"]: row for row in dataset[0]["accounts"]}
    family_sizes = Counter(row["corporate_family_id"] for row in rows.values())
    assert sum(size for size in family_sizes.values() if size > 1) == 450
    assert sum(row["is_subsidiary"] for row in rows.values()) == 360
    max_depth = 0
    for account in rows.values():
        row, visited, depth = account, set(), 0
        while row["parent_external_id"]:
            assert row["external_source_id"] not in visited
            visited.add(row["external_source_id"])
            row = rows[row["parent_external_id"]]
            assert row["corporate_family_id"] == account["corporate_family_id"]
            depth += 1
        assert row["external_source_id"] == account["corporate_family_id"]
        max_depth = max(max_depth, depth)
    assert max_depth == 3


def test_hierarchy_defects_are_present_and_traceable(dataset):
    _, dirty, truth = dataset
    rows = {row["external_source_id"]: row for row in dirty["accounts"]}
    hierarchy = [issue for issue in truth if issue["rule_id"].startswith("A-HIER")]
    assert len(hierarchy) == 50
    for issue in hierarchy:
        row = rows[issue["external_source_id"]]
        if issue["rule_id"] == "A-HIER-001":
            assert row["parent_external_id"] == row["external_source_id"]
        elif issue["rule_id"] == "A-HIER-002":
            other = rows[row["parent_external_id"]]
            assert other["parent_external_id"] == row["external_source_id"]
        elif issue["rule_id"] == "A-HIER-003":
            assert row["is_subsidiary"] and row["parent_external_id"] is None
        else:
            assert (
                row["corporate_family_id"] != rows[row["parent_external_id"]]["corporate_family_id"]
            )
