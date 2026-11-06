-- MediMatch AI — Migration 00014: Doctor Billing
-- Patients pay MediMatch nothing. Each doctor chooses a fee per completed appointment or a monthly
-- subscription. This records what is owed: no money moves through the app. With a price unset,
-- nothing is charged.

-- ==============================================================================
-- 1. Tables
-- ==============================================================================
-- One row, holding the current prices in whole taka
CREATE TABLE IF NOT EXISTS public.billing_settings (
    id BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (id),
    booking_fee_bdt INTEGER CHECK (booking_fee_bdt > 0),
    subscription_monthly_bdt INTEGER CHECK (subscription_monthly_bdt > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.billing_settings (id) VALUES (TRUE) ON CONFLICT DO NOTHING;

DROP TRIGGER IF EXISTS billing_settings_set_updated_at ON public.billing_settings;
CREATE TRIGGER billing_settings_set_updated_at BEFORE UPDATE ON public.billing_settings
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE TABLE IF NOT EXISTS public.doctor_billing_plans (
    doctor_id UUID PRIMARY KEY REFERENCES public.doctor_profiles(id) ON DELETE CASCADE,
    plan TEXT NOT NULL CHECK (plan IN ('booking_fee', 'subscription')),
    chosen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A charge keeps its amount, so a later price change never rewrites what a doctor already owes
CREATE TABLE IF NOT EXISTS public.billing_charges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES public.doctor_profiles(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('booking_fee', 'subscription')),
    appointment_id UUID UNIQUE REFERENCES public.appointments(id) ON DELETE SET NULL,
    billing_month DATE CHECK (billing_month = date_trunc('month', billing_month)::date),
    amount_bdt INTEGER NOT NULL CHECK (amount_bdt > 0),
    status TEXT NOT NULL DEFAULT 'owed' CHECK (status IN ('owed', 'paid', 'waived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    settled_at TIMESTAMPTZ,
    CONSTRAINT subscription_has_month CHECK (kind <> 'subscription' OR billing_month IS NOT NULL),
    CONSTRAINT one_subscription_charge_a_month UNIQUE (doctor_id, billing_month)
);

CREATE INDEX IF NOT EXISTS idx_billing_charges_doctor ON public.billing_charges(doctor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_charges_status ON public.billing_charges(status, created_at DESC);

-- ==============================================================================
-- 2. Row-Level Security: reads only. The API is the only writer
-- ==============================================================================
ALTER TABLE public.billing_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.doctor_billing_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_charges ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "billing_settings_read_admin" ON public.billing_settings;
CREATE POLICY "billing_settings_read_admin" ON public.billing_settings
    FOR SELECT USING (public.is_admin());

DROP POLICY IF EXISTS "doctor_billing_plans_read" ON public.doctor_billing_plans;
CREATE POLICY "doctor_billing_plans_read" ON public.doctor_billing_plans
    FOR SELECT USING (
        public.is_admin()
        OR EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = doctor_id AND dp.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "billing_charges_read" ON public.billing_charges;
CREATE POLICY "billing_charges_read" ON public.billing_charges
    FOR SELECT USING (
        public.is_admin()
        OR EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = doctor_id AND dp.user_id = auth.uid()
        )
    );

-- ==============================================================================
-- 3. Booking Fees
-- ==============================================================================
-- A trigger, so that no way of completing an appointment can skip the fee. The unique
-- appointment_id means an appointment can never be charged twice.
CREATE OR REPLACE FUNCTION public.charge_completed_appointment()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_fee INTEGER;
BEGIN
    SELECT s.booking_fee_bdt INTO v_fee
    FROM public.doctor_billing_plans p
    CROSS JOIN public.billing_settings s
    WHERE p.doctor_id = NEW.doctor_id AND p.plan = 'booking_fee';

    IF v_fee IS NOT NULL THEN
        INSERT INTO public.billing_charges (doctor_id, kind, appointment_id, amount_bdt)
        VALUES (NEW.doctor_id, 'booking_fee', NEW.id, v_fee)
        ON CONFLICT (appointment_id) DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS appointments_charge_on_complete ON public.appointments;
CREATE TRIGGER appointments_charge_on_complete
    AFTER UPDATE OF status ON public.appointments
    FOR EACH ROW
    WHEN (NEW.status = 'completed' AND OLD.status IS DISTINCT FROM 'completed')
    EXECUTE FUNCTION public.charge_completed_appointment();

-- ==============================================================================
-- 4. Subscriptions
-- ==============================================================================
-- Charges the current Dhaka month once for each approved doctor on the plan, or for one doctor.
-- Safe to run again at any time. Returns how many charges it added.
CREATE OR REPLACE FUNCTION public.bill_subscriptions(p_doctor_id UUID DEFAULT NULL)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_month DATE := date_trunc('month', now() AT TIME ZONE 'Asia/Dhaka')::date;
    v_added INTEGER;
BEGIN
    INSERT INTO public.billing_charges (doctor_id, kind, billing_month, amount_bdt)
    SELECT p.doctor_id, 'subscription', v_month, s.subscription_monthly_bdt
    FROM public.doctor_billing_plans p
    JOIN public.doctor_profiles d ON d.id = p.doctor_id
    CROSS JOIN public.billing_settings s
    WHERE p.plan = 'subscription'
      AND d.verification_status = 'approved'
      AND s.subscription_monthly_bdt IS NOT NULL
      AND (p_doctor_id IS NULL OR p.doctor_id = p_doctor_id)
    ON CONFLICT (doctor_id, billing_month) DO NOTHING;

    GET DIAGNOSTICS v_added = ROW_COUNT;
    RETURN v_added;
END;
$$;

REVOKE ALL ON FUNCTION public.charge_completed_appointment() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.bill_subscriptions(UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.bill_subscriptions(UUID) TO service_role;
