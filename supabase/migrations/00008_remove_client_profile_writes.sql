-- MediMatch AI — Migration 00008: Remove Remaining Client Writes
-- 00006 made the API the only writer but left these policies behind. Clients could forge their
-- own consent and deletion timestamps, and a user with no profile row could insert role = 'admin'.
-- The service role bypasses RLS and handle_new_user runs as definer, so neither is affected.

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
DROP POLICY IF EXISTS "profiles_insert_own_or_service" ON public.profiles;

-- Audit entries come from the API alone, so an admin session cannot forge one.
DROP POLICY IF EXISTS "audit_logs_insert_service" ON public.audit_logs;

-- Admin changes go through the API, where they are audited.
DROP POLICY IF EXISTS "specialties_admin_modify" ON public.specialties;
DROP POLICY IF EXISTS "doctor_profiles_delete_admin" ON public.doctor_profiles;
