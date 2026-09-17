"""A separate synthetic vendor feed, never silently accepted as authoritative."""

from gtmdq.generator.common import Record


def generate_enrichment(accounts: list[Record]) -> list[Record]:
    return [
        {
            "external_account_id": account["external_source_id"],
            "website": account["website"],
            "industry": account["industry"],
            "number_of_employees": account["number_of_employees"],
            "annual_revenue": account["annual_revenue"],
            "billing_country": account["billing_country"],
            "enriched_at": account["last_enriched_date"],
            "vendor_name": account["enrichment_source"],
            "vendor_confidence": 0.98,
        }
        for account in accounts
    ]
