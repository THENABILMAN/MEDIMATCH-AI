-- MediMatch AI — Migration 00004: Doctor Profile Vector Sync Status
-- Tracks vector synchronization state between Supabase and Pinecone.

ALTER TABLE public.doctor_profiles
ADD COLUMN IF NOT EXISTS sync_status TEXT NOT NULL DEFAULT 'pending' CHECK (sync_status IN ('pending', 'synced', 'failed')),
ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_doctor_profiles_sync_status ON public.doctor_profiles(sync_status);

