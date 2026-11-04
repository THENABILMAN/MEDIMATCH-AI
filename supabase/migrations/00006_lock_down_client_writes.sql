-- MediMatch AI — Migration 00006: Lock Down Client Writes
-- The API owns every write, with its business rules, using the service role. The public anon
-- key must not be able to skip those rules by talking to PostgREST directly.

-- ==============================================================================
-- 1. Booking Procedure: backend only
-- ==============================================================================
-- SECURITY DEFINER with a caller-supplied patient id, so anyone able to execute it could book
-- for any patient.
REVOKE ALL ON FUNCTION public.book_appointment_atomic(UUID, UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.book_appointment_atomic(UUID, UUID) TO service_role;

-- ==============================================================================
-- 2. Remove Direct Write Policies (service role bypasses RLS and is unaffected)
-- ==============================================================================
DROP POLICY IF EXISTS "appointments_insert_patient" ON public.appointments;
DROP POLICY IF EXISTS "appointments_update_parties" ON public.appointments;
DROP POLICY IF EXISTS "availability_slots_manage_own" ON public.availability_slots;
DROP POLICY IF EXISTS "doctor_profiles_insert_own" ON public.doctor_profiles;
DROP POLICY IF EXISTS "doctor_profiles_update_policy" ON public.doctor_profiles;
DROP POLICY IF EXISTS "doctor_specialties_manage_own" ON public.doctor_specialties;
DROP POLICY IF EXISTS "doctor_credentials_insert_own" ON public.doctor_credentials;
DROP POLICY IF EXISTS "doctor_credentials_delete_own" ON public.doctor_credentials;
DROP POLICY IF EXISTS "messages_insert_patient" ON public.messages;

-- ==============================================================================
-- 3. Reduce FOR ALL Policies to Read-Only
-- ==============================================================================
DROP POLICY IF EXISTS "conversations_patient_only" ON public.conversations;
DROP POLICY IF EXISTS "conversations_select_own" ON public.conversations;
CREATE POLICY "conversations_select_own" ON public.conversations
    FOR SELECT USING (
        patient_id = auth.uid() OR public.is_admin()
    );

DROP POLICY IF EXISTS "patient_symptom_sessions_own" ON public.patient_symptom_sessions;
DROP POLICY IF EXISTS "patient_symptom_sessions_select_own" ON public.patient_symptom_sessions;
CREATE POLICY "patient_symptom_sessions_select_own" ON public.patient_symptom_sessions
    FOR SELECT USING (
        patient_id = auth.uid() OR public.is_admin()
    );

-- ==============================================================================
-- 4. Stop Exposing Doctors' Private Profile Fields
-- ==============================================================================
-- This policy exposed whole rows of approved doctors, including phone numbers. Public names
-- are served by the API, which selects only what it needs.
DROP POLICY IF EXISTS "profiles_select_own_or_admin" ON public.profiles;
CREATE POLICY "profiles_select_own_or_admin" ON public.profiles
    FOR SELECT USING (
        auth.uid() = id OR public.is_admin()
    );

-- ==============================================================================
-- 5. Persist Assistant Message Details
-- ==============================================================================
-- Keeps emergency alerts and recommendation cards visible when a conversation is reloaded.
ALTER TABLE public.messages
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
