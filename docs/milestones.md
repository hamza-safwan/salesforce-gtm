# Delivery milestones and evidence

This is a three-to-four-day implementation plan, with verification gates rather
than a promise that external account setup or report building is automatic.

## 1. Foundation and source data

- [x] Python package, project-local Salesforce CLI configuration, Git exclusions.
- [x] PostgreSQL 16 Compose configuration and transactional migration runner.
- [x] Salesforce schema declarations and inactive prevention rule definitions.
- [x] Canonical synthetic generator and separately audited corruption.
- [x] Python dependencies installed; 27 unit tests pass and lint passes.
- [ ] PostgreSQL healthy; migration applied and rerun verified.
- [x] Full 10,000 CRM records generated and hashes verified on rerun.
- [ ] Developer Edition created and browser authentication completed.
- [ ] Org fields/stages described and schema deployment verified.

Gate: show local evidence and complete the browser-only org setup together.
Do not call this milestone fully complete while deployment is pending.

## 2. CRM round trip and DQ detection

Implement representative subset selection with relationship closure and coverage
evidence; quarantine relationships Salesforce cannot accept. Describe standard
picklists; import using external IDs; verify per-object counts. Export the actual
org and ingest separately from the full synthetic local dataset. Implement six
dimensions, safe recursive SQL, blocked duplicate matching and enrichment approval.

Gate: real Salesforce counts, preserved snapshots, known-defect coverage and tests.

## 3. Business impact and remediation

Implement configurable scores, distinct-opportunity exposure, source/batch root
cause rates, priority queue, review-state persistence and bounded Salesforce
pushback. Run baseline and reviewed deterministic remediation, then re-evaluate.

Gate: measured before/after runs, no duplicate Salesforce issues on rerun, no merges.

## 4. Operational presentation

Build Salesforce matching rules, duplicate rules, reports and dashboard in the UI
as specified. Activate prevention after the baseline, noting that rules can also
block DQ-only updates to existing dirty records. Build Power BI Desktop against
verified views, then document the case study and five-minute demonstration.

Gate: real screenshots and report artifacts. Optional AI starts only after this.

## Verification log

Observed on the initial Windows development environment:

| Check | Observed result |
|---|---|
| Python | 3.11.5, isolated `.venv`, dependencies installed; `pip check` passed |
| Salesforce CLI | Official project-local CLI 2.150.6, Node 24.11.1 |
| Unit tests | First suite: 25 passed; two added Salesforce contract tests: 2 passed |
| Database integration tests | 2 tests written; not run because Docker is unavailable |
| Ruff | Lint and formatting pass |
| Generation | 2,500 Accounts / 5,000 Contacts / 2,500 Opportunities |
| Enrichment | 2,500 additional synthetic vendor assertions |
| Ground truth | 3,800 mutation events; replay test reconstructs the dirty dataset exactly |
| Repeat generation | Existing bundle hashes verified; contents reused without duplicate rows |
| Canonical hierarchies | 450 family members; 360 children; maximum depth 3 parent edges |
| Metadata | 46 custom fields, one custom object, three inactive rules, one permission set |
| Metadata conversion | `sf project convert source` returned status 0; output in ignored `.local/metadata-validation` |
| Metadata drift | `scripts/build_metadata.py --check` passed |
| Compose configuration | `docker compose config --quiet` passed; no container created yet |
| Docker runtime | Engine API returned HTTP 500; logs waiting for WSL init for >25 minutes; normal restart timed out |
| WSL diagnostic | Version 2.6.1.0, kernel 6.6.87.2-1; user reports an update/restart prompt; exact prompt still needed |
| Salesforce deployment | Not attempted; user still needs to create and authenticate Developer Edition |
| Git | Initialized on `main`; credentials, generated data, snapshots, and dependencies confirmed ignored; no remote or commit yet |

Metadata conversion is a local packaging check, not a successful org deployment.
No Salesforce records, DQ runs, business-impact measurements, or dashboards have
been claimed. The complete MVP acceptance checklist remains in the original
[project specification](project_specification.txt).

## Resume here

1. Finish free Developer Edition signup and email activation. Run browser login
   from [Salesforce setup](salesforce_setup.md), then describe the org and deploy.
2. Capture the exact wording of Docker Desktop's WSL update/restart prompt. Installed
   WSL 2.6.1 exceeds Docker's documented minimum 2.1.5, so the observed prompt alone
   does not establish that the installed version is too old. See
   [Docker's WSL requirements](https://docs.docker.com/desktop/features/wsl/).
   Recover Docker Desktop's WSL startup through the desktop application. A normal
   `docker desktop restart --timeout 60` has already failed; inspect its displayed
   diagnostic or restart Windows at a suitable time if the application cannot exit.
3. Once Docker's engine is running, execute:

```powershell
docker compose up -d --wait
.\.venv\Scripts\python.exe -m gtmdq.cli db-init
.\.venv\Scripts\python.exe -m gtmdq.cli db-init
$env:GTMDQ_RUN_DB_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -m integration
Remove-Item Env:GTMDQ_RUN_DB_TESTS
```

The second `db-init` must report that the schema is current. Integration checks
verify migration drift detection and transaction rollback against real PostgreSQL.
After both environment gates pass, proceed to milestone 2's CRM round trip.
