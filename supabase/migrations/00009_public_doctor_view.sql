-- MediMatch AI — Migration 00009: Public Doctor View
-- Lets anonymous reads use the anon key, so RLS applies, without opening profiles again. The view
-- runs as its owner to reach doctors' names, so its columns are the whole of what it exposes.

CREATE OR REPLACE VIEW public.public_doctors
WITH (security_barrier = true) AS
SELECT
    d.id,
    p.full_name,
    d.bio,
    d.qualifications,
    d.years_experience,
    d.consultation_fee,
    d.clinic_name,
    d.city,
    d.verification_status,
    d.created_at
FROM public.doctor_profiles d
JOIN public.profiles p ON p.id = d.user_id
WHERE d.verification_status = 'approved';

REVOKE ALL ON public.public_doctors FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.public_doctors TO anon, authenticated, service_role;
