# Salesforce GTM Data Quality & Account Intelligence

A Python, PostgreSQL, and Salesforce project for investigating CRM quality,
prioritizing remediation, and measuring the open sales pipeline exposed to bad data.
Only synthetic records are used. Standard Accounts, Contacts, and Opportunities
remain the CRM model; `Data_Quality_Issue__c` will hold the highest-priority findings.

## Current scope

Milestone 1's local foundation is built and tested: **10,000 synthetic CRM records**,
**3,800 audited corruption events**, and **27 passing unit tests**. The PostgreSQL
runtime check is blocked by Docker/WSL startup on the development machine. Salesforce
deployment is **not verified** until an authenticated Developer Edition org returns
a successful deployment result.
The DQ engine, Salesforce data movement, scorecards, and Power BI belong to later
milestones. See [the milestone tracker](docs/milestones.md) for verification evidence.

## Local setup (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
.\.venv\Scripts\python.exe scripts/init_env.py
docker compose up -d --wait
.\.venv\Scripts\python.exe -m gtmdq.cli db-init
.\.venv\Scripts\python.exe -m gtmdq.cli generate
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

Python 3.11+, Node.js 22+, and Docker Desktop with Linux containers are required.
The Node dependency is the official Salesforce CLI, installed inside this project.
Power BI Desktop is a later reporting dependency. PostgreSQL binds only to loopback.

## Salesforce setup

Create and activate a free [Developer Edition org](https://developer.salesforce.com/signup).
Then follow [Salesforce setup](docs/salesforce_setup.md). Authentication is handled
by the CLI outside source control; no access tokens are printed by project code.

```powershell
npm.cmd run sf -- org login web --alias gtmdq
.\.venv\Scripts\python.exe -m gtmdq.cli sf-inspect --target-org gtmdq
npm.cmd run sf -- project deploy start --source-dir force-app/main/default --target-org gtmdq --wait 10
npm.cmd run sf -- org assign permset --name GTMDQ_Operator --target-org gtmdq
```

Validation rules ship inactive. Duplicate-rule configuration and report creation
remain hands-on Salesforce learning steps described in the setup guide.

## Data and reproducibility

`config/generation.yml` fixes seed 42 and a reference date. Generation writes 2,500
Accounts, 5,000 Contacts, 2,500 Opportunities, a 2,500-row enrichment feed, canonical
copies, a corruption ledger, and a manifest with SHA-256 hashes. Output is ignored
by Git and reproducible from pinned dependencies and source configuration.

The default Opportunity stages are **unverified local fixtures**. `sf-inspect`
discovers the actual org stage API names. Local fixture data is not an import file.
Dates are evaluated relative to the manifest's `as_of`, not today's date.

## Business definitions

- Enterprise: employees >= 1,000 **or** revenue >= 100 million.
- Mid-Market: employees >= 200 **or** revenue >= 20 million, after Enterprise.
- SMB: otherwise. Definitions live in `config/segmentation.yml`.
- Six planned quality dimensions: Completeness, Validity, Consistency, Uniqueness,
  Hierarchy, and Enrichment.
- Planned scoring: weighted passed checks / applicable checks, with non-applicable
  checks excluded. Dimension weights and severity precedence will be explicit.
- Planned pipeline risk: distinct affected **open** Opportunities, counted once
  at the enterprise level even when several findings expose the same Opportunity.
- Planned root-cause analysis: issue rates and exposure by source, batch, region,
  segment, vendor, entity, and rule, with denominators stated.
- Remediation will separate reviewable deterministic updates from human duplicate
  decisions. No automatic merges. Priority weights are a demo business policy.

## Documentation and limitations

- [Architecture and decisions](docs/architecture.md)
- [Milestones and acceptance evidence](docs/milestones.md)
- [Generator contract](docs/generation.md)
- [Salesforce setup](docs/salesforce_setup.md)
- [Custom field dictionary](docs/data_dictionary.md)
- [Dependency status and unresolved CLI advisories](docs/dependency_status.md)

Dashboard screenshots, before/after scores, and measured business results will be
added after those artifacts exist. Synthetic names may coincidentally resemble real
names; no real source data is read. Addresses explicitly contain "Synthetic", and
contact endpoints use reserved fictional ranges. Phones intentionally use one
fictional NANP range in every region; regional phone realism is not claimed.

## References

The CLI workflow follows the [official Salesforce CLI data commands](https://github.com/salesforcecli/plugin-data).
Database health checks follow [Docker Compose startup guidance](https://docs.docker.com/compose/how-tos/startup-order/).
