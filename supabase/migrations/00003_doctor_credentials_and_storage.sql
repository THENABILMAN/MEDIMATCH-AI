-- MediMatch AI — Migration 00003: Doctor Credentials Table & Storage Setup
-- Allows verified credential document uploads to private Supabase Storage.

-- ==============================================================================
-- 1. Doctor Credentials Table
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.doctor_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES public.doctor_profiles(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    document_type TEXT NOT NULL, -- e.g., 'bmdc_license', 'degree_certificate', 'nid_passport'
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_doctor_credentials_doctor_id ON public.doctor_credentials(doctor_id);

-- ==============================================================================
-- 2. Enable Row-Level Security on doctor_credentials
-- ==============================================================================
ALTER TABLE public.doctor_credentials ENABLE ROW LEVEL SECURITY;

-- Doctors can view only their own uploaded credentials; Admins can view all credentials
DROP POLICY IF EXISTS "doctor_credentials_select_parties" ON public.doctor_credentials;
CREATE POLICY "doctor_credentials_select_parties" ON public.doctor_credentials
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = doctor_credentials.doctor_id AND dp.user_id = auth.uid()
        )
        OR public.is_admin()
    );

-- Doctors can insert credentials for their own profile; Admins can also insert
DROP POLICY IF EXISTS "doctor_credentials_insert_own" ON public.doctor_credentials;
CREATE POLICY "doctor_credentials_insert_own" ON public.doctor_credentials
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = doctor_credentials.doctor_id AND dp.user_id = auth.uid()
        )
        OR public.is_admin()
    );

-- Doctors can delete their own credentials; Admins can delete any
DROP POLICY IF EXISTS "doctor_credentials_delete_own" ON public.doctor_credentials;
CREATE POLICY "doctor_credentials_delete_own" ON public.doctor_credentials
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM public.doctor_profiles dp
            WHERE dp.id = doctor_credentials.doctor_id AND dp.user_id = auth.uid()
        )
        OR public.is_admin()
    );

-- ==============================================================================
-- 3. Storage Bucket Configuration (Private)
-- ==============================================================================
-- Ensure the storage schema and bucket exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'storage') THEN
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'doctor-credentials',
            'doctor-credentials',
            false,
            10485760, -- 10MB limit
            ARRAY['image/png', 'image/jpeg', 'image/webp', 'application/pdf']
        )
        ON CONFLICT (id) DO UPDATE SET public = false;
    END IF;
END $$;

