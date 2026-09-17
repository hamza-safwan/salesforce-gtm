"""Business definitions shared by generation and future quality checks."""

from typing import Any


def expected_segment(employees: int | None, revenue: float | None, rules: dict[str, Any]) -> str:
    employees, revenue = employees or 0, revenue or 0
    enterprise, middle = rules["enterprise"], rules["mid_market"]
    if employees >= enterprise["min_employees"] or revenue >= enterprise["min_revenue"]:
        return "Enterprise"
    if employees >= middle["min_employees"] or revenue >= middle["min_revenue"]:
        return "Mid-Market"
    return "SMB"


def expected_region(country: str | None, rules: dict[str, Any]) -> str:
    return rules["country_regions"].get(country, "Other")
