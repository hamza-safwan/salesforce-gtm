# Synthetic source contract

## Run and inspect

```powershell
.\.venv\Scripts\python.exe -m gtmdq.cli generate
Get-Content data/generated/manifest.json
Import-Csv data/generated/ground_truth_issues.csv | Group-Object corruption_type | Select-Object Name,Count
```

Default counts: 2,500 Accounts, 5,000 Contacts, 2,500 Opportunities. The enrichment
feed has one row per Account and is additional to the 10,000 CRM records. Counts,
seed, reference date, distribution and defect rates are in `config/generation.yml`.
Re-running the same configuration verifies and reuses the same files.

## Files

| File | Meaning |
|---|---|
| `canonical/accounts.csv` | Clean Accounts, including valid corporate families |
| `canonical/contacts.csv` | Clean Contacts with valid external Account associations |
| `canonical/opportunities.csv` | Clean Opportunities consistent with canonical Accounts |
| `canonical/enrichment_feed.csv` | Clean synthetic vendor assertions |
| `accounts.csv`, `contacts.csv`, `opportunities.csv` | Deliberately corrupted source records |
| `enrichment_feed.csv` | Untrusted synthetic vendor feed |
| `ground_truth_issues.csv` | Injected changes, exact original/changed JSON and related duplicate/parent ID |
| `manifest.json` | Configuration, dependency identity, counts and SHA-256 file inventory |

Enrichment approved/rejected files are created by the later DQ validation stage;
the generator does not pretend that dirty vendor assertions have been approved.

## Fields and mappings

Source CSV columns use snake_case. These are **source contracts**, not Salesforce
Bulk API files. Standard fields map explicitly to Salesforce API names during the
later import stage; generated XML contains all project-owned custom API names.

| Source | Salesforce | Meaning |
|---|---|---|
| `external_source_id` | `External_Source_Id__c` | Stable per-object source identity |
| `source_system` | `Source_System__c` | Synthetic acquisition channel |
| `ingestion_batch_id` | `Ingestion_Batch_Id__c` | Batch lineage; synthetic marker retained even when source is missing |
| `parent_external_id` | resolve to `Account.ParentId` | Parent relationship |
| `account_external_id` | resolve to `Contact.AccountId` / `Opportunity.AccountId` | Child association |
| `name` | `Account.Name` / `Opportunity.Name` | Synthetic entity name |
| `website`, `phone` | `Account.Website`, `Phone` | Synthetic contact endpoints |
| `billing_*` | corresponding `Account.Billing*` | Synthetic address; known cities, invented street |
| `industry`, `type` | `Account.Industry`, `Account.Type` | Local fixtures until org values are described |
| `number_of_employees`, `annual_revenue` | `NumberOfEmployees`, `AnnualRevenue` | Segmentation inputs |
| `region`, `segment`, `sales_segment` | `Region__c`, `Segment__c`, `Sales_Segment__c` | Business segmentation |
| `canonical_domain`, `icp_tier` | `Canonical_Domain__c`, `ICP_Tier__c` | Derived domain and targeting tier |
| `enrichment_source`, `last_enriched_date` | `Enrichment_Source__c`, `Last_Enriched_Date__c` | Vendor lineage and freshness |
| `first_name`, `last_name`, `email` | `Contact.FirstName`, `LastName`, `Email` | Synthetic person |
| `mobile_phone`, `title`, `department`, `mailing_country` | `MobilePhone`, `Title`, `Department`, `MailingCountry` | Contact details |
| `seniority`, `contact_status` | `Seniority__c`, `Contact_Status__c` | Contact classification |
| `stage_name`, `amount`, `close_date` | `StageName`, `Amount`, `CloseDate` | Opportunity commercial state |
| `lead_source`, `probability` | `LeadSource`, `Probability` | Opportunity acquisition and likelihood |
| `is_closed`, `is_won` | read-only `IsClosed`, `IsWon` | Derived locally from stage definitions; never write these fields |
| `created_date`, `last_modified_date` | local simulated timestamps | Salesforce system timestamps are read on export, not written on import |
| `corporate_family_id`, `is_subsidiary` | local source metadata | Family assertion for hierarchy investigation, not invented Salesforce fields |

Enrichment fields follow the supplied specification. `enriched_at` is an ISO date,
and `vendor_confidence` is on a 0..1 scale. All revenue is assumed USD for this demo.

## Defect evidence and limitations

Corruptions are sampled without replacement per affected field. Duplicate support
fields are reserved on both members, so later scalar mutations cannot destroy the
intended match. Duplicate targets are existing rows: counts stay exactly 10,000.
Each ledger row captures a mutation event; it is not an exhaustive catalog of every
finding a DQ engine should produce. For example, corrupting an Account's segment
can expose additional mismatches in its otherwise unchanged Opportunities.

Duplicate evaluation must use unordered entity pairs (including the related ID),
not treat the untouched donor as a false positive. Deterministic rule evaluation
must account for downstream failures rather than treating all unlisted checks as
known negatives. No precision or recall is claimed at this milestone.

The source specification requires some corruptions without assigning rule IDs.
These explicit extensions complete the ledger:

| ID | Definition |
|---|---|
| `A-HIER-005` | Parent belongs to a different asserted corporate family |
| `O-COMP-004` | Source attribute missing |
| `E-ENR-001` | Vendor assertion older than 180 days |
| `E-ENR-002` | Vendor domain does not match canonical Account domain |
| `E-COMP-001` | Vendor industry missing |
| `E-ENR-003` | Vendor employee count contradicts canonical count by 10x |

Families contain five members with a maximum of three parent edges to the root.
At default settings 450 Accounts (18%) participate; 360 Accounts have a parent.
These are different denominators. Self-parent and cycle cases remain local until
a later import quarantine determines what Salesforce can accept.

Ground truth is audit-only. No detector may read `canonical/` to obtain the answer.
Detection of the wrong-family case needs source family assertions; Salesforce's
`ParentId` alone cannot establish the real corporate owner.
