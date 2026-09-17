import pytest

from gtmdq.generator.business import expected_region, expected_segment
from gtmdq.generator.opportunities import validate_stages


@pytest.mark.parametrize(
    ("employees", "revenue", "expected"),
    [
        (199, 19999999, "SMB"),
        (200, 1, "Mid-Market"),
        (1, 20000000, "Mid-Market"),
        (999, 99999999, "Mid-Market"),
        (1000, 1, "Enterprise"),
        (1, 100000000, "Enterprise"),
        (None, 100000000, "Enterprise"),
        (None, None, "SMB"),
    ],
)
def test_segmentation_thresholds(employees, revenue, expected, rules):
    assert expected_segment(employees, revenue, rules) == expected


@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("United States", "US"),
        ("United Kingdom", "UK"),
        ("Mexico", "MX"),
        ("Germany", "Other"),
        (None, "Other"),
    ],
)
def test_region_mapping(country, expected, rules):
    assert expected_region(country, rules) == expected


def test_stage_definitions_require_all_three_outcomes(stages):
    validate_stages(stages)
    with pytest.raises(ValueError, match="open stage"):
        validate_stages({"stages": [s for s in stages["stages"] if s["is_closed"]]})
