# MediMatch AI: Deployment

## Before You Deploy

- Set `ENVIRONMENT=production`. The app then refuses `:free` LLM models and fake embeddings, and turns off `/docs`.
- Use a paid OpenRouter model. See `docs/PRIVACY.md`.
- Have a clinician review `backend/app/ai/data/emergency_patterns.json`.
- Decide on email confirmation. Registration confirms addresses automatically today, because the web app signs in straight after. Turning it off needs an email service and a web change.

## Configuration

Copy `.env.example` and set every value through your host's secret manager. Never bake `.env` into an image: `.dockerignore` excludes it.

Set `BACKEND_CORS_ORIGINS` to your web origins. A wildcard is refused at startup.

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
- **Readiness:** `GET /ready` returns 503 if the database is unreachable. Pinecone and OpenRouter are reported but optional, since both have fallbacks.

**Workers:** rate limits are counted per process, so `workers x limit` applies. Run behind a proxy that sets `X-Forwarded-For`, or the limits see the proxy's address.

## Scheduled Jobs

| Job | Command | When |
|---|---|---|
| Erase expired chats | `python scripts/purge_expired.py` | Daily |
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
