-- Additive Correction Case Kernel schema (PostgreSQL only).
-- No legacy rows are rewritten by this migration.

ALTER TABLE entities
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'entities_revision_positive'
          AND conrelid = 'entities'::regclass
    ) THEN
        ALTER TABLE entities
            ADD CONSTRAINT entities_revision_positive CHECK (revision >= 1);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS cases (
    case_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_kind TEXT NOT NULL CHECK (service_kind IN ('correction', 'claim', 'account_recovery', 'safety_report')),
    category TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('intake', 'triage', 'investigation', 'decision', 'fulfillment', 'closed')),
    activity TEXT NOT NULL CHECK (activity IN ('active', 'waiting_on_requester', 'waiting_on_external')),
    disposition_family TEXT NOT NULL CHECK (disposition_family IN ('undetermined', 'action_taken', 'no_action', 'transferred', 'withdrawn', 'duplicate')),
    domain_outcome TEXT,
    severity TEXT,
    reporter_privacy TEXT NOT NULL,
    owner_ref TEXT NOT NULL,
    current_revision INTEGER NOT NULL DEFAULT 1 CHECK (current_revision >= 1),
    promise_policy_ref TEXT NOT NULL,
    review_of_case_id UUID REFERENCES cases(case_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    CONSTRAINT cases_closed_phase_order CHECK ((phase = 'closed') = (closed_at IS NOT NULL))
);
ALTER TABLE cases OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_interactions (
    interaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('web', 'phone', 'zalo_human', 'zalo_ai_handoff', 'email_transcribed')),
    actor_ref TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound', 'internal')),
    consent_ref TEXT,
    identity_assurance TEXT,
    payload_enc TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE case_interactions OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_party_authorities (
    party_authority_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    party_ref TEXT NOT NULL,
    authority_kind TEXT NOT NULL,
    scope TEXT NOT NULL,
    assurance_level TEXT NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT case_party_authorities_expiry_order CHECK (expires_at IS NULL OR expires_at > granted_at)
);
ALTER TABLE case_party_authorities OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_work_items (
    work_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    required_role TEXT NOT NULL,
    risk_class TEXT NOT NULL CHECK (risk_class IN ('R0', 'R1', 'R2', 'R3')),
    status TEXT NOT NULL CHECK (status IN ('ready', 'claimed', 'waiting', 'completed', 'cancelled')),
    assignee_ref TEXT,
    lease_expires_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    next_review_at TIMESTAMPTZ,
    priority SMALLINT NOT NULL DEFAULT 0,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    CONSTRAINT case_work_items_active_lease CHECK (status <> 'claimed' OR (assignee_ref IS NOT NULL AND lease_expires_at IS NOT NULL))
);
ALTER TABLE case_work_items OWNER TO vl360;
CREATE UNIQUE INDEX IF NOT EXISTS uq_case_work_items_active_lease
    ON case_work_items(case_id, kind)
    WHERE status = 'claimed';
CREATE INDEX IF NOT EXISTS idx_case_work_items_queue_priority
    ON case_work_items(priority DESC, ready_at, work_item_id)
    WHERE status = 'ready';

CREATE TABLE IF NOT EXISTS case_decisions (
    decision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    item_id UUID,
    outcome_code TEXT NOT NULL CHECK (outcome_code IN ('corrected', 'confirmed_current', 'insufficient_evidence', 'out_of_scope', 'duplicate_linked', 'unable_to_verify', 'withdrawn_by_requester')),
    reason_code TEXT NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    decision_maker_ref TEXT NOT NULL,
    reviewer_ref TEXT,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    policy_revision TEXT NOT NULL
);
ALTER TABLE case_decisions OWNER TO vl360;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'case_decisions_outcome_code_check' AND conrelid = 'case_decisions'::regclass) THEN
        ALTER TABLE case_decisions DROP CONSTRAINT case_decisions_outcome_code_check;
    END IF;
    ALTER TABLE case_decisions ADD CONSTRAINT case_decisions_outcome_code_check
        CHECK (outcome_code IN ('corrected', 'confirmed_current', 'insufficient_evidence', 'out_of_scope', 'duplicate_linked', 'unable_to_verify', 'withdrawn_by_requester'));
END $$;

CREATE TABLE IF NOT EXISTS case_promise_clocks (
    clock_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('receipt', 'triage', 'update', 'resolution')),
    started_at TIMESTAMPTZ NOT NULL,
    due_at TIMESTAMPTZ NOT NULL,
    health TEXT NOT NULL CHECK (health IN ('on_track', 'at_risk', 'breached', 'recovery')),
    policy_revision TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT case_promise_clocks_due_order CHECK (due_at >= started_at),
    CONSTRAINT case_promise_clocks_kind_unique UNIQUE (case_id, kind)
);
ALTER TABLE case_promise_clocks OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_case_promise_clocks_due
    ON case_promise_clocks(due_at, case_id)
    WHERE health IN ('at_risk', 'breached');

CREATE TABLE IF NOT EXISTS case_receipts (
    receipt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    public_reference TEXT NOT NULL UNIQUE,
    capability_digest TEXT NOT NULL UNIQUE,
    capability_key_version TEXT NOT NULL,
    receipt_revision INTEGER NOT NULL DEFAULT 1,
    subject_user_id TEXT,
    notification_consent_ref TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_receipts_capability_digest_shape CHECK (capability_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT case_receipts_receipt_revision_positive CHECK (receipt_revision >= 1),
    CONSTRAINT case_receipts_case_revision_unique UNIQUE (case_id, receipt_revision),
    CONSTRAINT case_receipts_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_receipts OWNER TO vl360;

-- Keep receipt identity bound to its case so child rows can use a composite FK.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'case_receipts_case_receipt_unique'
          AND conrelid = 'case_receipts'::regclass
    ) THEN
        ALTER TABLE case_receipts ADD CONSTRAINT case_receipts_case_receipt_unique UNIQUE (case_id, receipt_id);
    END IF;
END $$;

ALTER TABLE case_receipts ADD COLUMN IF NOT EXISTS receipt_revision INTEGER;
ALTER TABLE case_receipts ADD COLUMN IF NOT EXISTS subject_user_id TEXT;
WITH ranked AS (
    SELECT receipt_id, row_number() OVER (PARTITION BY case_id ORDER BY created_at, receipt_id) AS revision
    FROM case_receipts WHERE receipt_revision IS NULL
)
UPDATE case_receipts receipt SET receipt_revision = ranked.revision
FROM ranked WHERE receipt.receipt_id = ranked.receipt_id;
ALTER TABLE case_receipts ALTER COLUMN receipt_revision SET DEFAULT 1;
ALTER TABLE case_receipts ALTER COLUMN receipt_revision SET NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'case_receipts_receipt_revision_positive' AND conrelid = 'case_receipts'::regclass) THEN
        ALTER TABLE case_receipts ADD CONSTRAINT case_receipts_receipt_revision_positive CHECK (receipt_revision >= 1);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'case_receipts_case_revision_unique' AND conrelid = 'case_receipts'::regclass) THEN
        ALTER TABLE case_receipts ADD CONSTRAINT case_receipts_case_revision_unique UNIQUE (case_id, receipt_revision);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS case_access_sessions (
    access_session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    receipt_id UUID NOT NULL REFERENCES case_receipts(receipt_id) ON DELETE CASCADE,
    session_digest TEXT NOT NULL UNIQUE,
    session_key_version TEXT NOT NULL DEFAULT 'v1',
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_access_sessions_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_access_sessions OWNER TO vl360;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'case_access_sessions_case_receipt_fkey'
          AND conrelid = 'case_access_sessions'::regclass
    ) THEN
        ALTER TABLE case_access_sessions
            ADD CONSTRAINT case_access_sessions_case_receipt_fkey
            FOREIGN KEY (case_id, receipt_id)
            REFERENCES case_receipts(case_id, receipt_id)
            ON DELETE CASCADE;
    END IF;
END $$;
ALTER TABLE case_access_sessions ADD COLUMN IF NOT EXISTS session_key_version TEXT;
UPDATE case_access_sessions SET session_key_version = 'legacy-unusable' WHERE session_key_version IS NULL;
ALTER TABLE case_access_sessions ALTER COLUMN session_key_version SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_case_access_sessions_expiry
    ON case_access_sessions(expires_at, access_session_id)
    WHERE revoked_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_case_access_same_case() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM case_receipts WHERE receipt_id = NEW.receipt_id AND case_id = NEW.case_id) THEN
        RAISE EXCEPTION 'case_access_receipt_case_mismatch';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION reject_case_receipt_case_move() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.case_id IS DISTINCT FROM NEW.case_id THEN
        RAISE EXCEPTION 'case_receipt_case_immutable';
    END IF;
    RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS case_receipts_case_immutable ON case_receipts;
CREATE TRIGGER case_receipts_case_immutable
BEFORE UPDATE OF case_id ON case_receipts
FOR EACH ROW EXECUTE FUNCTION reject_case_receipt_case_move();
DROP TRIGGER IF EXISTS case_access_sessions_same_case ON case_access_sessions;
CREATE TRIGGER case_access_sessions_same_case BEFORE INSERT OR UPDATE ON case_access_sessions
FOR EACH ROW EXECUTE FUNCTION enforce_case_access_same_case();

CREATE TABLE IF NOT EXISTS case_admin_access_sessions (
    admin_access_session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    actor_ref TEXT NOT NULL,
    scope TEXT NOT NULL,
    session_digest TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_admin_access_sessions_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_admin_access_sessions OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_transitions (
    transition_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    from_phase TEXT CHECK (from_phase IS NULL OR from_phase IN ('intake', 'triage', 'investigation', 'decision', 'fulfillment', 'closed')),
    to_phase TEXT NOT NULL CHECK (to_phase IN ('intake', 'triage', 'investigation', 'decision', 'fulfillment', 'closed')),
    from_revision INTEGER,
    to_revision INTEGER NOT NULL,
    actor_ref TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_transitions_revision_order CHECK (to_revision >= 1 AND (from_revision IS NULL OR to_revision = from_revision + 1))
);
ALTER TABLE case_transitions OWNER TO vl360;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'case_transitions_from_phase_check' AND conrelid = 'case_transitions'::regclass) THEN
        ALTER TABLE case_transitions DROP CONSTRAINT case_transitions_from_phase_check;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'case_transitions_to_phase_check' AND conrelid = 'case_transitions'::regclass) THEN
        ALTER TABLE case_transitions DROP CONSTRAINT case_transitions_to_phase_check;
    END IF;
    ALTER TABLE case_transitions ADD CONSTRAINT case_transitions_from_phase_check
        CHECK (from_phase IS NULL OR from_phase IN ('intake', 'triage', 'investigation', 'decision', 'fulfillment', 'closed'));
    ALTER TABLE case_transitions ADD CONSTRAINT case_transitions_to_phase_check
        CHECK (to_phase IN ('intake', 'triage', 'investigation', 'decision', 'fulfillment', 'closed'));
END $$;

CREATE OR REPLACE FUNCTION reject_case_ledger_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'immutable_case_ledger';
END;
$$;

CREATE TABLE IF NOT EXISTS case_audit_events (
    audit_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    actor_ref TEXT NOT NULL,
    actor_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    channel TEXT,
    reason_code TEXT NOT NULL,
    policy_revision TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    before_snapshot JSONB,
    after_snapshot JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE case_audit_events OWNER TO vl360;

CREATE TABLE IF NOT EXISTS case_outbox (
    outbox_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(case_id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL,
    topic TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'sent', 'failed')),
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    last_error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_outbox_idempotency_unique UNIQUE (idempotency_key)
);
ALTER TABLE case_outbox OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_case_outbox_retry
    ON case_outbox(available_at, outbox_id)
    WHERE status IN ('pending', 'failed');

CREATE TABLE IF NOT EXISTS case_idempotency (
    idempotency_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    idempotency_key TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    response_enc TEXT NOT NULL,
    response_key_version TEXT NOT NULL DEFAULT 'v1',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_idempotency_key_actor_unique UNIQUE (idempotency_key, actor_ref),
    CONSTRAINT case_idempotency_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_idempotency OWNER TO vl360;
ALTER TABLE case_idempotency ADD COLUMN IF NOT EXISTS response_key_version TEXT;
UPDATE case_idempotency SET response_key_version = 'legacy-unusable' WHERE response_key_version IS NULL;
ALTER TABLE case_idempotency ALTER COLUMN response_key_version SET NOT NULL;

CREATE TABLE IF NOT EXISTS case_contact_challenges (
    challenge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    contact_digest TEXT NOT NULL,
    challenge_digest TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('phone', 'email')),
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT case_contact_challenges_expiry_order CHECK (expires_at > created_at)
);
ALTER TABLE case_contact_challenges OWNER TO vl360;

CREATE TABLE IF NOT EXISTS correction_items (
    item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    entity_id TEXT REFERENCES entities(id),
    field_path TEXT NOT NULL,
    reported_value_enc TEXT,
    proposed_value_enc TEXT,
    base_entity_revision INTEGER NOT NULL CHECK (base_entity_revision >= 1),
    risk_class TEXT NOT NULL CHECK (risk_class IN ('R0', 'R1', 'R2', 'R3')),
    evidence_level TEXT NOT NULL CHECK (evidence_level IN ('E0', 'E1', 'E2', 'E3', 'E4')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE correction_items OWNER TO vl360;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'case_decisions_item_id_fkey'
          AND conrelid = 'case_decisions'::regclass
    ) THEN
        ALTER TABLE case_decisions
            ADD CONSTRAINT case_decisions_item_id_fkey
            FOREIGN KEY (item_id) REFERENCES correction_items(item_id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS correction_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    item_id UUID REFERENCES correction_items(item_id) ON DELETE CASCADE,
    evidence_level TEXT NOT NULL CHECK (evidence_level IN ('E0', 'E1', 'E2', 'E3', 'E4')),
    source_ref TEXT,
    descriptor JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_enc TEXT,
    created_by_ref TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE correction_evidence OWNER TO vl360;

CREATE TABLE IF NOT EXISTS correction_change_sets (
    change_set_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    base_entity_revision INTEGER NOT NULL,
    before_patch JSONB NOT NULL,
    after_patch JSONB NOT NULL,
    inverse_patch JSONB NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_revision TEXT NOT NULL,
    risk_class TEXT NOT NULL CHECK (risk_class IN ('R0', 'R1', 'R2', 'R3')),
    decision_maker_ref TEXT NOT NULL,
    reviewer_ref TEXT,
    apply_status TEXT NOT NULL DEFAULT 'pending' CHECK (apply_status IN ('pending', 'applied', 'rolled_back', 'rejected')),
    public_projection_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT correction_change_sets_base_revision_positive CHECK (base_entity_revision >= 1)
);
ALTER TABLE correction_change_sets OWNER TO vl360;

CREATE TABLE IF NOT EXISTS correction_change_set_items (
    change_set_id UUID NOT NULL REFERENCES correction_change_sets(change_set_id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES correction_items(item_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (change_set_id, item_id)
);
ALTER TABLE correction_change_set_items OWNER TO vl360;

DO $$
DECLARE
    invalid_item_ids BOOLEAN;
BEGIN
    IF to_regclass('public.correction_change_sets') IS NOT NULL
       AND EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = 'correction_change_sets' AND column_name = 'item_ids'
       ) THEN
        IF EXISTS (SELECT 1 FROM correction_change_sets WHERE jsonb_typeof(item_ids) <> 'array') THEN
            RAISE EXCEPTION 'correction_change_set_item_ids_unmigratable';
        END IF;
        SELECT EXISTS (
            SELECT 1
            FROM correction_change_sets c
            CROSS JOIN LATERAL jsonb_array_elements(c.item_ids) value
            WHERE jsonb_typeof(value) <> 'string'
               OR NOT EXISTS (
                   SELECT 1 FROM correction_items i
                   WHERE i.item_id = (value #>> '{}')::uuid AND i.case_id = c.case_id
               )
        ) INTO invalid_item_ids;
        IF invalid_item_ids THEN
            RAISE EXCEPTION 'correction_change_set_item_ids_unmigratable';
        END IF;
        INSERT INTO correction_change_set_items(change_set_id, item_id)
        SELECT c.change_set_id, (value #>> '{}')::uuid
        FROM correction_change_sets c
        CROSS JOIN LATERAL jsonb_array_elements(c.item_ids) value
        ON CONFLICT DO NOTHING;
        ALTER TABLE correction_change_sets DROP COLUMN item_ids;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION enforce_change_set_item_same_case() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM correction_change_sets c
        JOIN correction_items i ON i.item_id = NEW.item_id
        WHERE c.change_set_id = NEW.change_set_id AND c.case_id = i.case_id
    ) THEN
        RAISE EXCEPTION 'change_set_item_case_mismatch';
    END IF;
    RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS correction_change_set_items_same_case ON correction_change_set_items;
CREATE TRIGGER correction_change_set_items_same_case
BEFORE INSERT OR UPDATE ON correction_change_set_items
FOR EACH ROW EXECUTE FUNCTION enforce_change_set_item_same_case();

CREATE OR REPLACE FUNCTION enforce_linked_correction_item_same_case() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.case_id IS DISTINCT FROM OLD.case_id AND EXISTS (
        SELECT 1
        FROM correction_change_set_items link
        JOIN correction_change_sets c ON c.change_set_id = link.change_set_id
        WHERE link.item_id = OLD.item_id AND c.case_id IS DISTINCT FROM NEW.case_id
    ) THEN
        RAISE EXCEPTION 'change_set_item_case_mismatch';
    END IF;
    RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS correction_items_linked_case_immutable ON correction_items;
CREATE TRIGGER correction_items_linked_case_immutable
BEFORE UPDATE OF case_id ON correction_items
FOR EACH ROW EXECUTE FUNCTION enforce_linked_correction_item_same_case();

DROP TRIGGER IF EXISTS correction_change_sets_immutable ON correction_change_sets;
CREATE TRIGGER correction_change_sets_immutable BEFORE UPDATE OR DELETE ON correction_change_sets
FOR EACH ROW EXECUTE FUNCTION reject_case_ledger_mutation();
DROP TRIGGER IF EXISTS correction_change_set_items_immutable ON correction_change_set_items;
CREATE TRIGGER correction_change_set_items_immutable BEFORE UPDATE OR DELETE ON correction_change_set_items
FOR EACH ROW EXECUTE FUNCTION reject_case_ledger_mutation();

CREATE TABLE IF NOT EXISTS legacy_intake_records (
    legacy_intake_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_file TEXT NOT NULL,
    source_line INTEGER NOT NULL CHECK (source_line >= 1),
    raw_record_digest TEXT NOT NULL CHECK (raw_record_digest ~ '^[0-9a-f]{64}$'),
    imported_case_id UUID REFERENCES cases(case_id),
    legacy_status TEXT,
    missing_data_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    mapping_decision TEXT NOT NULL,
    import_result TEXT NOT NULL,
    reconciliation_result TEXT,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT legacy_intake_locator_unique UNIQUE (source_file, source_line)
);
ALTER TABLE legacy_intake_records OWNER TO vl360;
CREATE INDEX IF NOT EXISTS idx_legacy_intake_reconcile
    ON legacy_intake_records(import_result, imported_at);

CREATE TABLE IF NOT EXISTS case_capacity_events (
    capacity_event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(case_id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    risk_class TEXT CHECK (risk_class IN ('R0', 'R1', 'R2', 'R3')),
    event_kind TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
ALTER TABLE case_capacity_events OWNER TO vl360;

DROP TRIGGER IF EXISTS case_transitions_immutable ON case_transitions;
CREATE TRIGGER case_transitions_immutable BEFORE UPDATE OR DELETE ON case_transitions
FOR EACH ROW EXECUTE FUNCTION reject_case_ledger_mutation();
DROP TRIGGER IF EXISTS case_audit_events_immutable ON case_audit_events;
CREATE TRIGGER case_audit_events_immutable BEFORE UPDATE OR DELETE ON case_audit_events
FOR EACH ROW EXECUTE FUNCTION reject_case_ledger_mutation();

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 80, '080_correction_case_kernel.sql', NOW())
ON CONFLICT (component) DO UPDATE SET
    version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
