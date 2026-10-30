# CLAUDE.md — MediMatch AI Development Guidelines

## Project Summary
MediMatch AI is an AI-powered doctor recommendation and appointment booking platform designed to connect patients with verified medical specialists. Patients can describe symptoms naturally to an intelligent conversational assistant, which clarifies details safely and guides them to appropriate doctors. The system leverages hybrid semantic search with Pinecone and Supabase PostgreSQL to offer verified doctor comparisons, live scheduling, and seamless booking across web and mobile platforms.

---

## Technology Stack
- **Backend API**: FastAPI (Python 3.12+)
- **Database & Auth**: Supabase (PostgreSQL, Supabase Auth, Row-Level Security)
- **Vector Search Index**: Pinecone
- **AI Orchestration & LLM**: LangGraph, OpenRouter
- **Web Frontend**: React + TypeScript (Vite)
- **Mobile Frontend**: Flutter (Dart)

---

## Repository Layout
```text
MEDIMATCH-AI/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, security, logging
│   │   ├── api/            # API routes and endpoints
│   │   ├── models/         # Pydantic schemas and database models
│   │   ├── services/       # AI triage, LangGraph agent, search, bookings
│   │   └── main.py         # Application entry point & /health endpoint
│   ├── tests/              # Pytest test suite
│   ├── pyproject.toml      # Python dependencies and build config
│   └── requirements.txt    # Frozen / pinned dependencies
├── web/                    # React + TypeScript frontend (Vite)
├── mobile/                 # Flutter mobile application
├── supabase/
│   └── migrations/         # Supabase SQL schema migrations and RLS policies
├── docs/                   # Documentation, specifications, and architecture plans
├── .env.example            # Canonical environment variable reference
├── CLAUDE.md               # Project instructions and status tracking
└── README.md               # Developer onboarding and runbook
```

---

## Non-Negotiable Rules
1. **Source of Truth**: Supabase Postgres is the single source of truth. Pinecone is exclusively a search index; always re-fetch current doctor records directly from Supabase before returning results to clients.
2. **Secret Isolation**: Never expose service-role keys, Pinecone API keys, or OpenRouter keys to any frontend (Web or Mobile). All credentials must be kept strictly on the backend and loaded via environment variables.
3. **Medical Safety**: The AI assistant must never diagnose, prescribe treatments, or reassure patients that serious symptoms are harmless. It only helps find suitable, qualified doctors.
4. **Deterministic Emergency Triage**: Emergency detection must be rule-based (deterministic keyword and regex checks backed by comprehensive tests), never delegated solely to an LLM.
5. **Doctor Verification Enforcement**: Only doctors with `verification_status = 'approved'` may ever be recommended or searchable by patients.
6. **Row-Level Security (RLS)**: Every table containing user data must have RLS enabled with strict least-privilege policies.
7. **Privacy Preservation**: Minimize personal data sent to LLM/embedding providers; never send patient names, phone numbers, email addresses, or identifying credentials.

---

## Conventions
- **Code Quality**: Strict Python type hints everywhere, Pydantic v2 models for data validation and configuration (`pydantic-settings`).
- **Formatting & Linting**: Ruff for linting and code formatting; follow PEP 8 standards.
- **Testing**: Write unit and integration tests with `pytest`. Ensure high test coverage for safety rules and authorization checks before committing.
- **Git Commits**: Small, atomic commits with clear imperative messages (e.g., `feat: add rule-based emergency triage`, `fix: enforce approved status in search query`).
- **Folder Names**: Lowercase with underscores (`snake_case`) for Python packages/modules; `kebab-case` for docs and non-code folders.

---

## Commands

### Backend
```bash
# Install dependencies
python -m pip install -r backend/requirements.txt

# Run migrations against Supabase database
python backend/app/run_migrations.py

# Seed specialties, 10 demo doctors, and 3 test accounts
python backend/scripts/seed.py

# Run development server
python -m uvicorn backend.app.main:app --reload --port 8000

# Run interactive AI symptom assistant terminal CLI
python backend/scripts/chat_cli.py

# Verify / setup Pinecone serverless index
python backend/scripts/setup_pinecone_index.py

# Rebuild entire vector index from Supabase PostgreSQL (idempotent)
python backend/scripts/reindex_all.py

# Run recommendation evaluation benchmark (Precision@3)
python backend/scripts/eval_recommendations.py

# Run all test suites
python -m pytest backend/tests/ -v

# Run formatting & linting
ruff check backend/
ruff format backend/
```

### Web
```bash
cd web
npm install
npm run dev
npm run build
```

### Mobile
```bash
cd mobile
flutter pub get
flutter run
```

---

## Current Status

- [x] **Phase 1: Foundation, Database Architecture & Security**
  - Supabase schema migrations: `profiles`, `specialties`, `doctor_profiles`, `doctor_specialties`, `availability_slots`, `appointments`, `conversations`, `messages`, `patient_symptom_sessions`, `audit_logs`
  - Trigger on `auth.users` creating `profiles` row with role default `patient` and admin escalation prevention
  - Row-Level Security (RLS) policies on every table with least-privilege access
  - FastAPI JWT verification, `get_current_user`, and `require_role(...)` dependencies
  - Endpoints: `GET /health`, `POST /auth/register-patient`, `POST /auth/register-doctor`, `POST /auth/login`, `GET /me`, `PATCH /me`
  - 14/14 automated tests passing (RBAC, unauthenticated 401, role-escalation prevention, PostgreSQL RLS isolation)
- [x] **Phase 2: Doctor Profiles, Admin Verification & Public Search**
  - Migration `00003_doctor_credentials_and_storage.sql`: `doctor_credentials` table, RLS, and private Supabase storage bucket `doctor-credentials`
  - Doctor endpoints (`/doctors/me/profile`, `/doctors/me/credentials`) with automatic status reset to `pending` upon material profile edits
  - Admin endpoints (`/admin/doctors?status=pending`, `/admin/doctors/{id}/approve`, `/reject`, `/suspend` with reason tracking)
  - Paginated admin audit logs (`/admin/audit-logs`) and full CRUD for medical specialties (`/admin/specialties`)
  - Anonymous-safe public search (`GET /doctors/search`, `GET /doctors/{id}`) enforcing `verification_status = 'approved'` and sanitizing private fields
  - Lifecycle event hooks in `app/services/doctor_events.py` (`on_doctor_approved`, `on_doctor_updated`, `on_doctor_suspended`)
  - Deterministic seed script (`backend/scripts/seed.py`) with 3 specialties, 10 Bangladesh demo doctors, and 3 test accounts
  - 31/31 automated tests passing across RBAC, public search filters, admin approvals, and RLS
- [x] **Phase 3: Safety Guardrails & AI Symptom Assistant**
  - Externalized rule-based emergency detection in `backend/app/ai/data/emergency_patterns.json` covering 6 clinical categories in English, Bengali script, and transliterated Banglish
  - Deterministic safety triage node short-circuiting the graph immediately on emergency detection, returning a 999 escalation alert with zero doctor recommendations
  - Output guard sanitizing any unauthorized diagnosis claims or drug prescription phrasing from LLM responses
  - PII redaction layer (`privacy.py`) masking patient names, phone numbers (BD + international), and emails before submitting prompts to external LLMs
  - LangGraph conversational workflow (`graph.py`) with typed state, single-question follow-ups bounded at max 3 rounds, and verified DB specialty mapping with General Medicine fallback
  - PostgreSQL-backed checkpointer (`MemorySaver` / `PostgresSaver`) maintaining conversational state across dialogue turns
  - Patient chat API (`POST /chat/conversations`, `POST /chat/conversations/{id}/messages`, `GET /chat/conversations/{id}`) enforcing strict patient ownership and mandatory medical disclaimer
  - Interactive terminal CLI (`backend/scripts/chat_cli.py`) for live triage testing
  - 101/101 automated tests passing across the repository (including 32 emergency test cases, 21 non-emergency test cases, output guard tests, workflow scripted tests, and patient isolation tests)
- [x] **Phase 4: Hybrid Search & Appointment Booking Engine**
  - Migration `00004_doctor_sync_status.sql` adding `sync_status` and `last_synced_at` columns
  - Embedding provider abstraction (`BaseEmbeddingProvider`) implementing Pinecone Inference API (`llama-text-embed-v2`, 1024-dim, cosine metric) and deterministic `FakeEmbeddingProvider` for unit tests
  - Script `backend/scripts/setup_pinecone_index.py` verifying and setting up serverless Pinecone index
  - Doctor document builder (`builder.py`) indexing specialties, bio, qualifications, and city while strictly omitting PII, names, and fees
  - Vector sync pipeline (`sync.py`) wired into lifecycle hooks (`on_doctor_approved`, `on_doctor_updated`, `on_doctor_suspended`, `on_doctor_rejected`)
  - Full idempotent reindex script (`reindex_all.py`) synchronizing all approved doctors
  - Hybrid recommendation engine (`recommend.py`) combining Pinecone semantic vector similarity with Supabase verification, budget limits, and future availability slots, with transparent multi-factor scoring and graceful SQL fallback
  - Direct recommendation endpoint `POST /recommendations` (and `/api/v1/recommendations`) and automatic recommendation cards formatted into chat consultation responses
  - Evaluation benchmark (`eval_recommendations.py`) scoring 100% Precision@3 across 20 clinical queries
  - 112/112 automated tests passing across the repository
- [x] **Phase 5: Appointments Engine & Web Application**
  - **Part A (Backend Appointments & Concurrency)**:
    - Migration `00005_appointments_concurrency.sql`: `btree_gist` slot overlap exclusion constraint `no_overlapping_slots`, partial unique constraint `idx_appointments_slot_booked`, and atomic stored procedure `book_appointment_atomic` with pessimistic row locking
    - Doctor slot endpoints (`POST /doctors/me/slots`, `GET /doctors/me/slots`, `DELETE /doctors/me/slots/{id}`, `GET /doctors/{id}/slots`) with overlap check and minimum 15-minute duration validation
    - Appointment endpoints (`POST /appointments`, `GET /appointments/me`, `POST /appointments/{id}/cancel`, `POST /appointments/{id}/complete`)
    - Audit log recording for appointment cancellations with reason tracking
    - 121/121 automated backend tests passing across the repository, including 20-thread simultaneous booking race condition test
  - **Part B (React + TypeScript Web Application)**:
    - Initialized React 19 + TypeScript + Vite 8 in `web/` with Tailwind CSS v4, Lucide icons, TanStack React Query, and Supabase JS Client using strictly public `anon` credentials
    - Authentication system with role selection (Patient / Doctor), role-based route protection (`ProtectedRoute`), fast demo-account login helpers, and session management
    - Patient Portal: AI Symptom Chat with persistent medical disclaimer, prominent red emergency escalation with 999 hotline CTA, live doctor recommendation cards with clinical match scores, specialist directory search with multi-filters, doctor detail page with live slot picker, and "My Appointments" with slot-freeing cancellations
    - Doctor Portal: Clinical profile management with specialty selector, BMDC/diploma credential document uploads, verification status badge, availability slot manager (with 15-min and overlap safeguards), and appointment management (complete / cancel)
    - Admin Dashboard: Doctor verification queue with credential preview and approve/reject/suspend actions, medical specialties CRUD, and real-time paginated audit logs table
    - Comprehensive test coverage: 8/8 Vitest + React Testing Library component tests passing (auth guards, booking flow, chat component) and Playwright E2E spec (`patient-flow.spec.ts`)
- [ ] **Phase 6: Mobile App & Production Deployment**
  - Flutter app for Patient and Doctor workflows
  - End-to-end integration test suite & deployment readiness

---

## Decisions Log
- **2026-10-28**: Repository initialized with skeleton structure, `/health` endpoint, Pydantic Settings configuration, comprehensive `.gitignore`, and `.env.example`.
- **2026-10-28**: Adopted hybrid search strategy: Pinecone provides semantic specialty/service similarity, Supabase PostgreSQL acts as authoritative store for verification and availability filtering.
- **2026-10-28**: Enforced immutable audit logs where inserts are restricted to backend service-role and reads restricted to administrators.
- **2026-10-28**: Implemented strict schema level (`extra="forbid"`) and trigger level guards preventing any user from self-escalating role to `admin` or self-approving `verification_status`.
- **2026-10-28**: Designed public doctor search (`/doctors/search` and `/doctors/{id}`) to be anonymous-safe (accessible without authentication) to minimize patient onboarding friction, strictly filtering for `verification_status = 'approved'` and never exposing credential paths or personal phone numbers.
- **2026-10-28**: Any material modification to a doctor profile by a doctor automatically resets status to `pending`, logs a `DOCTOR_MATERIAL_PROFILE_UPDATE` audit event, and fires `on_doctor_updated`.
- **2026-10-28**: Added doctor lifecycle event hooks in `app/services/doctor_events.py` for future Pinecone vector index synchronization.
- **2026-10-29**: Rule-based emergency detection patterns are externalized in JSON (`backend/app/ai/data/emergency_patterns.json`) rather than hardcoded in Python, enabling clinicians and administrators to review and update triage regexes without code changes.
- **2026-10-29**: Emergency detection completely bypasses LLM invocation; emergency turns immediately output a deterministic non-LLM message advising 999/hospital contact with zero doctor recommendations.
- **2026-10-29**: Output guard checks LLM replies against diagnostic phrasing ("you have pneumonia", "diagnosis:") and prescriptive dosing ("take 500mg amoxicillin") and substitutes safe non-diagnostic advisory text.
- **2026-10-29**: LangGraph `check_missing` logic is implemented in pure Python (deterministic), not LLM, asking at most 3 clarifying follow-up questions before falling back to General Medicine and default city Dhaka.
- **2026-10-29**: Privacy redaction runs prior to any LLM prompt serialization, substituting detected names, Bangladeshi/international phone numbers, and emails with redaction tokens.
- **2026-10-30**: Selected Pinecone Inference API with `llama-text-embed-v2` (1024-dim, cosine similarity) as primary embedding provider, leveraging existing `PINECONE_API_KEY` without requiring additional third-party embedding subscriptions.
- **2026-10-30**: Designed doctor document builder to index strictly clinical fields (specialties, clinical bio, qualifications, city, clinic) while deliberately omitting personal names, phone numbers, and fees to prevent demographic and fee bias in vector space.
- **2026-10-30**: Configured multi-factor scoring formula: $Score = 0.40 \cdot S_{\text{vector}} + 0.25 \cdot S_{\text{specialty}} + 0.15 \cdot S_{\text{experience}} + 0.10 \cdot S_{\text{fee}} + 0.10 \cdot S_{\text{availability}}$, with all weights externalized in `Settings`.
- **2026-10-30**: Enforced strict single source of truth in PostgreSQL: any stale or invalid vector returned by Pinecone is discarded if the doctor is not approved in Supabase, exceeds consultation fee budget, or possesses zero upcoming availability slots.
- **2026-10-30**: Built automatic SQL fallback mode if Pinecone returns fewer than 3 qualifying candidates or encounters an outage, guaranteeing zero-downtime recommendation responses.
- **2026-10-30**: Enforced zero double-booking via database-level pessimistic row locking in PostgreSQL (`SELECT ... FOR UPDATE` inside `book_appointment_atomic`) combined with a partial unique constraint (`idx_appointments_slot_booked WHERE status = 'booked'`).
- **2026-10-30**: Enforced temporal slot integrity via PostgreSQL exclusion constraint (`no_overlapping_slots` using `btree_gist`) and application-level 15-minute minimum duration and future timestamp checks.
- **2026-10-30**: Verified booking atomicity under high concurrency with a 20-thread simultaneous race test guaranteeing exactly 1 success (201) and 19 conflicts (409).
- **2026-10-30**: Enforced strict separation of frontend keys in `web/.env.example`: frontend holds exclusively `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`, communicating with backend API using Supabase JWT tokens; backend never exposes service-role, Pinecone, or OpenRouter keys to client code.
- **2026-10-30**: Designed patient triage chat UI to surface medical safety warnings as permanent prominent disclaimers and render emergency escalations as high-urgency red alerts with direct 999 toll-free dialers.
- **2026-10-30**: Integrated specialist recommendations directly into chat turns with match explanation snippets, match score percentage badges, and direct links to live slot booking.




