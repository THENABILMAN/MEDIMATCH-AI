-- MediMatch AI — Migration 00005: Appointments Concurrency and Slot Integrity
-- Implements database-level anti-double-booking constraints and atomic stored procedure.

-- 1. Enable btree_gist extension for PostgreSQL exclusion constraints
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- 2. Prevent overlapping availability slots for the same doctor
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'no_overlapping_slots'
    ) THEN
        ALTER TABLE public.availability_slots
        ADD CONSTRAINT no_overlapping_slots
        EXCLUDE USING gist (
            doctor_id WITH =,
            tstzrange(start_time, end_time) WITH &&
        );
    END IF;
END $$;

-- 3. Unique constraint preventing duplicate active bookings on the same slot
CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_slot_booked
ON public.appointments (slot_id)
WHERE status = 'booked';

-- 4. Atomic Booking Stored Procedure with Pessimistic Row Locking
CREATE OR REPLACE FUNCTION public.book_appointment_atomic(
    p_slot_id UUID,
    p_patient_id UUID
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
    -- 1. Acquire pessimistic row-level lock on the availability slot
    SELECT * INTO v_slot
    FROM public.availability_slots
    WHERE id = p_slot_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Availability slot not found',
            'code', 404
        );
    END IF;

    -- 2. Check if already booked
    IF v_slot.is_booked THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'This slot has already been booked by another patient',
            'code', 409
        );
    END IF;

    -- 3. Check slot start time is in the future
    IF v_slot.start_time <= timezone('utc'::text, now()) THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Cannot book an appointment slot in the past',
            'code', 400
        );
    END IF;

    -- 4. Verify doctor is approved
    SELECT * INTO v_doctor
    FROM public.doctor_profiles
    WHERE id = v_slot.doctor_id;

    IF NOT FOUND OR v_doctor.verification_status != 'approved' THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Doctor is not approved for appointment bookings',
            'code', 400
        );
    END IF;

    -- 5. Prevent doctor from booking their own slot
    IF v_doctor.user_id = p_patient_id THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Doctors cannot book their own appointment slots',
            'code', 400
        );
    END IF;

    -- 6. Mark slot as booked
    UPDATE public.availability_slots
    SET is_booked = true
    WHERE id = p_slot_id;

    -- 7. Insert appointment record
    INSERT INTO public.appointments (patient_id, doctor_id, slot_id, status)
    VALUES (p_patient_id, v_slot.doctor_id, p_slot_id, 'booked')
    RETURNING * INTO v_appointment;

    RETURN jsonb_build_object(
        'success', true,
        'appointment_id', v_appointment.id,
        'doctor_id', v_appointment.doctor_id,
        'patient_id', v_appointment.patient_id,
        'slot_id', v_appointment.slot_id,
        'status', v_appointment.status,
        'created_at', v_appointment.created_at
    );
END;
$$;

