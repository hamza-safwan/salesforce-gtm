# Salesforce setup and learning checklist

## 1. Create the free org (you)

Use [Developer Edition signup](https://developer.salesforce.com/signup), complete
email activation, and open Setup. Confirm standard Account, Contact and Opportunity
objects and API access. This is a dedicated synthetic-data org. A paid Salesforce
subscription and a custom OAuth client are not required.

## 2. CLI and authentication

From the project directory in PowerShell:

```powershell
npm.cmd ci
npm.cmd run sf -- version
npm.cmd run sf -- org login web --alias gtmdq
.\.venv\Scripts\python.exe -m gtmdq.cli sf-inspect --target-org gtmdq
```

Login opens your browser. Credentials remain in the Salesforce CLI user directory;
do not copy authentication files, access tokens or raw `org display` output into
the repository. The project does not change your global default org.

`sf-inspect` stores standard field descriptions, picklist definitions and active
Opportunity stage API names under ignored `data/salesforce/describe/`. This is a
read-only inspection. It does not prove that metadata was deployed or records loaded.

## 3. Generate and deploy the schema

```powershell
.\.venv\Scripts\python.exe scripts/build_metadata.py --check
npm.cmd run sf -- project deploy start --source-dir force-app/main/default --target-org gtmdq --wait 10
npm.cmd run sf -- org assign permset --name GTMDQ_Operator --target-org gtmdq
```

Use API version 65.0 as the project's pinned baseline; confirm target compatibility
when connected. If a deployment times out, use the returned job ID with
`sf project deploy report`; a job ID is not a success result.

Verify each custom field in Object Manager and the auto-numbered Data Quality Issue
object. The permission set grants read/create/edit with no delete or view-all rights.
All three prevention rules are inactive. Field XML and dictionary are generated
from `config/salesforce_schema.yml`; `--check` detects drift without writing files.

If component dependencies fail, deploy object metadata first, then the permission set.
Record actual component errors and adapt to the described org. Do not guess standard
picklist values. Industry, Type, LeadSource and stages require org inspection.

## 4. Next milestone: import and export

The import implementation is not part of milestone 1. The required sequence is:

1. Select approximately 300 Accounts / 550 Contacts / 300 Opportunities with defect
   coverage and enough parent/child closure; record anything excluded.
2. Map standard picklist values using the org descriptions. Do not silently discard
   rejected rows. Stage-derived closed/won flags are read-only in Salesforce.
3. Bulk upsert Accounts by `External_Source_Id__c`.
4. Query external-ID-to-Salesforce-ID mappings scoped to synthetic batches.
5. Set valid parent relationships; quarantine self-links, cycles and rejected links.
6. Resolve child Account associations; bulk upsert Contacts, then Opportunities.
7. Verify counts, bulk job results and failed rows, not merely job submission status.
8. Export each object with Bulk API 2.0 into a new timestamped snapshot.

No import command is exposed until those checks are implemented. Salesforce DQ field
pushback and the top 100-200 active issue upserts follow a functioning DQ run.

## 5. Duplicate Management (manual learning step)

After dirty records load:

- Inspect standard matching rules in Setup > Duplicate Management > Matching Rules.
- Create a custom Account rule exploring fuzzy Name with Website/domain and Phone.
- Create a Contact matching rule exploring exact Email and name/Account evidence.
- Create corresponding duplicate rules using **Allow + Alert**, and reporting where
  available. Activate matching rules before their duplicate rules.
- Manually create one duplicate Account and one duplicate Contact, inspect alerts,
  and capture screenshots without credentials.
- Inspect Potential Duplicates if available. Compare the evidence with the local
  engine. Do not depend on Duplicate Jobs or automatically merge records.

## 6. Activate prevention after the baseline

Inspect the shipped formulas, then activate through a reviewed metadata change or
Setup. Rules cover Enterprise Website, Contact Account and open past-due Close Date.
Salesforce validation runs on updates as well as creates; a score-only update may
fail on a dirty record. Plan the activation order around baseline and remediation.
Do not add an undisclosed bypass solely to make a bulk job appear successful.

## 7. Reports and dashboard (manual learning step)

Build reports for Account Data Quality, High-Priority DQ Issues, Pipeline at Risk,
Segmentation Coverage and Enrichment Coverage through the Report Builder. Create
the **GTM Data Quality Command Center** dashboard after real scores exist.
Keep enterprise pipeline exposure separate from summed issue-level exposure.
Power BI Desktop will read validated PostgreSQL analytics views in milestone 4.

## References

- [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli)
- [Official CLI data plugin commands](https://github.com/salesforcecli/plugin-data)
- [OpportunityStage object reference](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_opportunitystage.htm)
- [Metadata API reference](https://resources.docs.salesforce.com/latest/latest/en-us/sfdc/pdf/api_meta.pdf)
