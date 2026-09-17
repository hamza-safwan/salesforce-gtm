# Dependency status

Python runtime and development versions are recorded in `requirements.lock` and
applied through `requirements.txt`. The initial environment is Windows x64, Python
3.11.5. `pip check` checks dependency compatibility; it is not a vulnerability scan.
Linux installation has not yet been exercised. PostgreSQL uses the maintained
`postgres:16` major tag; record its actual image digest once Docker can pull it.

The project-local official Salesforce CLI is pinned at **2.150.6** with a committed
`package-lock.json`. It is an operational CLI dependency, not an application web
server. The installation reported **57 transitive advisories: 41 moderate and 16
high**. These are unresolved and have not been individually triaged. No clean
security audit is claimed. Do not force-upgrade its internal dependencies without
checking that Salesforce commands still work.

Next dependency-maintenance task:

```powershell
npm.cmd audit
```

Identify reachable advisories and fixes supported by the Salesforce CLI release,
update the lockfile with a reviewed change, then repeat version, metadata conversion,
org describe and deployment checks. No credentials belong in an audit artifact.
