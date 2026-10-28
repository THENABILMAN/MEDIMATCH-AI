# MediMatch AI — Project Implementation Plan

MediMatch AI is an AI-powered doctor recommendation and appointment booking platform. It matches patients with verified, suitable doctors through conversational symptom exploration, hybrid semantic retrieval, and verified booking schedules.

---

## 6-Phase Roadmap

### Phase 1: Foundation, Database Architecture & Security
- Initialize backend project layout with FastAPI and strict configuration management.
- Design Supabase PostgreSQL schema with migrations (`supabase/migrations/`):
  - `profiles` (User base info, roles: `patient`, `doctor`, `admin`)
  - `doctors` (Specialties, qualifications, experience, consultation fees, clinic locations, `verification_status`: `pending`, `approved`, `rejected`)
  - `appointments` (Patient reference, doctor reference, slot times, status)
- Implement Row-Level Security (RLS) on all tables with least-privilege policies.
- Set up admin approval workflow ensuring unapproved doctors cannot be queried.

### Phase 2: Doctor Catalog, Embeddings & Vector Indexing
- Build doctor profile management endpoints (FastAPI).
- Implement embedding generation pipeline using configured embedding provider (`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`).
- Set up Pinecone vector search index for semantic symptom-to-specialty matching.
- Implement background synchronization worker to keep Supabase doctor profiles and Pinecone embeddings synchronized.
- *Strict Rule*: Supabase Postgres is the single source of truth; Pinecone acts solely as a semantic index.

### Phase 3: Safety Guardrails & AI Symptom Assistant
- **Rule-Based Emergency Triage**:
  - Implement deterministic keyword and regex checks for red-flag symptoms (e.g., chest pain, severe shortness of breath, sudden numbness, uncontrolled bleeding).
  - Immediate emergency alert prompt directing patient to emergency care before any LLM invocation.
- **LangGraph Conversational Assistant**:
  - Multi-turn symptom clarifying questions powered by OpenRouter LLM.
  - Strict medical safety guardrails: The assistant must NEVER diagnose, prescribe, or claim symptoms are benign.
  - Privacy guardrail: Strip all Personally Identifiable Information (PII: names, phone numbers, emails) before sending queries to external LLMs/embeddings.

### Phase 4: Hybrid Search & Appointment Booking Engine
- Implement hybrid retrieval algorithm:
  - Vector similarity query on Pinecone to find candidate specialties and doctor profiles.
  - Re-fetch records directly from Supabase Postgres with filters: `verification_status = 'approved'`, location, fee range, and real-time availability.
- Implement appointment scheduling:
  - Doctor slot definitions and recurring availability.
  - Concurrency-safe slot reservation to prevent double-booking.

### Phase 5: Web Frontend (React + TypeScript + Vite)
- Patient Portal: Interactive symptom chat, doctor comparison cards, booking interface.
- Doctor Portal: Profile credential management, availability scheduler, appointment tracker.
- Admin Portal: Doctor verification approval/rejection panel, platform audits.
- Safe client configuration (no service-role or private keys exposed).

### Phase 6: Mobile App (Flutter) & Production Deployment
- Flutter cross-platform client (Android & iOS) for patients and doctors.
- Push notifications for booking reminders and status changes.
- End-to-end integration testing across FastAPI, Supabase, Pinecone, and OpenRouter.
- Production readiness: rate limiting, audit logging, monitoring, and CI/CD pipelines.

