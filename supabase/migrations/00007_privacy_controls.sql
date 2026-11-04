-- MediMatch AI — Migration 00007: Privacy Controls
-- Records AI assistant consent and marks anonymized patient accounts.

ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS ai_consent_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_profiles_role_active ON public.profiles(role)
    WHERE deleted_at IS NULL;
