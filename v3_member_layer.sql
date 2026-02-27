BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> baseline_v2_full_schema

CREATE EXTENSION IF NOT EXISTS pgcrypto;;

CREATE TYPE casestatus AS ENUM ('intake_submitted', 'intake_incomplete', 'under_review', 'in_progress', 'program_completed_positive_outcome', 'case_closed_other_outcome', 'auction_intake');

CREATE TYPE documenttype AS ENUM ('id_verification', 'income_verification', 'lease_or_mortgage', 'foreclosure_notice', 'eviction_notice', 'signed_consent', 'taskcheck_evidence', 'training_proof', 'system_doc', 'other');

CREATE TYPE referralstatus AS ENUM ('draft', 'queued', 'sent', 'failed', 'cancelled');

CREATE TYPE userrole AS ENUM ('case_worker', 'referral_coordinator', 'admin', 'audit_steward', 'ai_policy_chair', 'partner_org');

CREATE TYPE workflowoverridecategory AS ENUM ('data_correction', 'legal_exception', 'executive_directive', 'system_recovery');

CREATE TYPE workflowresponsiblerole AS ENUM ('operator', 'occupant', 'system', 'lender');

CREATE TYPE workflowstepstatus AS ENUM ('pending', 'active', 'blocked', 'complete');

CREATE TABLE ai_activity_logs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID, 
    policy_version_id UUID, 
    ai_role VARCHAR, 
    model_provider VARCHAR, 
    model_name VARCHAR, 
    model_version VARCHAR, 
    prompt_hash VARCHAR, 
    policy_rule_id VARCHAR, 
    confidence_score NUMERIC(5, 4), 
    human_override BOOLEAN DEFAULT false, 
    incident_type VARCHAR, 
    admin_review_required BOOLEAN DEFAULT false, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_ai_activity_logs PRIMARY KEY (id)
);

CREATE TABLE auction_imports (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    filename VARCHAR NOT NULL, 
    content_type VARCHAR, 
    file_bytes BYTEA NOT NULL, 
    file_type VARCHAR, 
    file_hash VARCHAR, 
    status VARCHAR DEFAULT 'received' NOT NULL, 
    records_created INTEGER DEFAULT 0 NOT NULL, 
    error_message VARCHAR, 
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_auction_imports PRIMARY KEY (id)
);

CREATE TABLE bot_commands (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    target_bot VARCHAR NOT NULL, 
    command VARCHAR NOT NULL, 
    args_json JSONB, 
    priority INTEGER DEFAULT 10 NOT NULL, 
    status VARCHAR, 
    notes VARCHAR, 
    CONSTRAINT pk_bot_commands PRIMARY KEY (id)
);

CREATE TABLE bot_inbound_logs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    source_bot VARCHAR NOT NULL, 
    payload_hash VARCHAR, 
    type VARCHAR, 
    status VARCHAR, 
    notes VARCHAR, 
    raw_json JSONB, 
    CONSTRAINT pk_bot_inbound_logs PRIMARY KEY (id)
);

CREATE TABLE bot_pages (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    url VARCHAR NOT NULL, 
    status VARCHAR, 
    last_crawl TIMESTAMP WITH TIME ZONE, 
    title VARCHAR, 
    notes VARCHAR, 
    CONSTRAINT pk_bot_pages PRIMARY KEY (id)
);

CREATE TABLE bot_reports (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    bot VARCHAR NOT NULL, 
    level VARCHAR NOT NULL, 
    code VARCHAR, 
    message VARCHAR NOT NULL, 
    details_json JSONB, 
    CONSTRAINT pk_bot_reports PRIMARY KEY (id)
);

CREATE TABLE bot_settings (
    key VARCHAR NOT NULL, 
    value VARCHAR NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_bot_settings PRIMARY KEY (key)
);

CREATE TABLE bot_triggers (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    enabled BOOLEAN DEFAULT true NOT NULL, 
    metric VARCHAR NOT NULL, 
    operator VARCHAR DEFAULT '>=' NOT NULL, 
    threshold FLOAT DEFAULT 0 NOT NULL, 
    priority INTEGER DEFAULT 10 NOT NULL, 
    target_bot VARCHAR NOT NULL, 
    command VARCHAR NOT NULL, 
    args_json JSONB, 
    CONSTRAINT pk_bot_triggers PRIMARY KEY (id)
);

CREATE TABLE certifications (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID, 
    cert_key VARCHAR NOT NULL, 
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    expires_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_certifications PRIMARY KEY (id)
);

CREATE TABLE ingestion_metrics (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    metric_type VARCHAR NOT NULL, 
    source VARCHAR, 
    file_hash VARCHAR, 
    file_name VARCHAR, 
    count_value INTEGER, 
    duration_seconds FLOAT, 
    notes VARCHAR, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_ingestion_metrics PRIMARY KEY (id)
);

CREATE TABLE leads (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    lead_id VARCHAR NOT NULL, 
    source VARCHAR, 
    address VARCHAR NOT NULL, 
    city VARCHAR, 
    state VARCHAR, 
    zip VARCHAR, 
    apn VARCHAR, 
    county VARCHAR, 
    trustee VARCHAR, 
    mortgagor VARCHAR, 
    mortgagee VARCHAR, 
    auction_date TIMESTAMP WITH TIME ZONE, 
    case_number VARCHAR, 
    opening_bid FLOAT, 
    list_price FLOAT, 
    arrears FLOAT, 
    equity_pct FLOAT, 
    arv FLOAT, 
    mao FLOAT, 
    spread_pct FLOAT, 
    tier VARCHAR, 
    south_dallas_override BOOLEAN DEFAULT false NOT NULL, 
    exit_strategy VARCHAR, 
    status VARCHAR, 
    score FLOAT, 
    notes VARCHAR, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_leads PRIMARY KEY (id)
);

CREATE TABLE outbox_queue (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    event_type VARCHAR, 
    case_id UUID, 
    payload JSONB, 
    dedupe_key VARCHAR, 
    attempts INTEGER DEFAULT 0, 
    max_attempts INTEGER DEFAULT 3, 
    processed_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_outbox_queue PRIMARY KEY (id)
);

CREATE TABLE partners (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    name VARCHAR NOT NULL, 
    contact_email VARCHAR, 
    CONSTRAINT pk_partners PRIMARY KEY (id)
);

CREATE TABLE policy_versions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    program_key VARCHAR NOT NULL, 
    version_tag VARCHAR NOT NULL, 
    is_active BOOLEAN DEFAULT true, 
    config_json JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_policy_versions PRIMARY KEY (id)
);

CREATE TABLE properties (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    external_id VARCHAR NOT NULL, 
    address VARCHAR NOT NULL, 
    city VARCHAR NOT NULL, 
    state VARCHAR NOT NULL, 
    zip VARCHAR NOT NULL, 
    county VARCHAR, 
    property_type VARCHAR, 
    year_built INTEGER, 
    sqft INTEGER, 
    beds FLOAT, 
    baths FLOAT, 
    assessed_value INTEGER, 
    mortgagor VARCHAR, 
    mortgagee VARCHAR, 
    trustee VARCHAR, 
    loan_type VARCHAR, 
    interest_rate FLOAT, 
    orig_loan_amount INTEGER, 
    est_balance INTEGER, 
    auction_date TIMESTAMP WITH TIME ZONE, 
    auction_time VARCHAR, 
    source VARCHAR, 
    latitude FLOAT, 
    longitude FLOAT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_properties PRIMARY KEY (id)
);

CREATE TABLE training_quiz_attempts (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID, 
    lesson_key VARCHAR NOT NULL, 
    answers JSONB, 
    passed BOOLEAN DEFAULT false, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_training_quiz_attempts PRIMARY KEY (id)
);

CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    email VARCHAR NOT NULL, 
    hashed_password VARCHAR NOT NULL, 
    role userrole, 
    full_name VARCHAR, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_users PRIMARY KEY (id)
);

CREATE TABLE workflow_templates (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    program_key VARCHAR NOT NULL, 
    name VARCHAR NOT NULL, 
    template_version INTEGER DEFAULT 1 NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_workflow_templates PRIMARY KEY (id)
);

CREATE TABLE cert_revocations (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    certification_id UUID, 
    reason_code VARCHAR NOT NULL, 
    revoked_by_system BOOLEAN DEFAULT true, 
    revoked_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_cert_revocations PRIMARY KEY (id)
);

CREATE TABLE cases (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    status casestatus NOT NULL, 
    created_by UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    program_type VARCHAR, 
    program_key VARCHAR, 
    meta JSONB, 
    case_type VARCHAR, 
    policy_version_id UUID, 
    property_id UUID, 
    auction_date TIMESTAMP WITH TIME ZONE, 
    canonical_key VARCHAR, 
    CONSTRAINT pk_cases PRIMARY KEY (id)
);

CREATE TABLE workflow_steps (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    template_id UUID NOT NULL, 
    step_key VARCHAR NOT NULL, 
    display_name VARCHAR NOT NULL, 
    responsible_role workflowresponsiblerole NOT NULL, 
    required_documents JSONB DEFAULT '[]'::jsonb NOT NULL, 
    required_actions JSONB DEFAULT '[]'::jsonb NOT NULL, 
    blocking_conditions JSONB DEFAULT '[]'::jsonb NOT NULL, 
    kanban_column VARCHAR NOT NULL, 
    order_index INTEGER NOT NULL, 
    auto_advance BOOLEAN DEFAULT false NOT NULL, 
    sla_days INTEGER DEFAULT 30 NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_workflow_steps PRIMARY KEY (id)
);

CREATE TABLE ai_scores (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID NOT NULL, 
    equity NUMERIC(12, 2) NOT NULL, 
    strategy VARCHAR NOT NULL, 
    confidence NUMERIC(4, 2) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_ai_scores PRIMARY KEY (id)
);

CREATE TABLE audit_logs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID, 
    actor_id UUID, 
    actor_is_ai BOOLEAN DEFAULT false, 
    action_type VARCHAR NOT NULL, 
    reason_code VARCHAR NOT NULL, 
    before_state JSONB, 
    after_state JSONB, 
    policy_version_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_audit_logs PRIMARY KEY (id)
);

CREATE TABLE case_workflow_instances (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID NOT NULL, 
    template_id UUID NOT NULL, 
    locked_template_version INTEGER DEFAULT 1 NOT NULL, 
    current_step_key VARCHAR NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    completed_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_case_workflow_instances PRIMARY KEY (id)
);

CREATE TABLE consent_records (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID, 
    granted_by_user_id UUID, 
    scope JSONB NOT NULL, 
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    valid_until TIMESTAMP WITH TIME ZONE, 
    revoked BOOLEAN DEFAULT false, 
    CONSTRAINT pk_consent_records PRIMARY KEY (id)
);

CREATE TABLE deal_scores (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    property_id UUID NOT NULL, 
    case_id UUID NOT NULL, 
    score INTEGER NOT NULL, 
    tier VARCHAR NOT NULL, 
    exit_strategy VARCHAR NOT NULL, 
    urgency_days INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_deal_scores PRIMARY KEY (id)
);

CREATE TABLE documents (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID NOT NULL, 
    uploaded_by UUID NOT NULL, 
    doc_type documenttype NOT NULL, 
    meta JSONB, 
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    file_url VARCHAR, 
    CONSTRAINT pk_documents PRIMARY KEY (id)
);

CREATE TABLE referrals (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID NOT NULL, 
    partner_id UUID NOT NULL, 
    status referralstatus DEFAULT 'draft' NOT NULL, 
    payload JSONB, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_referrals PRIMARY KEY (id)
);

CREATE TABLE role_sessions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    role_name VARCHAR NOT NULL, 
    scope_case_id UUID, 
    scope_program_key VARCHAR, 
    assumed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_role_sessions PRIMARY KEY (id)
);

CREATE TABLE taskchecks (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID, 
    skill_key VARCHAR NOT NULL, 
    passed BOOLEAN DEFAULT false, 
    evidence JSONB, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_taskchecks PRIMARY KEY (id)
);

CREATE TABLE case_workflow_progress (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    instance_id UUID NOT NULL, 
    step_key VARCHAR NOT NULL, 
    status workflowstepstatus DEFAULT 'pending' NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    block_reason VARCHAR, 
    CONSTRAINT pk_case_workflow_progress PRIMARY KEY (id)
);

CREATE TABLE workflow_overrides (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    case_id UUID NOT NULL, 
    instance_id UUID NOT NULL, 
    from_step_key VARCHAR NOT NULL, 
    to_step_key VARCHAR NOT NULL, 
    reason_category workflowoverridecategory NOT NULL, 
    reason VARCHAR NOT NULL, 
    actor_id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    CONSTRAINT pk_workflow_overrides PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_auction_imports_file_hash ON auction_imports (file_hash);

CREATE INDEX ix_bot_commands_created_at ON bot_commands (created_at);

CREATE INDEX ix_bot_inbound_logs_created_at ON bot_inbound_logs (created_at);

CREATE INDEX ix_bot_reports_created_at ON bot_reports (created_at);

CREATE INDEX ix_ingestion_metrics_metric_type ON ingestion_metrics (metric_type);

CREATE UNIQUE INDEX ix_properties_external_id ON properties (external_id);

CREATE INDEX ix_workflow_templates_program_key ON workflow_templates (program_key);

CREATE UNIQUE INDEX ix_cases_canonical_key ON cases (canonical_key);

CREATE INDEX ix_workflow_steps_template_id ON workflow_steps (template_id);

CREATE UNIQUE INDEX ix_case_workflow_instances_case_id ON case_workflow_instances (case_id);

CREATE INDEX ix_case_workflow_instances_template_id ON case_workflow_instances (template_id);

CREATE INDEX ix_workflow_overrides_case_id ON workflow_overrides (case_id);

CREATE INDEX ix_workflow_overrides_instance_id ON workflow_overrides (instance_id);

CREATE INDEX ix_case_workflow_progress_instance_id ON case_workflow_progress (instance_id);

ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);

ALTER TABLE leads ADD CONSTRAINT uq_leads_lead_id UNIQUE (lead_id);

ALTER TABLE outbox_queue ADD CONSTRAINT uq_outbox_queue_dedupe_key UNIQUE (dedupe_key);

ALTER TABLE cases ADD CONSTRAINT uq_cases_property_id_auction_date UNIQUE (property_id, auction_date);

ALTER TABLE certifications ADD CONSTRAINT fk_certifications_user_id_users FOREIGN KEY(user_id) REFERENCES users (id);

ALTER TABLE cert_revocations ADD CONSTRAINT fk_cert_revocations_certification_id_certifications FOREIGN KEY(certification_id) REFERENCES certifications (id);

ALTER TABLE cases ADD CONSTRAINT fk_cases_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE cases ADD CONSTRAINT fk_cases_policy_version_id_policy_versions FOREIGN KEY(policy_version_id) REFERENCES policy_versions (id);

ALTER TABLE cases ADD CONSTRAINT fk_cases_property_id_properties FOREIGN KEY(property_id) REFERENCES properties (id);

ALTER TABLE workflow_steps ADD CONSTRAINT fk_workflow_steps_template_id_workflow_templates FOREIGN KEY(template_id) REFERENCES workflow_templates (id);

ALTER TABLE ai_scores ADD CONSTRAINT fk_ai_scores_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE ai_activity_logs ADD CONSTRAINT fk_ai_activity_logs_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE ai_activity_logs ADD CONSTRAINT fk_ai_activity_logs_policy_version_id_policy_versions FOREIGN KEY(policy_version_id) REFERENCES policy_versions (id);

ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_policy_version_id_policy_versions FOREIGN KEY(policy_version_id) REFERENCES policy_versions (id);

ALTER TABLE case_workflow_instances ADD CONSTRAINT fk_case_workflow_instances_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE case_workflow_instances ADD CONSTRAINT fk_case_workflow_instances_template_id_workflow_templates FOREIGN KEY(template_id) REFERENCES workflow_templates (id);

ALTER TABLE consent_records ADD CONSTRAINT fk_consent_records_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE deal_scores ADD CONSTRAINT fk_deal_scores_property_id_properties FOREIGN KEY(property_id) REFERENCES properties (id);

ALTER TABLE deal_scores ADD CONSTRAINT fk_deal_scores_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE documents ADD CONSTRAINT fk_documents_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE documents ADD CONSTRAINT fk_documents_uploaded_by_users FOREIGN KEY(uploaded_by) REFERENCES users (id);

ALTER TABLE referrals ADD CONSTRAINT fk_referrals_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE referrals ADD CONSTRAINT fk_referrals_partner_id_partners FOREIGN KEY(partner_id) REFERENCES partners (id);

ALTER TABLE role_sessions ADD CONSTRAINT fk_role_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id);

ALTER TABLE role_sessions ADD CONSTRAINT fk_role_sessions_scope_case_id_cases FOREIGN KEY(scope_case_id) REFERENCES cases (id);

ALTER TABLE taskchecks ADD CONSTRAINT fk_taskchecks_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE training_quiz_attempts ADD CONSTRAINT fk_training_quiz_attempts_user_id_users FOREIGN KEY(user_id) REFERENCES users (id);

ALTER TABLE outbox_queue ADD CONSTRAINT fk_outbox_queue_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE case_workflow_progress ADD CONSTRAINT fk_case_workflow_progress_instance_id_case_workflow_instances FOREIGN KEY(instance_id) REFERENCES case_workflow_instances (id);

ALTER TABLE workflow_overrides ADD CONSTRAINT fk_workflow_overrides_case_id_cases FOREIGN KEY(case_id) REFERENCES cases (id);

ALTER TABLE workflow_overrides ADD CONSTRAINT fk_workflow_overrides_instance_id_case_workflow_instances FOREIGN KEY(instance_id) REFERENCES case_workflow_instances (id);

CREATE OR REPLACE FUNCTION enforce_workflow_override_limit()
        RETURNS trigger AS $$
        DECLARE
            override_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO override_count
            FROM workflow_overrides
            WHERE case_id = NEW.case_id;

            IF override_count >= 3 THEN
                RAISE EXCEPTION
                'workflow override limit exceeded for case_id=%',
                NEW.case_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;;

CREATE OR REPLACE FUNCTION prevent_documents_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
            'documents are immutable; operation=% is not allowed',
            TG_OP;
        END;
        $$ LANGUAGE plpgsql;;

CREATE OR REPLACE FUNCTION prevent_audit_logs_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
            'audit_logs are immutable; operation=% is not allowed',
            TG_OP;
        END;
        $$ LANGUAGE plpgsql;;

CREATE TRIGGER trg_enforce_workflow_override_limit
        BEFORE INSERT ON workflow_overrides
        FOR EACH ROW
        EXECUTE FUNCTION enforce_workflow_override_limit();;

CREATE TRIGGER trg_prevent_documents_update
        BEFORE UPDATE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION prevent_documents_mutation();;

CREATE TRIGGER trg_prevent_documents_delete
        BEFORE DELETE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION prevent_documents_mutation();;

CREATE TRIGGER trg_prevent_audit_logs_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_logs_mutation();;

CREATE TRIGGER trg_prevent_audit_logs_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_logs_mutation();;

INSERT INTO alembic_version (version_num) VALUES ('baseline_v2_full_schema') RETURNING alembic_version.version_num;

-- Running upgrade baseline_v2_full_schema -> v3_member_layer

CREATE TYPE applicationstatus AS ENUM ('started', 'submitted', 'needs_info', 'qualified', 'not_qualified');

CREATE TYPE membershipstatus AS ENUM ('active', 'paused', 'expired', 'cancelled');

CREATE TYPE installmentstatus AS ENUM ('due', 'paid_cash', 'satisfied_contribution', 'missed', 'waived');

CREATE TYPE credit_type AS ENUM ('testimonial_video', 'referral', 'volunteer', 'training_module', 'other');

CREATE TYPE checkintype AS ENUM ('hardship_notice', 'monthly_update', 'support_request');

CREATE TABLE applications (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    email TEXT NOT NULL, 
    full_name TEXT, 
    phone TEXT, 
    program_key TEXT NOT NULL, 
    status applicationstatus DEFAULT 'started' NOT NULL, 
    answers_json JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    submitted_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_applications PRIMARY KEY (id)
);

CREATE TABLE memberships (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    program_key TEXT NOT NULL, 
    term_start DATE NOT NULL, 
    term_end DATE NOT NULL, 
    annual_price_cents INTEGER NOT NULL, 
    installment_cents INTEGER NOT NULL, 
    status membershipstatus DEFAULT 'active' NOT NULL, 
    good_standing BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_memberships PRIMARY KEY (id)
);

CREATE TABLE membership_installments (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    membership_id UUID NOT NULL, 
    due_date DATE NOT NULL, 
    amount_cents INTEGER NOT NULL, 
    status installmentstatus DEFAULT 'due' NOT NULL, 
    paid_at TIMESTAMP WITH TIME ZONE, 
    notes TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_membership_installments PRIMARY KEY (id)
);

CREATE TABLE contribution_credits (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    membership_id UUID NOT NULL, 
    installment_id UUID, 
    credit_type credit_type NOT NULL, 
    amount_cents_equivalent INTEGER NOT NULL, 
    evidence_document_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_contribution_credits PRIMARY KEY (id)
);

CREATE TABLE member_checkins (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    membership_id UUID NOT NULL, 
    type checkintype NOT NULL, 
    notes TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_member_checkins PRIMARY KEY (id)
);

CREATE TABLE stability_assessments (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    user_id UUID NOT NULL, 
    property_id UUID, 
    program_key TEXT NOT NULL, 
    equity_estimate NUMERIC(12, 2), 
    equity_health_band TEXT, 
    stability_score INTEGER NOT NULL, 
    risk_level TEXT, 
    breakdown_json JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_stability_assessments PRIMARY KEY (id)
);

CREATE INDEX ix_applications_program_key ON applications (program_key);

CREATE INDEX ix_applications_status ON applications (status);

CREATE INDEX ix_memberships_user_id ON memberships (user_id);

CREATE INDEX ix_memberships_program_key ON memberships (program_key);

CREATE INDEX ix_membership_installments_membership_id ON membership_installments (membership_id);

CREATE INDEX ix_membership_installments_due_date ON membership_installments (due_date);

CREATE INDEX ix_contribution_credits_membership_id ON contribution_credits (membership_id);

CREATE INDEX ix_contribution_credits_installment_id ON contribution_credits (installment_id);

CREATE INDEX ix_member_checkins_membership_id ON member_checkins (membership_id);

CREATE INDEX ix_stability_assessments_user_id ON stability_assessments (user_id);

CREATE INDEX ix_stability_assessments_program_key ON stability_assessments (program_key);

CREATE INDEX ix_stability_assessments_created_at ON stability_assessments (created_at);

CREATE UNIQUE INDEX uq_memberships_active_user_program ON memberships (user_id, program_key) WHERE status = 'active';

ALTER TABLE memberships ADD CONSTRAINT fk_memberships_user_id_users FOREIGN KEY(user_id) REFERENCES users (id);

ALTER TABLE membership_installments ADD CONSTRAINT fk_membership_installments_membership_id_memberships FOREIGN KEY(membership_id) REFERENCES memberships (id);

ALTER TABLE contribution_credits ADD CONSTRAINT fk_contribution_credits_membership_id_memberships FOREIGN KEY(membership_id) REFERENCES memberships (id);

ALTER TABLE contribution_credits ADD CONSTRAINT fk_contribution_credits_installment_id_membership_installments FOREIGN KEY(installment_id) REFERENCES membership_installments (id);

ALTER TABLE contribution_credits ADD CONSTRAINT fk_contribution_credits_evidence_document_id_documents FOREIGN KEY(evidence_document_id) REFERENCES documents (id);

ALTER TABLE member_checkins ADD CONSTRAINT fk_member_checkins_membership_id_memberships FOREIGN KEY(membership_id) REFERENCES memberships (id);

ALTER TABLE stability_assessments ADD CONSTRAINT fk_stability_assessments_user_id_users FOREIGN KEY(user_id) REFERENCES users (id);

ALTER TABLE stability_assessments ADD CONSTRAINT fk_stability_assessments_property_id_properties FOREIGN KEY(property_id) REFERENCES properties (id);

CREATE VIEW active_stable_members AS
        WITH latest_stability AS (
            SELECT DISTINCT ON (sa.user_id, sa.program_key)
                sa.user_id,
                sa.program_key,
                sa.stability_score,
                sa.created_at AS stability_created_at
            FROM stability_assessments sa
            ORDER BY sa.user_id, sa.program_key, sa.created_at DESC
        )
        SELECT
            m.id AS membership_id,
            m.user_id,
            m.program_key,
            ls.stability_score,
            GREATEST(
                COALESCE(mi.last_paid_cash_at, to_timestamp(0)),
                COALESCE(cc.last_contribution_at, to_timestamp(0)),
                COALESCE(d.last_document_at, to_timestamp(0)),
                COALESCE(mc.last_checkin_at, to_timestamp(0)),
                COALESCE(tqa.last_training_at, to_timestamp(0))
            ) AS last_activity_at
        FROM memberships m
        JOIN latest_stability ls
            ON ls.user_id = m.user_id
           AND ls.program_key = m.program_key
        LEFT JOIN (
            SELECT membership_id, MAX(paid_at) AS last_paid_cash_at
            FROM membership_installments
            WHERE status = 'paid_cash'
            GROUP BY membership_id
        ) mi ON mi.membership_id = m.id
        LEFT JOIN (
            SELECT membership_id, MAX(created_at) AS last_contribution_at
            FROM contribution_credits
            GROUP BY membership_id
        ) cc ON cc.membership_id = m.id
        LEFT JOIN (
            SELECT c.created_by AS user_id, c.program_key, MAX(d.uploaded_at) AS last_document_at
            FROM documents d
            JOIN cases c ON c.id = d.case_id
            GROUP BY c.created_by, c.program_key
        ) d ON d.user_id = m.user_id AND d.program_key = m.program_key
        LEFT JOIN (
            SELECT membership_id, MAX(created_at) AS last_checkin_at
            FROM member_checkins
            GROUP BY membership_id
        ) mc ON mc.membership_id = m.id
        LEFT JOIN (
            SELECT user_id, MAX(created_at) AS last_training_at
            FROM training_quiz_attempts
            GROUP BY user_id
        ) tqa ON tqa.user_id = m.user_id
        WHERE m.status = 'active'
          AND m.good_standing = true
          AND ls.stability_score >= 65
          AND GREATEST(
                COALESCE(mi.last_paid_cash_at, to_timestamp(0)),
                COALESCE(cc.last_contribution_at, to_timestamp(0)),
                COALESCE(d.last_document_at, to_timestamp(0)),
                COALESCE(mc.last_checkin_at, to_timestamp(0)),
                COALESCE(tqa.last_training_at, to_timestamp(0))
          ) >= now() - interval '30 days';;

INSERT INTO workflow_templates (id, program_key, name, template_version, created_at)
        SELECT gen_random_uuid(), 'homeowner_protection', 'Homeowner Protection Program', 1, now()
        WHERE NOT EXISTS (
            SELECT 1
            FROM workflow_templates
            WHERE program_key = 'homeowner_protection' AND template_version = 1
        );;

INSERT INTO workflow_steps (
            id,
            template_id,
            step_key,
            display_name,
            responsible_role,
            required_documents,
            required_actions,
            blocking_conditions,
            kanban_column,
            order_index,
            auto_advance,
            sla_days,
            created_at
        )
        SELECT
            gen_random_uuid(),
            wt.id,
            s.step_key,
            s.display_name,
            s.responsible_role::workflowresponsiblerole,
            '[]'::jsonb,
            '[]'::jsonb,
            '[]'::jsonb,
            s.kanban_column,
            s.order_index,
            false,
            30,
            now()
        FROM workflow_templates wt
        JOIN (
            VALUES
                ('qualification_submitted', 'Qualification Submitted', 'operator', 'intake', 1),
                ('identity_verified', 'Identity Verified', 'operator', 'verification', 2),
                ('property_snapshot', 'Property Snapshot', 'operator', 'analysis', 3),
                ('baseline_stability_generated', 'Baseline Stability Generated', 'system', 'analysis', 4),
                ('plan_activated', 'Plan Activated', 'operator', 'activation', 5),
                ('monthly_checkin_cycle', 'Monthly Check-in Cycle', 'occupant', 'monitoring', 6)
        ) AS s(step_key, display_name, responsible_role, kanban_column, order_index)
            ON true
        WHERE wt.program_key = 'homeowner_protection'
          AND wt.template_version = 1
          AND NOT EXISTS (
              SELECT 1
              FROM workflow_steps ws
              WHERE ws.template_id = wt.id
                AND ws.step_key = s.step_key
          );;

UPDATE alembic_version SET version_num='v3_member_layer' WHERE alembic_version.version_num = 'baseline_v2_full_schema';

COMMIT;

