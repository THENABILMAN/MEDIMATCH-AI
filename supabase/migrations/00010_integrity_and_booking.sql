-- MediMatch AI — Migration 00010: Data Integrity and Atomic Appointment Changes

-- ==============================================================================
-- 1. Timestamps
-- ==============================================================================
-- timezone('utc', now()) gives a timestamp with no zone, which is then read using the session
-- timezone. now() is already an exact instant.
ALTER TABLE public.profiles ALTER COLUMN created_at SET DEFAULT now(), ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE public.specialties ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE public.doctor_profiles ALTER COLUMN created_at SET DEFAULT now(), ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE public.availability_slots ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE public.appointments ALTER COLUMN created_at SET DEFAULT now(), ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE public.conversations ALTER COLUMN created_at SET DEFAULT now(), ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE public.messages ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE public.patient_symptom_sessions ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE public.audit_logs ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE public.doctor_credentials ALTER COLUMN uploaded_at SET DEFAULT now();

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := clock_timestamp();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tr_appointments_updated_at ON public.appointments;
CREATE TRIGGER tr_appointments_updated_at
    BEFORE UPDATE ON public.appointments
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS tr_conversations_updated_at ON public.conversations;
CREATE TRIGGER tr_conversations_updated_at
    BEFORE UPDATE ON public.conversations
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ==============================================================================
-- 2. Indexes
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_appointments_slot ON public.appointments(slot_id);
CREATE INDEX IF NOT EXISTS idx_conversations_patient ON public.conversations(patient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_symptom_sessions_patient ON public.patient_symptom_sessions(patient_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON public.messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON public.audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target ON public.audit_logs(target_type, target_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON public.audit_logs(actor_id);

-- ==============================================================================
-- 3. Constraints
-- ==============================================================================
ALTER TABLE public.availability_slots DROP CONSTRAINT IF EXISTS check_slot_min_duration;
ALTER TABLE public.availability_slots
    ADD CONSTRAINT check_slot_min_duration CHECK (end_time >= start_time + interval '15 minutes');

-- Records of care must survive: accounts close by anonymizing, never by deleting these rows
ALTER TABLE public.appointments DROP CONSTRAINT appointments_patient_id_fkey;
ALTER TABLE public.appointments
    ADD CONSTRAINT appointments_patient_id_fkey
    FOREIGN KEY (patient_id) REFERENCES public.profiles(id) ON DELETE RESTRICT;

ALTER TABLE public.appointments DROP CONSTRAINT appointments_doctor_id_fkey;
ALTER TABLE public.appointments
    ADD CONSTRAINT appointments_doctor_id_fkey
    FOREIGN KEY (doctor_id) REFERENCES public.doctor_profiles(id) ON DELETE RESTRICT;

-- ==============================================================================
-- 4. Appointment Time Snapshot
-- ==============================================================================
-- A slot can be deleted after its appointment was cancelled, and the record must keep its time.
ALTER TABLE public.appointments
    ADD COLUMN IF NOT EXISTS scheduled_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS scheduled_end TIMESTAMPTZ;

UPDATE public.appointments a
SET scheduled_start = s.start_time, scheduled_end = s.end_time
FROM public.availability_slots s
WHERE a.slot_id = s.id AND a.scheduled_start IS NULL;

CREATE INDEX IF NOT EXISTS idx_appointments_patient_active
    ON public.appointments(patient_id, scheduled_start) WHERE status = 'booked';

-- ==============================================================================
-- 5. Immutable Audit Log
-- ==============================================================================
-- RLS does not bind the service role, so this is enforced for every writer. The one allowed change
-- is the foreign key clearing actor_id when an auth user is removed.
CREATE OR REPLACE FUNCTION public.protect_audit_logs()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.actor_id IS NULL
        AND (to_jsonb(NEW) - 'actor_id') = (to_jsonb(OLD) - 'actor_id') THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'audit_logs is append-only';
END;
$$;

DROP TRIGGER IF EXISTS tr_protect_audit_logs ON public.audit_logs;
CREATE TRIGGER tr_protect_audit_logs
    BEFORE UPDATE OR DELETE ON public.audit_logs
    FOR EACH ROW EXECUTE FUNCTION public.protect_audit_logs();

-- ==============================================================================
-- 6. Atomic Booking
-- ==============================================================================
DROP FUNCTION IF EXISTS public.book_appointment_atomic(UUID, UUID);

CREATE OR REPLACE FUNCTION public.book_appointment_atomic(
    p_slot_id UUID,
    p_patient_id UUID,
    p_max_active INTEGER
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_slot RECORD;
    v_doctor RECORD;
    v_appointment RECORD;
BEGIN
    SELECT * INTO v_slot FROM public.availability_slots WHERE id = p_slot_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Availability slot not found', 'code', 404);
    END IF;

    IF v_slot.is_booked THEN
        RETURN jsonb_build_object('success', false, 'error', 'This slot has already been booked by another patient', 'code', 409);
    END IF;

    IF v_slot.start_time <= now() THEN
        RETURN jsonb_build_object('success', false, 'error', 'Cannot book an appointment slot in the past', 'code', 400);
    END IF;

    SELECT * INTO v_doctor FROM public.doctor_profiles WHERE id = v_slot.doctor_id;
    IF NOT FOUND OR v_doctor.verification_status != 'approved' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Doctor is not approved for appointment bookings', 'code', 400);
    END IF;

    IF v_doctor.user_id = p_patient_id THEN
        RETURN jsonb_build_object('success', false, 'error', 'Doctors cannot book their own appointment slots', 'code', 400);
    END IF;

    -- Taken after the slot lock, so one patient's simultaneous bookings count correctly
    PERFORM pg_advisory_xact_lock(hashtextextended(p_patient_id::text, 0));

    IF (
        SELECT count(*) FROM public.appointments
        WHERE patient_id = p_patient_id AND status = 'booked' AND scheduled_start > now()
    ) >= p_max_active THEN
        RETURN jsonb_build_object('success', false, 'error', 'You have reached the limit of upcoming appointments. Cancel one to book another.', 'code', 409);
    END IF;

    IF EXISTS (
        SELECT 1 FROM public.appointments
        WHERE patient_id = p_patient_id AND status = 'booked'
          AND tstzrange(scheduled_start, scheduled_end) && tstzrange(v_slot.start_time, v_slot.end_time)
    ) THEN
        RETURN jsonb_build_object('success', false, 'error', 'You already have an appointment at this time.', 'code', 409);
    END IF;

    UPDATE public.availability_slots SET is_booked = true WHERE id = p_slot_id;

    INSERT INTO public.appointments (patient_id, doctor_id, slot_id, status, scheduled_start, scheduled_end)
    VALUES (p_patient_id, v_slot.doctor_id, p_slot_id, 'booked', v_slot.start_time, v_slot.end_time)
    RETURNING * INTO v_appointment;

    RETURN jsonb_build_object(
        'success', true,
        'appointment_id', v_appointment.id,
        'doctor_id', v_appointment.doctor_id
    );
END;
$$;

-- ==============================================================================
-- 7. Atomic Cancel and Complete
-- ==============================================================================
CREATE OR REPLACE FUNCTION public.cancel_appointment_atomic(p_appointment_id UUID)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_appointment RECORD;
BEGIN
    SELECT * INTO v_appointment FROM public.appointments WHERE id = p_appointment_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Appointment not found', 'code', 404);
    END IF;

    IF v_appointment.status = 'cancelled' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Appointment is already cancelled', 'code', 400);
    END IF;
    IF v_appointment.status = 'completed' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Cannot cancel an appointment that is already completed', 'code', 400);
    END IF;
    IF v_appointment.scheduled_start <= now() THEN
        RETURN jsonb_build_object('success', false, 'error', 'Cannot cancel an appointment that has already started', 'code', 400);
    END IF;

    UPDATE public.appointments SET status = 'cancelled' WHERE id = p_appointment_id;

    -- Only frees the slot if nobody else holds it
    UPDATE public.availability_slots s SET is_booked = false
    WHERE s.id = v_appointment.slot_id
      AND NOT EXISTS (
          SELECT 1 FROM public.appointments a
          WHERE a.slot_id = s.id AND a.status = 'booked' AND a.id <> p_appointment_id
      );

    RETURN jsonb_build_object('success', true);
END;
$$;

CREATE OR REPLACE FUNCTION public.complete_appointment_atomic(p_appointment_id UUID)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_appointment RECORD;
BEGIN
    SELECT * INTO v_appointment FROM public.appointments WHERE id = p_appointment_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Appointment not found', 'code', 404);
    END IF;

    IF v_appointment.status = 'cancelled' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Cannot complete a cancelled appointment', 'code', 400);
    END IF;
    IF v_appointment.status = 'completed' THEN
        RETURN jsonb_build_object('success', false, 'error', 'This appointment is already completed', 'code', 400);
    END IF;
    IF v_appointment.scheduled_start > now() THEN
        RETURN jsonb_build_object('success', false, 'error', 'Cannot complete an appointment before it starts', 'code', 400);
    END IF;

    UPDATE public.appointments SET status = 'completed' WHERE id = p_appointment_id;
    RETURN jsonb_build_object('success', true);
END;
$$;

REVOKE ALL ON FUNCTION public.book_appointment_atomic(UUID, UUID, INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.cancel_appointment_atomic(UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.complete_appointment_atomic(UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.book_appointment_atomic(UUID, UUID, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.cancel_appointment_atomic(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_appointment_atomic(UUID) TO service_role;
