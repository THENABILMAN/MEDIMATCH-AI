-- MediMatch AI — Migration 00011: Conversation State
-- Keeps the assistant's progress with the conversation, so it survives restarts, works across
-- workers, and is erased with the conversation.

ALTER TABLE public.conversations
    ADD COLUMN IF NOT EXISTS graph_state JSONB NOT NULL DEFAULT '{}'::jsonb;
