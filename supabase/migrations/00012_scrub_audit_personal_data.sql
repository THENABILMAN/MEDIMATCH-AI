-- MediMatch AI — Migration 00012: Remove Personal Data From Audit Logs
-- Older entries stored emails, names and phone numbers in metadata. New entries hold field names
-- only. This is the one change allowed to an append-only table, and it keeps every event.

ALTER TABLE public.audit_logs DISABLE TRIGGER tr_protect_audit_logs;

UPDATE public.audit_logs
SET metadata = metadata - 'email' - 'file_path'
WHERE metadata ? 'email' OR metadata ? 'file_path';

UPDATE public.audit_logs
SET metadata = jsonb_build_object(
    'changed_fields',
    (SELECT coalesce(jsonb_agg(key ORDER BY key), '[]'::jsonb) FROM jsonb_object_keys(metadata) AS key)
)
WHERE action IN ('UPDATE_PROFILE', 'UPDATE_DOCTOR_PROFILE')
  AND NOT metadata ? 'changed_fields';

ALTER TABLE public.audit_logs ENABLE TRIGGER tr_protect_audit_logs;
