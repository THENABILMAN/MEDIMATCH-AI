# MediMatch AI 🩺🤖

AI-Powered Doctor Recommendation & Appointment Booking Platform.

MediMatch AI connects patients with verified, suitable medical specialists using an intelligent conversational assistant, hybrid semantic search, live doctor schedules, and role-based access.

---

## 🛠 Stack
- **Backend API**: FastAPI (Python 3.12+)
- **Database & Auth**: Supabase (PostgreSQL, Supabase Auth, Row-Level Security)
- **Vector Search Index**: Pinecone
- **AI Orchestration & LLM**: LangGraph, OpenRouter
- **Web Frontend**: React + TypeScript (Vite)
- **Mobile Frontend**: Flutter (Dart)

---

## 📁 Repository Structure
```text
MEDIMATCH-AI/
├── backend/
│   ├── app/
│   │   ├── api/            # API routes and dependencies (v1, auth, users, health)
│   │   ├── core/           # Settings (pydantic-settings), security, Supabase client
│   │   ├── models/         # Enums (UserRole, VerificationStatus, AppointmentStatus)
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── services/       # Auth, profile, and audit services
│   │   ├── main.py         # Application entry point (/health, /me, /auth)
│   │   └── run_migrations.py # SQL migration runner
│   ├── tests/              # Pytest test suite (health, auth, RBAC, RLS)
│   ├── pyproject.toml      # Project metadata & build tool
│   └── requirements.txt    # Python dependencies
├── supabase/
│   └── migrations/         # Numbered SQL schema and RLS policies
├── docs/                   # System plans and architecture specs
├── CLAUDE.md               # Development guide and progress tracking
└── README.md               # Onboarding and instructions
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.11+
- A [Supabase](https://supabase.com) project (or local Supabase via CLI)
- A [Pinecone](https://pinecone.io) account & index
- An [OpenRouter](https://openrouter.ai) API key

### 2. Environment Configuration
Copy the example environment file and fill in your credentials:
```bash
cp .env.example .env
```

Ensure your `.env` contains the required keys:
```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
DATABASE_URL=postgresql://postgres:your_password@db.your-project.supabase.co:5432/postgres
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX=medimatch-doctors
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

### 3. Install Backend Dependencies
```bash
# Navigate to backend or repo root
python -m pip install -r backend/requirements.txt
```

### 4. Apply Database Migrations
Apply the initial schema and Row-Level Security policies to your PostgreSQL / Supabase database:
```bash
python backend/app/run_migrations.py
```
Or via Supabase CLI:
```bash
supabase db push
```

### 5. Seed Demo Data & Local Test Accounts
Populate 3 specialties, 10 demo Bangladesh doctors (approved, pending, suspended), and 3 core test accounts:
```bash
python backend/scripts/seed.py
```

#### Demo Test Accounts (Local / Development Use Only)
| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@medimatch.test` | `AdminPass123!` | Platform administrator with review privileges |
| **Doctor** | `doctor@medimatch.test` | `DoctorPass123!` | Verified consultant cardiologist in Dhaka |
| **Patient** | `patient@medimatch.test` | `PatientPass123!` | Standard patient user |

### 6. Run the Backend API
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```
- Interactive API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 7. Run the Automated Tests
```bash
python -m pytest backend/tests/ -v
```

---

## 🔒 Security & Medical Non-Negotiables
1. **PostgreSQL as Source of Truth**: Pinecone only indexes specialties and profiles for semantic search. All records are re-fetched from Supabase to guarantee live verification status and availability.
2. **Secret Isolation**: Frontend clients never receive service-role, Pinecone, or OpenRouter keys.
3. **Medical Safety**: The conversational assistant never diagnoses, prescribes, or claims symptoms are harmless. It guides patients to qualified medical specialists.
4. **Deterministic Emergency Triage**: Red-flag emergency detection is rule-based (regex and keywords) with comprehensive unit tests, never left solely to an LLM.
5. **Doctor Verification Enforcement**: Only doctors with `verification_status = 'approved'` are ever visible or bookable by patients.
6. **Strict Row-Level Security (RLS)**: Every user table has least-privilege RLS policies.
7. **PII Sanitization**: Personal identifiers (names, emails, phones) are stripped before sending symptom descriptions to LLMs or vector embeddings.

