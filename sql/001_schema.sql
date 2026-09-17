-- Preserve raw quality defects. Relationship constraints belong in detection,
-- not in raw ingestion, where they would discard the evidence under investigation.
CREATE SCHEMA raw;
CREATE SCHEMA dq;
CREATE SCHEMA analytics;

CREATE TABLE raw.snapshot (
    snapshot_run_id UUID PRIMARY KEY,
    snapshot_at TIMESTAMPTZ NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('synthetic_local', 'salesforce')),
    as_of_date DATE NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    record_count INTEGER NOT NULL CHECK (record_count >= 0),
    UNIQUE (source_kind, manifest_sha256)
);

CREATE TABLE raw.salesforce_account (
    snapshot_run_id UUID NOT NULL REFERENCES raw.snapshot,
    snapshot_at TIMESTAMPTZ NOT NULL,
    id TEXT,
    external_source_id TEXT NOT NULL,
    name TEXT, website TEXT, canonical_domain TEXT, phone TEXT,
    billing_street TEXT, billing_city TEXT, billing_state TEXT,
    billing_postal_code TEXT, billing_country TEXT, industry TEXT,
    number_of_employees INTEGER, annual_revenue NUMERIC(18,2), type TEXT,
    parent_id TEXT, parent_external_id TEXT,
    corporate_family_id TEXT, is_subsidiary BOOLEAN,
    source_system TEXT, ingestion_batch_id TEXT, region TEXT, segment TEXT,
    icp_tier TEXT, enrichment_source TEXT, last_enriched_date DATE,
    dq_score NUMERIC(5,2), dq_status TEXT, dq_issue_count INTEGER,
    created_date TIMESTAMPTZ, last_modified_date TIMESTAMPTZ,
    source_payload JSONB NOT NULL,
    PRIMARY KEY (snapshot_run_id, external_source_id),
    UNIQUE (snapshot_run_id, id)
);
CREATE INDEX account_id_idx ON raw.salesforce_account(id);
CREATE INDEX account_external_idx ON raw.salesforce_account(external_source_id);
CREATE INDEX account_parent_idx ON raw.salesforce_account(snapshot_run_id, parent_id);
CREATE INDEX account_domain_idx ON raw.salesforce_account(snapshot_run_id, canonical_domain);

CREATE TABLE raw.salesforce_contact (
    snapshot_run_id UUID NOT NULL REFERENCES raw.snapshot,
    snapshot_at TIMESTAMPTZ NOT NULL,
    id TEXT, external_source_id TEXT NOT NULL,
    account_id TEXT, account_external_id TEXT,
    first_name TEXT, last_name TEXT, email TEXT, phone TEXT, mobile_phone TEXT,
    title TEXT, department TEXT, mailing_country TEXT, seniority TEXT,
    contact_status TEXT, last_enriched_date DATE,
    source_system TEXT, ingestion_batch_id TEXT,
    dq_score NUMERIC(5,2), dq_status TEXT, dq_issue_count INTEGER,
    created_date TIMESTAMPTZ, last_modified_date TIMESTAMPTZ,
    source_payload JSONB NOT NULL,
    PRIMARY KEY (snapshot_run_id, external_source_id),
    UNIQUE (snapshot_run_id, id)
);
CREATE INDEX contact_id_idx ON raw.salesforce_contact(id);
CREATE INDEX contact_external_idx ON raw.salesforce_contact(external_source_id);
CREATE INDEX contact_account_idx ON raw.salesforce_contact(snapshot_run_id, account_id);
CREATE INDEX contact_email_idx ON raw.salesforce_contact(snapshot_run_id, lower(trim(email)));

CREATE TABLE raw.salesforce_opportunity (
    snapshot_run_id UUID NOT NULL REFERENCES raw.snapshot,
    snapshot_at TIMESTAMPTZ NOT NULL,
    id TEXT, external_source_id TEXT NOT NULL,
    name TEXT, account_id TEXT, account_external_id TEXT,
    stage_name TEXT, amount NUMERIC(18,2), close_date DATE, lead_source TEXT,
    probability NUMERIC(5,2), is_closed BOOLEAN, is_won BOOLEAN,
    source_system TEXT, ingestion_batch_id TEXT, region TEXT, sales_segment TEXT,
    dq_score NUMERIC(5,2), dq_status TEXT, dq_issue_count INTEGER,
    created_date TIMESTAMPTZ, last_modified_date TIMESTAMPTZ,
    source_payload JSONB NOT NULL,
    PRIMARY KEY (snapshot_run_id, external_source_id),
    UNIQUE (snapshot_run_id, id)
);
CREATE INDEX opportunity_id_idx ON raw.salesforce_opportunity(id);
CREATE INDEX opportunity_external_idx ON raw.salesforce_opportunity(external_source_id);
CREATE INDEX opportunity_account_idx ON raw.salesforce_opportunity(snapshot_run_id, account_id);

CREATE TABLE raw.enrichment_feed (
    snapshot_run_id UUID NOT NULL REFERENCES raw.snapshot,
    snapshot_at TIMESTAMPTZ NOT NULL,
    external_account_id TEXT NOT NULL,
    website TEXT, industry TEXT, number_of_employees INTEGER,
    annual_revenue NUMERIC(18,2), billing_country TEXT, enriched_at DATE,
    vendor_name TEXT NOT NULL, vendor_confidence NUMERIC(5,4),
    source_payload JSONB NOT NULL,
    PRIMARY KEY (snapshot_run_id, external_account_id, vendor_name)
);

CREATE TABLE dq.run (
    run_id UUID PRIMARY KEY,
    snapshot_run_id UUID NOT NULL REFERENCES raw.snapshot,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    source_snapshot_at TIMESTAMPTZ NOT NULL,
    git_commit_sha TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    record_count INTEGER NOT NULL CHECK (record_count >= 0),
    config_snapshot JSONB NOT NULL,
    CHECK (status = 'running' OR completed_at IS NOT NULL)
);

CREATE TABLE dq.rule_catalog (
    rule_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    dimension TEXT NOT NULL CHECK (dimension IN
        ('Completeness', 'Validity', 'Consistency', 'Uniqueness', 'Hierarchy', 'Enrichment')),
    name TEXT NOT NULL, description TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('Critical', 'High', 'Medium', 'Low')),
    weight NUMERIC NOT NULL CHECK (weight > 0),
    recommended_action TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE dq.rule_result (
    run_id UUID NOT NULL REFERENCES dq.run,
    rule_id TEXT NOT NULL REFERENCES dq.rule_catalog,
    entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
    external_source_id TEXT NOT NULL,
    -- NULL means not applicable; never turn N/A into an artificial pass.
    passed BOOLEAN,
    observed_value TEXT, expected_value TEXT,
    details JSONB NOT NULL,
    dimension TEXT NOT NULL, severity TEXT NOT NULL,
    explanation TEXT NOT NULL, recommended_action TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (run_id, rule_id, entity_type, entity_id)
);
CREATE INDEX result_rule_idx ON dq.rule_result(rule_id, run_id);

CREATE TABLE dq.duplicate_candidate (
    run_id UUID NOT NULL REFERENCES dq.run,
    entity_type TEXT NOT NULL,
    left_entity_id TEXT NOT NULL, right_entity_id TEXT NOT NULL,
    matching_method TEXT NOT NULL,
    similarity_score NUMERIC NOT NULL CHECK (similarity_score BETWEEN 0 AND 1),
    confidence_band TEXT NOT NULL,
    reasons JSONB NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'Needs Human Review',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, entity_type, left_entity_id, right_entity_id),
    CHECK (left_entity_id < right_entity_id)
);

-- Workflow state persists across runs instead of being recreated every day.
CREATE TABLE dq.issue_review (
    issue_key TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'New' CHECK (status IN ('New', 'In Review', 'Resolved', 'Ignored')),
    review_note TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dq.remediation_queue (
    run_id UUID NOT NULL REFERENCES dq.run,
    issue_key TEXT NOT NULL,
    entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, external_source_id TEXT NOT NULL,
    rule_id TEXT NOT NULL REFERENCES dq.rule_catalog,
    dimension TEXT NOT NULL, severity TEXT NOT NULL,
    pipeline_at_risk NUMERIC(18,2) NOT NULL CHECK (pipeline_at_risk >= 0),
    segment_weight NUMERIC NOT NULL CHECK (segment_weight BETWEEN 0 AND 1),
    detection_confidence NUMERIC NOT NULL CHECK (detection_confidence BETWEEN 0 AND 1),
    priority_score NUMERIC(5,2) NOT NULL CHECK (priority_score BETWEEN 0 AND 100),
    recommended_action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'New',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, issue_key)
);
CREATE INDEX remediation_priority_idx ON dq.remediation_queue(run_id, priority_score DESC);
