# MediMatch AI: Security Report

Results from 2026-11-04. Attacks ran against a local Supabase stack with real tokens, not the live project. Findings are in `docs/AUDIT.md`.

**Summary:** every attack in the final pass was blocked. **The fixes are not all on the live project yet**, because migrations `00008` to `00012` need your approval. Until they run, the live database still has the direct-write gaps listed at the end.

## Test Results

| Check | Result |
|---|---|
| Backend tests, on real Postgres | 867 passed, in a clean install from pinned files |
| Coverage | 93% overall, 100% on safety and booking |
| Coverage of services | 88% to 100%, against a target of 80% |
| ruff, ruff format, mypy | All clean. mypy runs with typed definitions required, not full `--strict` |
| pip-audit, pinned dependencies | No known vulnerabilities |
| gitleaks, full git history | 0 findings |
| End-to-end journey, real tokens, Pinecone and LLM | 32 of 32 checks passed |
| Real web app in Chrome, all three roles | 44 API responses, all 200, 0 problems |
| Web unit tests | 44 passed |
| Docker image | Runs as non-root, healthy, no `.env` inside, stops cleanly in 1 second |

## Adversarial Pass

48 attacks, all blocked.

| Attack group | Attacks | Result |
|---|---|---|
| Reading or changing another user's data | 16 | 403 on each, and lists show only your own rows |
| Privilege escalation | 5 | 422 or 403. Setting `role` in your own user metadata has no effect |
| Tokens: expired, wrong key, admin claim, `alg=none`, none | 5 | 401 on each |
| SQL and JSON injection in text fields | 12 | Treated as text. No rows changed, no unapproved doctors exposed |
| Disguised or oversized uploads, and path traversal | 6 | 415, 413 or 422 |
| Flooding chat, login and signup | 3 | 429 after 20, 10 and 5 requests a minute |

The script's own report showed 1 item to check. That was a bug in its comparison: the same row-count check passed separately.

**Flood detail:** 40 emergency messages gave 20 alerts and 20 429s. The limit protects the service, but it also means a patient sending more than 20 messages a minute would be refused, even for an emergency.

## Before and After

| Check | Before | After |
|---|---|---|
| Unauthenticated booking on the live project | Possible | **Closed on live** |
| Doctors' phone numbers readable by anon on live | Yes | **Closed on live** |
| Fake approved doctors listed publicly | 15 | **Removed from live** |
| Emergency alert depends on a database write | Yes | No |
| Unsigned tokens accepted by `ENVIRONMENT=test` | Yes | Path removed |
| Read another doctor's credential through `../` | Proven | Blocked, field removed |
| Admin can read patient chats | Yes | No |
| Forged consent through PostgREST | Proven | Closed, **live needs `00008`** |
| Self-insert as admin with no profile row | Proven | Closed, **live needs `00008`** |
| Rate limiting | None | Login, signup, chat, uploads |
| Disguised files | Accepted | Refused by content |
| RLS inside the API | Not used | Public and signed-in reads use it |
| Malformed ids | 500 | 422 |
| Untyped responses | 17 | 0 |
| Clean install | Could not start | Works from pinned files |

## Route Inventory After the Fixes

41 unique operations, plus `GET /specialties` and `GET /`. The same routes also exist under `/api/v1`, hidden from the docs. Before the fixes, 17 had no precise response model, admins passed patient and doctor checks, and any signed-in role could book or request recommendations. "Rate limited" means by the API. Web sign-in goes straight to Supabase Auth, which has its own limits.

| Method | Path | Roles | Rate limited | Response model |
|---|---|---|---|---|
| GET | `/health` | public | - | HealthResponse |
| GET | `/ready` | public | - | Readiness JSON |
| POST | `/auth/register-patient` | public | yes | RegisterResponse |
| POST | `/auth/register-doctor` | public | yes | RegisterResponse |
| POST | `/auth/login` | public | yes | TokenResponse |
| GET | `/me` | any signed-in | - | UserMeResponse |
| PATCH | `/me` | any signed-in | - | UserMeResponse |
| DELETE | `/me/conversations` | any signed-in | - | ChatHistoryDeleted |
| DELETE | `/me` | any signed-in | - | MessageResponse |
| GET | `/doctors/me/profile` | doctor | - | DoctorProfileRead |
| POST | `/doctors/me/profile` | doctor | - | DoctorProfileRead |
| PUT | `/doctors/me/profile` | doctor | - | DoctorProfileRead |
| POST | `/doctors/me/credentials` | doctor | yes | DoctorCredentialRead |
| GET | `/doctors/me/credentials` | doctor | - | list[DoctorCredentialRead] |
| GET | `/doctors/me/verification-history` | doctor | - | list[VerificationEvent] |
| GET | `/doctors/credentials/{id}/url` | any signed-in | - | CredentialLink |
| POST | `/doctors/me/slots` | doctor | - | SlotResponse |
| GET | `/doctors/me/slots` | doctor | - | list[SlotResponse] |
| DELETE | `/doctors/me/slots/{slot_id}` | doctor | - | none (204) |
| GET | `/doctors/specialties` | public | - | list[SpecialtyRead] |
| GET | `/doctors/search` | public | - | DoctorSearchResult |
| GET | `/doctors/{id}` | public | - | PublicDoctorRead |
| GET | `/doctors/{id}/slots` | public | - | list[SlotResponse] |
| POST | `/appointments` | patient | - | AppointmentResponse |
| GET | `/appointments/me` | any signed-in | - | list[AppointmentResponse] |
| POST | `/appointments/{id}/cancel` | any signed-in | - | AppointmentResponse |
| POST | `/appointments/{id}/complete` | doctor | - | AppointmentResponse |
| GET | `/admin/patients` | admin | - | AdminPatientPage |
| GET | `/admin/doctors` | admin | - | AdminDoctorPage |
| POST | `/admin/doctors/{id}/approve` | admin | - | DoctorActionResponse |
| POST | `/admin/doctors/{id}/reject` | admin | - | DoctorActionResponse |
| POST | `/admin/doctors/{id}/suspend` | admin | - | DoctorActionResponse |
| GET | `/admin/audit-logs` | admin | - | AuditLogPaginatedResponse |
| POST | `/admin/specialties` | admin | - | SpecialtyRead |
| GET | `/admin/specialties` | admin | - | list[SpecialtyRead] |
| PUT | `/admin/specialties/{id}` | admin | - | SpecialtyRead |
| DELETE | `/admin/specialties/{id}` | admin | - | MessageResponse |
| GET | `/chat/conversations` | patient | - | list[ConversationSummary] |
| POST | `/chat/conversations` | patient | - | ConversationCreated |
| POST | `/chat/conversations/{id}/messages` | patient | yes | SendMessageResponse |
| GET | `/chat/conversations/{id}` | patient | - | ConversationDetail |
| POST | `/recommendations` | patient | - | RecommendationResponse |

## Known Gaps

**Decisions for you**
- **Live migrations `00008` to `00012` are not applied.** Until then, forged consent and the admin-row insert remain possible there, and the code in this repository does not match that database: it needs `public_doctors`, `conversations.graph_state`, and the new booking functions. **Do not deploy this code to the live project before migrating.**
- **Email addresses are not verified.** Anyone can register with someone else's address, because the web app signs in straight after registering. Fixing this needs an email service and a web change.
- **The free LLM model must not handle real patient text.** See `docs/PRIVACY.md`.
- **45 other `@test.com` accounts remain on the live project**, which you have not approved removing.

**Limits of what was built**
- Rate limits are per worker, and in memory.
- Rate limits on `/auth/login` do not cover web sign-in, which uses Supabase directly.
- Profile reads and recommendations still use the service role, behind route checks.
- `/doctors/search` is public and has no rate limit.
- The audit log can fail silently, though failures are now logged as errors.
- Doctors have no account deletion path.
- Name redaction is rule-based and incomplete.
- A restore from the backup has not been tested.

**Clinical**
- **Emergency patterns need a clinician's review before real patients use this.** See `docs/EVAL_REPORT.md`.
- Self-harm alerts have no crisis line, because I would not add a number I could not verify.
