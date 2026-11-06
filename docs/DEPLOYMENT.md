# MediMatch AI: Deployment

## Before You Deploy

- Set `ENVIRONMENT=production`. The app then refuses fake embeddings and turns off `/docs`.
- This project uses Groq for the assistant. Read `docs/PRIVACY.md` first.
- Have a clinician review `backend/app/ai/data/emergency_patterns.json`.
- Decide on email confirmation. Registration confirms addresses automatically today, because the web app signs in straight after. Turning it off needs an email service and a web change.

## Configuration

Copy `.env.example` and set every value through your host's secret manager. Never bake `.env` into an image: `.dockerignore` excludes it.

Set `BACKEND_CORS_ORIGINS` to your web origins. A wildcard is refused at startup.

## Hosting on Render

`render.yaml` deploys the API from `backend/Dockerfile` and the web app as a static site.

1. In Render, choose New, then Blueprint, and connect this GitHub repository.
2. Fill in the values it asks for. They stay in Render and are never committed.
3. Set `GROQ_API_KEY`. The current Groq account allows 8,000 tokens a minute, 200,000 tokens a day and 1,000 requests a day. A patient message uses about 3,300 tokens, so that is about 2 messages a minute and about 60 a day across all patients. Raise the account limit before real use.
4. Set `CRISIS_HELPLINES`, and verify every number yourself by calling it. With it empty, crisis messages show only `EMERGENCY_NUMBER`.
5. Apply migration `00013`, so the mental-health specialties exist, and approve real providers for them. Until then, patients in emotional distress cannot be matched to the right kind of care.
4. Set `BACKEND_CORS_ORIGINS` to `["https://your-web-address"]`, and `VITE_API_BASE_URL` to the API address, then redeploy the web app.
5. Check the whole journey on the hosted API:

```bash
python backend/scripts/e2e_check.py --api https://your-api-address --allow-remote
```

Render's free plan sleeps when idle, so the first request after a pause is slow. It has no scheduled jobs either, so the jobs below need a paid plan or another scheduler.

## Migrations

`backend/app/run_migrations.py` applies each file in `supabase/migrations/` once and records it in `schema_migrations`.

**The current live project needs a baseline once**, because it has tables but no history. It has migrations up to `00007`:

```bash
python backend/app/run_migrations.py --baseline 00007
```

After that, run it with no arguments on each deploy, before starting the new version. Each file runs in its own transaction, and a failure stops the run. Back up first.

Connecting from a container may need a pooled connection string: the direct Supabase host is IPv6 only, and Docker networks often have no IPv6 route.

## Running the API

```bash
docker build -f backend/Dockerfile -t medimatch-api .
docker run --env-file .env.production -p 8000:8000 medimatch-api
```

The image runs as a non-root user, has a health check, and finishes running work on `SIGTERM`, within 30 seconds.

- **Liveness:** `GET /health`
- **Readiness:** `GET /ready` returns 503 if the database is unreachable. Pinecone and Groq are reported but optional, since both have fallbacks.

**Workers:** rate limits are counted per process, so `workers x limit` applies. Run behind a proxy that sets `X-Forwarded-For`, or the limits see the proxy's address.

## Billing

Apply migration `00014`, then set prices at `/admin/billing`. Until a price is set, nothing is charged. Payment happens outside the app, and an admin records it there.

## Scheduled Jobs

| Job | Command | When |
|---|---|---|
| Erase expired chats | `python scripts/purge_expired.py` | Daily |
| Charge doctor subscriptions | `python scripts/bill_subscriptions.py` | Daily. Each month is charged once |
| Retry failed vector syncs | `python scripts/reindex_all.py --unsynced` | Every 15 minutes |
| Rebuild the vector index | `python scripts/reindex_all.py` | After changing the embedding model |

## Rollback

Migrations only move forward. To roll back, redeploy the previous image, and restore a database backup only if a migration must be undone. Test a restore before you rely on one.

## Monitoring

Alert on these log messages:

- `[SAFETY ESCALATION]`, to see volume, not as an error
- `LLM attempt` failures, because the classifier layer of emergency detection is off while they continue
- `Failed to record audit log`, since those events are lost
- `Unhandled`, for unexpected errors
- `sync_status = 'failed'` rows in `doctor_profiles`
