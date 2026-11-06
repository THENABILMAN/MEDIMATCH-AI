# CLAUDE.md — MediMatch AI Development Guidelines

## Project Summary
MediMatch AI is an AI-powered doctor recommendation and appointment booking platform designed to connect patients with verified medical specialists. Patients can describe symptoms naturally to an intelligent conversational assistant, which clarifies details safely and guides them to appropriate doctors. The system leverages hybrid semantic search with Pinecone and Supabase PostgreSQL to offer verified doctor comparisons, live scheduling, and seamless booking across web and mobile platforms.

---

## Technology Stack
- **Backend API**: FastAPI (Python 3.12+)
- **Database & Auth**: Supabase (PostgreSQL, Supabase Auth, Row-Level Security)
- **Vector Search Index**: Pinecone
- **AI Orchestration & LLM**: LangGraph, Groq
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
│   │   ├── ai/             # Safety rules, LangGraph assistant, routing, prompts, LLM client, privacy
│   │   ├── models/         # Enums
│   │   ├── schemas/        # Pydantic request and response models
│   │   ├── search/         # Embeddings, Pinecone sync, recommendations
│   │   ├── services/       # Business logic for each route group
│   │   ├── run_migrations.py # Applies and tracks SQL migrations
│   │   └── main.py         # Application entry point
│   ├── scripts/            # Seed, reindex, evals, purge, end-to-end check
│   ├── tests/              # Pytest test suite
│   ├── pyproject.toml      # Python dependencies and build config
│   ├── requirements.txt    # Pinned runtime dependencies
│   └── requirements-dev.txt # Pinned development dependencies
├── web/                    # React + TypeScript frontend (Vite)
├── supabase/
│   └── migrations/         # Supabase SQL schema migrations and RLS policies
├── docs/                   # Design, deployment, privacy, audit, security and eval reports
├── .env.example            # Canonical environment variable reference
├── CLAUDE.md               # Project instructions and status tracking
└── README.md               # Developer onboarding and runbook
```

---

## Non-Negotiable Rules
1. **Source of Truth**: Supabase Postgres is the single source of truth. Pinecone is exclusively a search index; always re-fetch current doctor records directly from Supabase before returning results to clients.
2. **Secret Isolation**: Never expose service-role keys, Pinecone API keys, or Groq keys to any frontend (Web or Mobile). All credentials must be kept strictly on the backend and loaded via environment variables.
3. **Medical Safety**: The AI assistant must never diagnose, prescribe treatments, or reassure patients that serious symptoms are harmless. It only helps find suitable, qualified doctors.
4. **Deterministic Emergency Triage**: Emergency detection must be rule-based (deterministic keyword and regex checks backed by comprehensive tests), never delegated solely to an LLM.
5. **Doctor Verification Enforcement**: Only doctors with `verification_status = 'approved'` may ever be recommended or searchable by patients.
6. **Row-Level Security (RLS)**: Every table containing user data must have RLS enabled with strict least-privilege policies.
7. **Privacy Preservation**: Minimize personal data sent to LLM/embedding providers; never send patient names, phone numbers, email addresses, or identifying credentials.
8. **Defense in Depth**: Every route enforces auth and role checks, and RLS guards the same data. Rely on neither alone. Clients never write directly: the API is the only writer.
9. **Model Writes the Conversation**: The LLM writes every normal reply, in the patient's language, with no templates or keyword lists. Emergency and crisis messages stay fixed and rule-checked first, the model can add an alert but never remove one, and every reply passes the output guard. Stopping, searching and safety are decided in Python, not by the model.
10. **Honest About Being an AI**: The assistant never claims feelings, a body or a human life. Warmth comes from attention and language. It is a guide to human help, not a therapist or a friend.

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
python -m pip install -r backend/requirements-dev.txt   # Python 3.12. requirements.txt is runtime only

# Start local Supabase (needs Docker), or rebuild it from zero
npx supabase@latest start
npx supabase@latest db reset

# Apply pending migrations to DATABASE_URL. A database with no history needs --baseline once
python backend/app/run_migrations.py

# Seed demo data. --with-logins sets demo passwords and only works on a local database
python backend/scripts/seed.py --with-logins

# Run development server
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Run interactive AI symptom assistant terminal CLI
python backend/scripts/chat_cli.py

# Verify / setup Pinecone serverless index
python backend/scripts/setup_pinecone_index.py

# Rebuild the vector index, or only retry failed doctors
python backend/scripts/reindex_all.py
python backend/scripts/reindex_all.py --unsynced

# Erase chats past the retention period. Run daily
python backend/scripts/purge_expired.py

# Charge this month's doctor subscriptions. Run daily, each month is charged once
python backend/scripts/bill_subscriptions.py

# Run all tests. They use local Supabase only and refuse any other host
cd backend && python -m pytest tests -q

# Run tests that need no database
cd backend && python -m pytest tests -q -m "not integration"

# Evaluations. These call real services, so they are opt-in
python backend/scripts/eval_recommendations.py
python backend/scripts/eval_emergency.py
python backend/scripts/eval_conversation.py   # Takes several days on the Groq limit, and resumes

# Whole journey against a running local API, with real Pinecone and LLM
python backend/scripts/e2e_check.py --api http://127.0.0.1:8010

# Lint, format and types
ruff check backend/
ruff format backend/
cd backend && mypy app
```

### Web
```bash
cd web
npm install
npm run dev
npm run build
npm test                 # Vitest
npx playwright test      # Mocked API. Writes web/screenshots/after/
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
  - Assistant progress is saved in `conversations.graph_state`, so it survives restarts, works across workers and is erased with the conversation
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
  - Evaluation benchmark (`eval_recommendations.py`): that first version scored 100% only because it passed the answer in. See `docs/EVAL_REPORT.md`
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
- [x] **Phase 5b: Web UI Rebuild**
  - Design system in `docs/DESIGN.md`, tokens in `web/src/styles/tokens.css`, rules in `docs/UI_PRINCIPLES.md`
  - Primitives on Radix with cva in `web/src/components/ui/`, domain components in `web/src/components/domain/`; all copy in `web/src/locales/en.json`
  - Patient, doctor and admin portals rebuilt, with URL-synced state and designed loading, empty and error states
  - Backend additions: credential links, verification history, admin patients, consent, chat history erasure, patient anonymization; migrations `00006` and `00007`
  - Tests: 44 Vitest, 95 Playwright on a mocked API covering every screen at 3 sizes with axe, keyboard paths, offline and slow network, and critical journeys
- [x] **Phase 5c: Backend Audit and Hardening**
  - `docs/AUDIT.md` records the state before, `docs/SECURITY_REPORT.md` after, and `docs/EVAL_REPORT.md` what was measured
  - Tests run on local Supabase only
  - Emergency detection is rules plus the model, which can only add alerts. The model writes normal replies
  - All 14 migrations are applied to the live project, and vector search is on with 7 approved doctors indexed
- [x] **Phase 5d: Web Redesign**
  - `docs/UI_AUDIT.md` records the state before, `docs/UI_REVIEW.md` the review, and `docs/DESIGN.md` the system
  - Teal and violet tokens on a light palette, Instrument Sans and Source Serif. All photographs are gone, and the Imagery section of `docs/DESIGN.md` keeps them out
  - The home page is a split stage: `ProductStage` plays the chat on scroll with live doctors and holds no inputs or buttons. The one real message box sends a first message to the chat
  - Language switch added. Most of the interface is still English, because Bangla copy needs a reviewer
  - Tests: 44 Vitest and 97 Playwright passing on a mocked API
  - The assistant runs on Groq and was tried in real English, Bangla and Banglish conversations. The full emergency evaluation was measured on the earlier model. A spot check on Groq flagged 12 of 14 emergencies and 0 of 8 ordinary messages
- [x] **Phase 5g: Business Model**
  - Free for patients, paid by doctors. Each doctor chooses a fee per completed appointment or a monthly subscription
  - Migration `00014` adds `billing_settings`, `doctor_billing_plans` and `billing_charges`. It is applied to the live project
  - Prices are unset, so nothing is charged. An admin sets them at `/admin/billing`. This records what is owed: no money moves through the app
  - Routes: `GET /billing/pricing`, `GET /billing/me`, `PUT /billing/me/plan`, and `/admin/billing/pricing` and `/admin/billing/charges`. Web: `/for-doctors`, `/doctor/billing`, `/admin/billing`
  - The hospitals plan and go-to-market steps stay off the site, on the owner's decision
  - All 1066 backend tests pass on local Supabase, the first full run since Phase 5e. 53 Vitest and 128 Playwright pass on a mocked API
- [x] **Phase 5f: Landing Page Design System**
  - The whole web app follows the landing page design skill: Manrope only, named text styles, the fixed spacing table, Tailwind radii, Phosphor icons, one motion curve, sentence case and no hyphens in copy. `web/tests/design-rules.test.ts` enforces this
  - The home page was rebuilt: hero, problem, benefits, tagline reveal, how it works, live doctor register, FAQ with schema, risk reversal, final CTA, footer
  - Floating translucent navigation, full height mobile menu, `/privacy` and `/terms`. The legal wording needs a lawyer's review
  - Black and white palette, pill buttons and a white hero card. See `design-system/source/report.md`
- [x] **Phase 5e: Assistant Personality and Routing**
  - Each turn is a hidden analysis, Python decisions in `backend/app/ai/routing.py`, then a reply written from `backend/app/ai/prompts/persona.md`
  - One question at a time with no fixed cap, a soft limit of 12, and stopping once the top specialty is clearly ahead, urgency is known and the city is known
  - Ambiguous phrases such as "broken heart" get a clarifying question before routing. A physical answer about the chest gets the fixed alert
  - Psychiatry, Clinical Psychology and Counselling added in migration `00013`, applied to the live project on 2026-11-06. No approved provider exists for them there yet, so those patients are told none were found
  - Self-harm has its own fixed message in `prompts/safety_messages.yaml`. It needs review by a mental-health professional and a native Bangla speaker. `CRISIS_HELPLINES` is empty until the owner verifies numbers
  - API changes are additive: `chips` and `safety_kind`. The web shows the assistant's chips, a calm `CrisisNotice` for self-harm, and "Show me doctors now"
  - `docs/CONVERSATION_EVAL.md` is incomplete: 2 of 45 scenarios ran before the Groq daily limit stopped it. Rules plus model recall on unseen phrases has not been measured
- [ ] **Phase 6: Mobile App & Production Deployment**
  - Flutter app for Patient and Doctor workflows
  - End-to-end integration test suite & deployment readiness

---

## Decisions Log
- **2026-11-06**: "Show me doctors now" is never offered after an alert or in a conversation that touched self-harm, so the app does not push a search at someone in crisis. The patient can still ask in words.
- **2026-11-06**: Form errors clear as they are corrected (`mode: 'onTouched'`). Clearing on blur moved the submit button under the click, and the click was lost.
- **2026-11-06**: Booking fees are charged when an appointment is completed, because booking has no confirmed step. A database trigger does it, so no path can skip it, and an appointment is charged once. Cancelled appointments cost nothing.
- **2026-11-06**: Choosing the subscription charges the current month at once, in full, so a doctor cannot leave the booking fee mid-month and pay nothing until the next run. Only approved doctors are charged a subscription. Not paying does not delist a doctor.
- **2026-11-06**: A charge keeps its amount, so a price change never rewrites what is owed. Marking a charge paid or waived cannot be undone in the app.
- **2026-11-06**: Replaced teal and violet with black and white on a grey page, pill buttons and a white hero card, on the owner's instruction. Colours were sampled from an image of the MyDNA concept by Levi Wilson, because it is not a live site. Its art is not used. Violet stays on AI content, sampled from that art, and red stays for emergencies.
- **2026-11-06**: Adopted the landing page design skill for all web UI on the owner's instruction. It replaces Instrument Sans and Source Serif with Manrope, Lucide with Phosphor, Title Case with sentence case, and lifts the old ban on glass for the navigation bar. Teal and violet stay, because the skill sets no light palette.
- **2026-11-06**: No testimonials or logos on the home page, because none exist and they are never invented. The live doctor register is the proof.
- **2026-11-05**: Replaced the 3 follow-up limit with confidence-based stopping and a soft limit of 12, on the owner's instruction.
- **2026-11-05**: "my heart hurts" and "heavy chest" alone no longer raise the alert, on the owner's decision, against advice, so the assistant can ask whether they are physical or emotional. The 999 instruction is no longer guaranteed on that turn. Any other danger sign, "heart pain", "hurts badly", and every plain chest phrase still alert. A clinician must review this.
- **2026-11-05**: "Show me doctors now" asks for the city once if it is unknown, then searches all of Bangladesh. Pressed after a clarifying question has been asked once, it searches even if the meaning stays unclear, and the reply must say to call 999 for chest pain.
- **2026-11-05**: The assistant searches strictly, so General Medicine appears only when routing chose it. `POST /recommendations` keeps general doctors, because that search is not routed.
- **2026-11-05**: Routing reasons live in `graph_state`, not `audit_logs`, because audit logs outlive chat deletion.
- **2026-11-05**: The Groq account allows 8,000 tokens a minute, 200,000 tokens a day and 1,000 requests a day. A message uses about 3,300 tokens, so about 60 messages a day. The analysis step keeps full reasoning because it is a safety net; only the writer uses low reasoning.
- **2026-11-05**: The assistant must have a city before any search, so patients aren't shown doctors they can't reach. A patient can say any city is fine. If the model tries to search without one, a second call asks for it, so the model still writes the reply.
- **2026-11-05**: Match reasons state the specialty and experience only. Fee and soonest time are already on the row.
- **2026-11-05**: Replaced the navy and beige work with the teal, violet and serif system on the owner's instruction, and removed every photograph. The striking look comes from large type and the real product, never from decoration.
- **2026-11-05**: Dropped the dark ink field on the owner's feedback, because it didn't match the rest of the site. Home and sign-in use the teal tint.
- **2026-11-05**: The first message from the home page travels in `sessionStorage`, not the URL, so symptoms stay out of browser history and logs.
- **2026-11-05**: Removed emoji from the emergency alert and the greeting on the owner's instruction. The wording is otherwise unchanged.
- **2026-11-05**: Removed tracked screenshots, `docs/PLAN.md`, `docs/UI_REVIEW.md`, an empty root lockfile, and the unused `lighthouse` and `user-event` packages.
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
- **2026-10-29**: LangGraph `check_missing` logic is implemented in pure Python (deterministic), not LLM, asking at most 3 clarifying follow-up questions before falling back to General Medicine and default city Dhaka. Replaced on 2026-11-05.
- **2026-10-29**: Privacy redaction runs prior to any LLM prompt serialization, substituting detected names, Bangladeshi/international phone numbers, and emails with redaction tokens.
- **2026-10-30**: Selected Pinecone Inference API with `llama-text-embed-v2` (1024-dim, cosine similarity) as primary embedding provider, leveraging existing `PINECONE_API_KEY` without requiring additional third-party embedding subscriptions.
- **2026-10-30**: Designed doctor document builder to index strictly clinical fields (specialties, clinical bio, qualifications, city, clinic) while deliberately omitting personal names, phone numbers, and fees to prevent demographic and fee bias in vector space.
- **2026-10-30**: Configured multi-factor scoring formula: $Score = 0.40 \cdot S_{\text{vector}} + 0.25 \cdot S_{\text{specialty}} + 0.15 \cdot S_{\text{experience}} + 0.10 \cdot S_{\text{fee}} + 0.10 \cdot S_{\text{availability}}$, with all weights externalized in `Settings`.
- **2026-10-30**: Enforced strict single source of truth in PostgreSQL: any stale or invalid vector returned by Pinecone is discarded if the doctor is not approved in Supabase, exceeds consultation fee budget, or possesses zero upcoming availability slots.
- **2026-10-30**: Built automatic SQL fallback mode if Pinecone returns fewer than 3 qualifying candidates or encounters an outage, guaranteeing zero-downtime recommendation responses.
- **2026-10-30**: Enforced zero double-booking via database-level pessimistic row locking in PostgreSQL (`SELECT ... FOR UPDATE` inside `book_appointment_atomic`) combined with a partial unique constraint (`idx_appointments_slot_booked WHERE status = 'booked'`).
- **2026-10-30**: Enforced temporal slot integrity via PostgreSQL exclusion constraint (`no_overlapping_slots` using `btree_gist`) and application-level 15-minute minimum duration and future timestamp checks.
- **2026-10-30**: Verified booking atomicity under high concurrency with a 20-thread simultaneous race test guaranteeing exactly 1 success (201) and 19 conflicts (409).
- **2026-10-30**: Enforced strict separation of frontend keys in `web/.env.example`: frontend holds exclusively `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`, communicating with backend API using Supabase JWT tokens; backend never exposes service-role, Pinecone, or LLM keys to client code.
- **2026-10-30**: Designed patient triage chat UI to surface medical safety warnings as permanent prominent disclaimers and render emergency escalations as high-urgency red alerts with direct 999 toll-free dialers.
- **2026-10-30**: Integrated specialist recommendations directly into chat turns with match explanation snippets, match score percentage badges, and direct links to live slot booking.
- **2026-11-04**: Tokens are always verified by Supabase Auth, and production code has no test bypass. Tests replace verification from `conftest.py`. Roles always come from `profiles`, never from token metadata.
- **2026-11-04**: Migration `00006` makes the API the only writer: RLS gives clients read access only, and `book_appointment_atomic` is executable by the service role alone.
- **2026-11-04**: Recommendations hard-filter on city and specialty (General Medicine doctors stay eligible) on both the hybrid and SQL paths.
- **2026-11-04**: Closing a patient account anonymizes the profile and bans the sign-in identity rather than deleting it, so doctors' appointment records survive. Upcoming appointments block closure.
- **2026-11-04**: Playwright runs against a mocked API with `api.test` and `supabase.test` hosts, and blocks all other outbound requests, so UI tests cannot reach the real project or paid AI services.
- **2026-11-04**: AI consent is enforced by the API. An emergency still gets its alert without consent, and nothing the patient wrote is stored.
- **2026-11-04**: Backend tests ignore `.env` and refuse non-local hosts, because they once wrote fake approved doctors to the real project.
- **2026-11-04**: Rule-based detection alone missed 61% to 88% of unseen phrases, so the classifier is a second net rather than a replacement. Never report a detection score measured on phrases the rules were tuned on.
- **2026-11-05**: Reversed the fixed-reply design on the owner's instruction, because it made the assistant robotic. One model call wrote the reply and read the details, since split into two steps. A model failure returns 503 and saves nothing, rather than a canned question. The guard is now the last check on model text, and it is known to be incomplete.
- **2026-11-05**: Moved the assistant from OpenRouter to Groq on the owner's instruction, using `openai/gpt-oss-120b`. The account limit of 8,000 tokens a minute is shared by every model, and a turn uses about 1,800 tokens, so it handles about 4 messages a minute. The client honours `Retry-After` up to 10 seconds.
- **2026-11-04**: Assistant state lives on the conversation row, not in a LangGraph checkpointer, so deletion and multiple workers need no extra machinery.
- **2026-11-04**: Booking, cancelling and completing run in locked stored procedures. Appointments keep their own times, and audit logs are append-only for every writer.
- **2026-11-04**: Signed-in reads of chats, appointments and credentials use the caller's token, so RLS applies. Writes use the service role behind route checks.
- **2026-11-04**: LLM calls have a deadline on the whole call, because provider keep-alive bytes restart httpx read timeouts.




