-- Make the change set lifecycle columns reachable (PostgreSQL only).
-- No rows are rewritten by this migration.
--
-- 080 gave correction_change_sets two columns whose only purpose is to record
-- what happens AFTER the insert: apply_status, whose CHECK already enumerates
-- pending/applied/rolled_back/rejected, and public_projection_verified_at. The
-- same file then froze the whole row with BEFORE UPDATE OR DELETE, so both
-- columns could never leave their defaults and a decided correction could never
-- be marked as published. The two statements contradicted each other.
--
-- What that trigger is for is that the DECISION cannot be rewritten: which
-- entry, at which revision, with which patch, on whose evidence, decided and
-- reviewed by whom, and when. Every one of those columns is named below, so
-- that protection is unchanged. What opens is the pair that records the
-- outcome. DELETE stays rejected, because a change set that was applied to a
-- live entry must remain answerable afterwards.

DROP TRIGGER IF EXISTS correction_change_sets_immutable ON correction_change_sets;
CREATE TRIGGER correction_change_sets_immutable
BEFORE UPDATE OF case_id, base_entity_revision, before_patch, after_patch, inverse_patch,
                 evidence_refs, policy_revision, risk_class, decision_maker_ref,
                 reviewer_ref, created_at
    OR DELETE ON correction_change_sets
FOR EACH ROW EXECUTE FUNCTION reject_case_ledger_mutation();

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 81, '081_change_set_lifecycle.sql', NOW())
ON CONFLICT (component) DO UPDATE SET
    version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
