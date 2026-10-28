-- MediMatch AI — Migration 00002: Row-Level Security (RLS) Policies
-- Enforces least-privilege access across all user data tables.

-- ==============================================================================
-- 1. Helper Functions
-- ==============================================================================

-- Check if current authenticated user has the 'admin' role
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT (
        auth.role() = 'service_role' OR
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );
$$;

-- Trigger to prevent doctors from self-approving their verification status
CREATE OR REPLACE FUNCTION public.protect_doctor_verification_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.verification_status IS DISTINCT FROM OLD.verification_status THEN
        IF NOT public.is_admin() THEN
            RAISE EXCEPTION 'Unauthorized: Only platform administrators can change doctor verification status';
        END IF;
    END IF;
    NEW.updated_at := timezone('utc'::text, now());
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tr_protect_doctor_verification ON public.doctor_profiles;
CREATE TRIGGER tr_protect_doctor_verification
    BEFORE UPDATE ON public.doctor_profiles
    FOR EACH ROW EXECUTE FUNCTION public.protect_doctor_verification_status();

-- ==============================================================================
-- 2. Enable RLS on All Tables
-- ==============================================================================
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.specialties ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctor_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctor_specialties ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.availability_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patient_symptom_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- 3. Profiles Policies
-- ==============================================================================
DROP POLICY IF EXISTS "profiles_select_own_or_admin" ON public.profiles;
CREATE POLICY "profiles_select_own_or_admin" ON public.profiles
    FOR SELECT USING (
        auth.uid() = id 
        OR public.is_admin()
        -- Allow public to see basic profile of approved doctors
        OR EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.user_id = profiles.id AND dp.verification_status = 'approved'
        )
    );

DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own" ON public.profiles
    FOR UPDATE USING (
        auth.uid() = id OR public.is_admin()
    );

DROP POLICY IF EXISTS "profiles_insert_own_or_service" ON public.profiles;
CREATE POLICY "profiles_insert_own_or_service" ON public.profiles
    FOR INSERT WITH CHECK (
        auth.uid() = id OR auth.role() = 'service_role'
    );

-- ==============================================================================
-- 4. Specialties Policies
-- ==============================================================================
DROP POLICY IF EXISTS "specialties_select_all" ON public.specialties;
CREATE POLICY "specialties_select_all" ON public.specialties
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "specialties_admin_modify" ON public.specialties;
CREATE POLICY "specialties_admin_modify" ON public.specialties
    FOR ALL USING (public.is_admin());

-- ==============================================================================
-- 5. Doctor Profiles Policies
-- ==============================================================================
-- Patients and public can ONLY see approved doctors.
-- Doctors can see their own profile regardless of status. Admins see all.
DROP POLICY IF EXISTS "doctor_profiles_select_policy" ON public.doctor_profiles;
CREATE POLICY "doctor_profiles_select_policy" ON public.doctor_profiles
    FOR SELECT USING (
        verification_status = 'approved'
        OR user_id = auth.uid()
        OR public.is_admin()
    );

DROP POLICY IF EXISTS "doctor_profiles_insert_own" ON public.doctor_profiles;
CREATE POLICY "doctor_profiles_insert_own" ON public.doctor_profiles
    FOR INSERT WITH CHECK (
        (user_id = auth.uid() AND verification_status = 'pending')
        OR public.is_admin()
    );

DROP POLICY IF EXISTS "doctor_profiles_update_policy" ON public.doctor_profiles;
CREATE POLICY "doctor_profiles_update_policy" ON public.doctor_profiles
    FOR UPDATE USING (
        user_id = auth.uid() OR public.is_admin()
    );

DROP POLICY IF EXISTS "doctor_profiles_delete_admin" ON public.doctor_profiles;
CREATE POLICY "doctor_profiles_delete_admin" ON public.doctor_profiles
    FOR DELETE USING (public.is_admin());

-- ==============================================================================
-- 6. Doctor Specialties Policies
-- ==============================================================================
DROP POLICY IF EXISTS "doctor_specialties_select" ON public.doctor_specialties;
CREATE POLICY "doctor_specialties_select" ON public.doctor_specialties
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = doctor_specialties.doctor_id
            AND (dp.verification_status = 'approved' OR dp.user_id = auth.uid() OR public.is_admin())
        )
    );

DROP POLICY IF EXISTS "doctor_specialties_manage_own" ON public.doctor_specialties;
CREATE POLICY "doctor_specialties_manage_own" ON public.doctor_specialties
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = doctor_specialties.doctor_id
            AND (dp.user_id = auth.uid() OR public.is_admin())
        )
    );

-- ==============================================================================
-- 7. Availability Slots Policies
-- ==============================================================================
DROP POLICY IF EXISTS "availability_slots_select" ON public.availability_slots;
CREATE POLICY "availability_slots_select" ON public.availability_slots
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = availability_slots.doctor_id
            AND (dp.verification_status = 'approved' OR dp.user_id = auth.uid() OR public.is_admin())
        )
    );

DROP POLICY IF EXISTS "availability_slots_manage_own" ON public.availability_slots;
CREATE POLICY "availability_slots_manage_own" ON public.availability_slots
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = availability_slots.doctor_id
            AND (dp.user_id = auth.uid() OR public.is_admin())
        )
    );

-- ==============================================================================
-- 8. Appointments Policies
-- ==============================================================================
DROP POLICY IF EXISTS "appointments_select_parties" ON public.appointments;
CREATE POLICY "appointments_select_parties" ON public.appointments
    FOR SELECT USING (
        patient_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = appointments.doctor_id AND dp.user_id = auth.uid()
        )
        OR public.is_admin()
    );

DROP POLICY IF EXISTS "appointments_insert_patient" ON public.appointments;
CREATE POLICY "appointments_insert_patient" ON public.appointments
    FOR INSERT WITH CHECK (
        patient_id = auth.uid() OR public.is_admin()
    );

DROP POLICY IF EXISTS "appointments_update_parties" ON public.appointments;
CREATE POLICY "appointments_update_parties" ON public.appointments
    FOR UPDATE USING (
        patient_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = appointments.doctor_id AND dp.user_id = auth.uid()
        )
        OR public.is_admin()
    );

-- ==============================================================================
-- 9. Conversations & Messages Policies
-- ==============================================================================
DROP POLICY IF EXISTS "conversations_patient_only" ON public.conversations;
CREATE POLICY "conversations_patient_only" ON public.conversations
    FOR ALL USING (
        patient_id = auth.uid() OR public.is_admin()
    );

DROP POLICY IF EXISTS "messages_conversation_parties" ON public.messages;
CREATE POLICY "messages_conversation_parties" ON public.messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = messages.conversation_id
            AND (c.patient_id = auth.uid() OR public.is_admin())
        )
    );

DROP POLICY IF EXISTS "messages_insert_patient" ON public.messages;
CREATE POLICY "messages_insert_patient" ON public.messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.conversations c
            WHERE c.id = messages.conversation_id
            AND (c.patient_id = auth.uid() OR public.is_admin())
        )
        OR auth.role() = 'service_role'
    );

-- ==============================================================================
-- 10. Patient Symptom Sessions Policies
-- ==============================================================================
DROP POLICY IF EXISTS "patient_symptom_sessions_own" ON public.patient_symptom_sessions;
CREATE POLICY "patient_symptom_sessions_own" ON public.patient_symptom_sessions
    FOR ALL USING (
        patient_id = auth.uid() OR public.is_admin()
    );

-- ==============================================================================
-- 11. Audit Logs Policies (Append-only by service role, admin read-only)
-- ==============================================================================
DROP POLICY IF EXISTS "audit_logs_select_admin" ON public.audit_logs;
CREATE POLICY "audit_logs_select_admin" ON public.audit_logs
    FOR SELECT USING (public.is_admin());

DROP POLICY IF EXISTS "audit_logs_insert_service" ON public.audit_logs;
CREATE POLICY "audit_logs_insert_service" ON public.audit_logs
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role' OR public.is_admin()
    );

-- Prevent update or delete on audit logs
DROP POLICY IF EXISTS "audit_logs_no_update" ON public.audit_logs;
CREATE POLICY "audit_logs_no_update" ON public.audit_logs
    FOR UPDATE USING (false);

DROP POLICY IF EXISTS "audit_logs_no_delete" ON public.audit_logs;
CREATE POLICY "audit_logs_no_delete" ON public.audit_logs
    FOR DELETE USING (false);

