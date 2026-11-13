-- MediMatch AI — Migration 00015: Directory Doctors
-- Doctors listed from a public directory have no MediMatch account, and MediMatch has not checked
-- their credentials. They carry listing_source = 'directory' and patients are told so. Their fee,
-- experience and city can be unknown, and unknown stays NULL rather than a guess.

-- ==============================================================================
-- 1. Listings Without an Account
-- ==============================================================================
ALTER TABLE public.doctor_profiles ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE public.doctor_profiles ALTER COLUMN years_experience DROP NOT NULL;
ALTER TABLE public.doctor_profiles ALTER COLUMN consultation_fee DROP NOT NULL;
ALTER TABLE public.doctor_profiles ALTER COLUMN city DROP NOT NULL;

ALTER TABLE public.doctor_profiles
    ADD COLUMN IF NOT EXISTS listing_source TEXT NOT NULL DEFAULT 'registered',
    ADD COLUMN IF NOT EXISTS listed_name TEXT,
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS bmdc_number TEXT,
    ADD COLUMN IF NOT EXISTS designation TEXT,
    ADD COLUMN IF NOT EXISTS specialty_text TEXT;

ALTER TABLE public.doctor_profiles DROP CONSTRAINT IF EXISTS doctor_listing_source_valid;
ALTER TABLE public.doctor_profiles ADD CONSTRAINT doctor_listing_source_valid CHECK (
    (listing_source = 'registered' AND user_id IS NOT NULL)
    OR (listing_source = 'directory' AND user_id IS NULL AND listed_name IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_doctor_profiles_source_url
    ON public.doctor_profiles(source_url) WHERE source_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_doctor_profiles_status_city
    ON public.doctor_profiles(verification_status, city);
CREATE INDEX IF NOT EXISTS idx_doctor_specialties_specialty
    ON public.doctor_specialties(specialty_id);

-- ==============================================================================
-- 2. Public View
-- ==============================================================================
-- A directory doctor's name lives on the listing, a registered doctor's on their profile
DROP VIEW IF EXISTS public.public_doctors;
CREATE VIEW public.public_doctors
WITH (security_barrier = true) AS
SELECT
    d.id,
    COALESCE(p.full_name, d.listed_name) AS full_name,
    d.bio,
    d.qualifications,
    d.years_experience,
    d.consultation_fee,
    d.clinic_name,
    d.city,
    d.verification_status,
    d.created_at,
    d.listing_source,
    d.source_url,
    d.bmdc_number,
    d.designation,
    d.specialty_text
FROM public.doctor_profiles d
LEFT JOIN public.profiles p ON p.id = d.user_id
WHERE d.verification_status = 'approved';

REVOKE ALL ON public.public_doctors FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.public_doctors TO anon, authenticated, service_role;

-- The assistant reads the cities with doctors on every turn, so it asks for the short list
CREATE OR REPLACE VIEW public.doctor_cities
WITH (security_barrier = true) AS
SELECT DISTINCT city
FROM public.doctor_profiles
WHERE verification_status = 'approved' AND city IS NOT NULL;

REVOKE ALL ON public.doctor_cities FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.doctor_cities TO anon, authenticated, service_role;

-- ==============================================================================
-- 3. Specialties
-- ==============================================================================
-- Fixed ids, matching backend/scripts/directory_rules.py by name. Existing names are left as they are
INSERT INTO public.specialties (id, name, description)
VALUES
    ('11111111-0000-0000-0000-000000000007', 'Gynecology & Obstetrics', 'Women''s health, pregnancy, childbirth and fertility.'),
    ('11111111-0000-0000-0000-000000000008', 'Pediatrics', 'Health of newborns, children and teenagers.'),
    ('11111111-0000-0000-0000-000000000009', 'Pediatric Surgery', 'Surgery for babies and children.'),
    ('11111111-0000-0000-0000-000000000010', 'ENT', 'Ear, nose, throat, head and neck.'),
    ('11111111-0000-0000-0000-000000000011', 'Ophthalmology', 'Eyes and vision.'),
    ('11111111-0000-0000-0000-000000000012', 'Dentistry', 'Teeth, gums, mouth and jaw.'),
    ('11111111-0000-0000-0000-000000000013', 'Dermatology', 'Skin, hair, nails, allergies of the skin and sexually transmitted infections.'),
    ('11111111-0000-0000-0000-000000000014', 'Cardiac & Vascular Surgery', 'Surgery of the heart, chest and blood vessels.'),
    ('11111111-0000-0000-0000-000000000015', 'Neurosurgery', 'Surgery of the brain, spine and nerves.'),
    ('11111111-0000-0000-0000-000000000016', 'Orthopedics', 'Bones, joints, fractures and injuries.'),
    ('11111111-0000-0000-0000-000000000017', 'Physical Medicine & Rehabilitation', 'Pain, movement problems and recovery after illness or injury.'),
    ('11111111-0000-0000-0000-000000000018', 'Rheumatology', 'Arthritis and other joint and immune conditions.'),
    ('11111111-0000-0000-0000-000000000019', 'Urology', 'Kidneys, bladder, urinary system and men''s reproductive health.'),
    ('11111111-0000-0000-0000-000000000020', 'Nephrology', 'Kidney diseases and dialysis.'),
    ('11111111-0000-0000-0000-000000000021', 'Gastroenterology & Hepatology', 'Stomach, intestines, liver and digestion.'),
    ('11111111-0000-0000-0000-000000000022', 'Endocrinology', 'Diabetes, thyroid and hormones.'),
    ('11111111-0000-0000-0000-000000000023', 'Pulmonology', 'Lungs, breathing and chest diseases.'),
    ('11111111-0000-0000-0000-000000000024', 'Oncology', 'Cancer care.'),
    ('11111111-0000-0000-0000-000000000025', 'Hematology', 'Blood disorders.'),
    ('11111111-0000-0000-0000-000000000026', 'Plastic Surgery', 'Burns, reconstruction and plastic surgery.'),
    ('11111111-0000-0000-0000-000000000027', 'General Surgery', 'Operations on the abdomen and other general surgery.'),
    ('11111111-0000-0000-0000-000000000028', 'Nutrition', 'Diet and nutrition.')
ON CONFLICT (name) DO NOTHING;
