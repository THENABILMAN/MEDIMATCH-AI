# MediMatch AI

MediMatch AI helps patients in Bangladesh find a verified doctor and book a time. A patient describes symptoms in their own words, an AI assistant asks a few questions, and the app shows suitable doctors with live schedules.

The assistant never diagnoses or prescribes. Possible emergencies get a fixed alert to call 999.

## Status

The backend and the patient, doctor and admin web portals work end to end. The Flutter app and production deployment are still to come. See [CLAUDE.md](CLAUDE.md) for details.

## Stack

| Part | Technology |
|---|---|
| API | FastAPI, Python 3.12 |
| Database and auth | Supabase (Postgres, Auth, Row-Level Security, Storage) |
| Search | Pinecone with `llama-text-embed-v2` |
| AI | LangGraph, with free OpenRouter models |
| Web | React 19, TypeScript, Vite, Tailwind CSS v4, Radix |

## Repository

```text
backend/
  app/            API routes, core settings, AI assistant, search, services
  scripts/        Seed, reindex, evaluations, purge, end-to-end check
  tests/          Pytest suite
web/              React app, with Vitest and Playwright tests
supabase/         Migrations and local stack config
docs/             Design, deployment, privacy, audit, security and eval reports
.env.example      Every backend setting
CLAUDE.md         Project rules, commands, status and decisions
```

## Run It Locally

You need Python 3.12, Node, Docker, and accounts with Pinecone and OpenRouter.

**1. Configure.** Copy the example files, then fill them in. Values for local Supabase come from `npx supabase@latest status`.

```bash
cp .env.example .env
cp web/.env.example web/.env
```

**2. Install.**

```bash
python -m pip install -r backend/requirements-dev.txt
cd web && npm install
```

**3. Start the database and add demo data.**

```bash
npx supabase@latest start
npx supabase@latest db reset
python backend/scripts/seed.py --with-logins
```

`--with-logins` only works on a local database. It sets passwords for these accounts, and the development sign-in page has a button to fill in each one.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@medimatch.test` | `Admin123!Safe` |
| Doctor | `doctor@medimatch.test` | `Doctor123!Safe` |
| Patient | `patient@medimatch.test` | `Patient123!Safe` |

**4. Build the search index.**

```bash
python backend/scripts/setup_pinecone_index.py
python backend/scripts/reindex_all.py
```

**5. Start the API and the web app, in two terminals.**

```bash
cd backend && python -m uvicorn app.main:app --reload --port 8000
cd web && npm run dev
```

The web app runs at `http://localhost:5173`, and the API docs at `http://localhost:8000/docs`.

To apply migrations to a hosted database, set `DATABASE_URL` and run `python backend/app/run_migrations.py`.

## Test

```bash
cd backend && python -m pytest tests -q   # Needs local Supabase, and refuses any other host
cd web && npm test                        # Vitest
cd web && npx playwright test             # Browser tests on a mocked API
```

`make check` runs the backend lint, types, tests and dependency audit. `CLAUDE.md` lists every other command.

## Project Rules

1. Supabase Postgres is the source of truth. Pinecone is only a search index, so doctor records are always re-read from Postgres.
2. Service-role, Pinecone and OpenRouter keys stay on the backend.
3. The assistant never diagnoses, prescribes, or says serious symptoms are harmless.
4. Emergency detection runs on fixed rules first. The model can add an alert but never remove one.
5. Only approved doctors can be found or booked.
6. Every table with user data has Row-Level Security, and the API is the only writer.
7. Names, phone numbers and emails are removed before text reaches an AI provider.

## Docs

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md): configuration, migrations, Docker and scheduled jobs
- [docs/PRIVACY.md](docs/PRIVACY.md): what is stored, and what third parties receive
- [docs/SECURITY_REPORT.md](docs/SECURITY_REPORT.md): test results and known gaps
- [docs/EVAL_REPORT.md](docs/EVAL_REPORT.md): emergency detection and recommendation quality
- [docs/AUDIT.md](docs/AUDIT.md): the backend audit, before the fixes
- [docs/DESIGN.md](docs/DESIGN.md) and [docs/UI_PRINCIPLES.md](docs/UI_PRINCIPLES.md): web design rules
- [docs/UI_AUDIT.md](docs/UI_AUDIT.md) and [docs/UI_REVIEW.md](docs/UI_REVIEW.md): the web UI before and after the redesign
