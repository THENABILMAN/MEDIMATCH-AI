# MediMatch AI Backend Audit

Audit date: 2026-11-04, at commit `9027d3f`. No application code was changed for this audit.

Part of this code was written by Claude Code earlier in the same project (`account_service.py`, migrations `00006` and `00007`, the credential routes). It is judged the same way as the rest.

**Evidence labels**
- **PROVEN:** the behaviour was observed by running it.
- **READ:** found by reading the code, not yet triggered.

**Severity:** Critical, High, Medium, Low.

**This records the state before the fixes.** For what changed and what remains, see `docs/SECURITY_REPORT.md`.

## Summary

The backend runs and its core design is reasonable, but it is not ready for patients.

1. **Live booking hole:** the public anon key can run the booking function on the live project, because migration `00006` was never applied.
2. **Live chat failure:** chat saves to a column that does not exist on the live database, so turns should fail, including emergencies.
3. **Emergency detection:** it missed 93 of 118 test phrases, and common wording such as "my chest hurts" is among them.
4. **Output guard:** it let 25 of 32 unsafe replies through, including "There is no need to see a doctor".
5. **Claimed results:** the 100% Precision@3 score tests nothing, and the race and RLS tests only run against a real project.
6. **Clean install:** a fresh install from `requirements.txt` cannot start the app.

## Update: Blocked Checks Now Run

Completed the same day, once Docker and the database password were available. All attacks ran against a local Supabase stack with real tokens, never the live project.

**Live project containment, done:**
- Backed up `public` and `auth` first. The backup's contents were listed, but a test restore has not been run.
- Applied `00006` and `00007`. Anon now gets `permission denied` on `book_appointment_atomic`, and doctors' phone numbers are no longer readable by anon.
- Removed the 15 fake approved doctors and their 7 vectors. They had no appointments, slots, credentials or audit rows. 7 real approved doctors remain.

**Rebuild from zero: PROVEN.** All 7 migrations apply cleanly to an empty Supabase database.

**Double-booking attack: PROVEN safe.**

| Attack | Result |
|---|---|
| 20 patients, one slot, 3 rounds | 1 success and 19 409s each round, 1 booked row each time |
| One patient, one slot, 20 requests | 1 success, 19 409s |
| Double cancel racing a rebook, 25 rounds | 0 inconsistent slots. Concurrent cancels can both return 200 |

**New or upgraded findings:**

| Severity | Finding | Evidence |
|---|---|---|
| High | **A doctor account can read another doctor's credential file through the API.** Registering `own-id/../victim-id/file.pdf` passes the prefix check, and the signed link opened the victim's file. Anyone can self-register as a doctor. The attacker needs the exact path, which is hard to guess for API uploads because they carry a random prefix. `doctors.py:75` | PROVEN |
| High | A user with no `profiles` row can insert `role = 'admin'` directly. Signup normally creates that row, so this needs an edge case, but the policy is live. `00002:82` | PROVEN |
| High | A patient can set `ai_consent_at` and `deleted_at` on their own profile directly, so consent can be forged. `profiles_update_own` | PROVEN |
| High | No throttling: 60 wrong passwords through `/auth/login` in 0.4 seconds, all 401 | PROVEN |
| High | 30 accounts registered with 6-character passwords, with no throttling | PROVEN |
| High | A duplicate email returns "A user with this email address has already been registered" | PROVEN |
| High | Admin read a patient's chat with 200 and no audit entry | PROVEN |
| High | An approved doctor renamed to "Prof. Famous Surgeon" and stayed approved | PROVEN |
| High | Completing a future appointment returns 200, and completing it again returns 200 | PROVEN |
| High | A chat message with no consent returned 200, and raw symptoms were stored | PROVEN |
| Medium | A doctor can book another doctor's slot | PROVEN |
| Medium | A disguised executable uploaded as a PDF was accepted | PROVEN |
| Medium | A 30MB upload is read fully into memory, then fails with 502 rather than 413 | PROVEN |
| Medium | One patient booked 10 slots with no limit | PROVEN |
| Medium | Only 5 of 7 approved doctors are in Pinecone | PROVEN |
| Medium | 45 other `@test.com` accounts remain on the live project, not authorized for removal | PROVEN |
| Low | Cancelling checks status before ownership, so a stranger learns an appointment is completed from the 400 | PROVEN |

**Corrections to the first pass:**
- The cancel race was rated High from reading the code. It did not reproduce in 25 rounds, so it is now Medium. Cancels are still not atomic and will be fixed.
- A chat emergency returns 200 now that the live database has its columns. The fix to return the alert before any database write still stands.

**RLS with real sessions**

Rows visible to each role, in a seeded local database:

| Table | anon | patient A | patient B | doctor | pending doctor | admin |
|---|---|---|---|---|---|---|
| `profiles` | 0 | 1 | 1 | 1 | 1 | all |
| `doctor_profiles` | 1 | 1 | 1 | 1 | 2 | 2 |
| `availability_slots` | 2 | 2 | 2 | 2 | 2 | 2 |
| `appointments` | 0 | 1 | 0 | 1 | 0 | 1 |
| `conversations`, `messages`, `patient_symptom_sessions` | 0 | 1 | 0 | 0 | 0 | 1 |
| `doctor_credentials` | 0 | 0 | 0 | 1 | 0 | 1 |
| `audit_logs` | 0 | 0 | 0 | 0 | 0 | 1 |

Isolation holds. Blocked direct writes: own role change, editing another profile, self-approval, editing a doctor profile, inserting or changing appointments, changing slots, inserting messages, deleting conversations, inserting audit logs, admins changing or deleting audit logs, and creating specialties. Anon and patients are refused the booking function, and the bucket refuses direct reads and uploads.

## Tooling Results

Run on Python 3.12.13 in a venv outside the repo. All service variables were blank, so nothing touched a real service.

| Tool | Result |
|---|---|
| Fresh install, then import | **Fails:** `ImportError: email-validator is not installed`. `requirements.txt` omits it. High, PROVEN |
| pytest (after adding `email-validator` to the venv) | 152 passed, 41 failed, 5 errors, 3 skipped. Same on Python 3.14 |
| Coverage, offline | 58% overall. `appointment_service` 13%, `auth_service` 16%, `admin_service` 21%, `recommend` 46%, `safety` 96%. Lines ran; assertions are a separate question, see 3f |
| pip-audit | No known vulnerabilities. This only covers versions resolved today, because nothing is pinned |
| detect-secrets, tracked files | 5 files flagged. All are placeholders, mock keys or UI labels |
| gitleaks 8.30.1, full git history | 0 findings |
| ruff | 745 errors, 59 files need formatting |
| mypy | 962 errors, 987 with `--strict` |

**Test reality:** 201 tests exist. The 46 that fail or error offline need live services and write to whichever project `.env` names. All 3 RLS tests are skipped offline, and the 20-thread race test is one of the failures.

## 3a. Route Inventory

41 unique operations, plus `GET /specialties` and `GET /`. Each is mounted twice, at the root and under `/api/v1`, giving 84 operations on 66 paths. The web app uses the root paths.

"Path in tests" means the path appears in a test file. It does not show that the test can run offline.

| Method | Path | Roles | Body | Response model | Path in tests |
|---|---|---|---|---|---|
| GET | `/health` | PUBLIC | - | none | yes |
| POST | `/auth/register-patient` | PUBLIC | RegisterPatientRequest | none | NO |
| POST | `/auth/register-doctor` | PUBLIC | RegisterDoctorRequest | none | NO |
| POST | `/auth/login` | PUBLIC | LoginRequest | TokenResponse | NO |
| GET | `/me` | any signed-in | - | UserMeResponse | yes |
| PATCH | `/me` | any signed-in | ProfileUpdate | UserMeResponse | yes |
| DELETE | `/me/conversations` | any signed-in | - | Dict[str, Any] | NO |
| DELETE | `/me` | any signed-in | - | Dict[str, Any] | yes |
| GET | `/doctors/me/profile` | doctor, admin | - | DoctorProfileRead | yes |
| POST | `/doctors/me/profile` | doctor, admin | DoctorProfileCreateOrUpdate | DoctorProfileRead | yes |
| PUT | `/doctors/me/profile` | doctor, admin | DoctorProfileCreateOrUpdate | DoctorProfileRead | yes |
| POST | `/doctors/me/credentials` | doctor, admin | multipart | DoctorCredentialRead | yes |
| GET | `/doctors/me/credentials` | doctor, admin | - | List[DoctorCredentialRead] | yes |
| GET | `/doctors/me/verification-history` | doctor, admin | - | List[Dict[str, Any]] | NO |
| GET | `/doctors/credentials/{id}/url` | any signed-in | - | Dict[str, str] | NO |
| POST | `/doctors/me/slots` | doctor, admin | SlotCreate | SlotResponse | yes |
| GET | `/doctors/me/slots` | doctor, admin | - | List[SlotResponse] | yes |
| DELETE | `/doctors/me/slots/{slot_id}` | doctor, admin | - | none | yes |
| GET | `/doctors/specialties` | PUBLIC | - | List[SpecialtyRead] | NO |
| GET | `/doctors/search` | PUBLIC | - | DoctorSearchResult | yes |
| GET | `/doctors/{id}` | PUBLIC | - | PublicDoctorRead | yes |
| GET | `/doctors/{id}/slots` | PUBLIC | - | List[SlotResponse] | yes |
| POST | `/appointments` | any signed-in | AppointmentCreate | AppointmentResponse | yes |
| GET | `/appointments/me` | any signed-in | - | List[AppointmentResponse] | yes |
| POST | `/appointments/{id}/cancel` | any signed-in | optional body | AppointmentResponse | yes |
| POST | `/appointments/{id}/complete` | doctor, admin | - | AppointmentResponse | yes |
| GET | `/admin/patients` | admin | - | Dict[str, Any] | NO |
| GET | `/admin/doctors` | admin | - | Dict[str, Any] | yes |
| POST | `/admin/doctors/{id}/approve` | admin | - | Dict[str, Any] | yes |
| POST | `/admin/doctors/{id}/reject` | admin | AdminDoctorActionRequest | Dict[str, Any] | yes |
| POST | `/admin/doctors/{id}/suspend` | admin | AdminDoctorActionRequest | Dict[str, Any] | yes |
| GET | `/admin/audit-logs` | admin | - | AuditLogPaginatedResponse | yes |
| POST | `/admin/specialties` | admin | SpecialtyCreate | SpecialtyRead | yes |
| GET | `/admin/specialties` | admin | - | List[SpecialtyRead] | yes |
| PUT | `/admin/specialties/{id}` | admin | SpecialtyUpdate | SpecialtyRead | yes |
| DELETE | `/admin/specialties/{id}` | admin | - | Dict[str, Any] | yes |
| GET | `/chat/conversations` | patient, admin | - | List[Dict[str, Any]] | yes |
| POST | `/chat/conversations` | patient, admin | optional body | Dict[str, Any] | yes |
| POST | `/chat/conversations/{id}/messages` | patient, admin | SendMessageRequest | SendMessageResponse | yes |
| GET | `/chat/conversations/{id}` | patient, admin | - | Dict[str, Any] | yes |
| POST | `/recommendations` | any signed-in | RecommendationQueryRequest | RecommendationResponse | yes |

**Flags**

| Severity | Finding | Evidence |
|---|---|---|
| High | Admins pass `require_patient`, so they can read any patient's chat, with no audit entry. `chat.py:109`, `deps.py:94` | READ |
| High | `POST /appointments` accepts any role. `appointments.py:29` | READ |
| High | `POST /recommendations` accepts any role and skips emergency checks. `recommendations.py:42` | READ |
| Medium | Admins pass `require_doctor`, so they can create a doctor profile for themselves. `deps.py:95` | READ |
| Medium | 17 operations have no precise response model, so their output is not whitelisted | PROVEN |
| Medium | 8 operations appear in no test, including all registration and the credential link | PROVEN |

## 3b. Database

| Severity | Finding | Evidence |
|---|---|---|
| Critical | `book_appointment_atomic` is callable by anon on the live project. It takes a caller-supplied patient ID and runs as `SECURITY DEFINER`, so anyone can book for anyone. `00005:28` | PROVEN: an anon call ran the function and returned its own 404 for nil IDs. Nothing was written |
| Critical | Migrations `00006` and `00007` are not applied on the live project | PROVEN: `messages.metadata`, `profiles.ai_consent_at` and `profiles.deleted_at` are missing |
| High | Client write policies should still be live for the same reason | READ, needs a write to prove |
| High | Anon can read the `phone` column for approved doctors' profiles. One row has a phone number | PROVEN, counted without reading values |
| High | The API uses the service role for almost all data access, including anonymous routes, so RLS is not a second layer inside the API | READ |
| High | `run_migrations.py` has no tracking table and replays every file on each run, so a skipped migration goes unnoticed | READ |
| Medium | `profiles_insert_own_or_service` survives `00006`, and the role trigger only fires on UPDATE. A user with no profile row could insert `role = 'admin'`. `00002:82`, `00001:186` | READ |
| Medium | `profiles_update_own` survives `00006`, so a client can set its own `ai_consent_at` and `deleted_at` once those columns exist | READ |
| Medium | Deleting a slot sets `appointments.slot_id` to NULL, which erases the time from past appointments. `00001:89` | READ |
| Medium | `ON DELETE CASCADE` from `profiles` removes appointments if a profile row is ever deleted | READ |
| Medium | `timezone('utc', now())` yields a timestamp without a zone, then relies on the session timezone being UTC. `00005:66`, all column defaults | READ |
| Medium | `updated_at` has no trigger on `appointments` or `conversations`. `messages`, `doctor_specialties` and `availability_slots` have no `updated_at` | READ |
| Low | No index on `appointments.slot_id` alone, `patient_symptom_sessions.patient_id`, `conversations.patient_id` or `audit_logs(target_type, target_id, created_at)` | READ |
| Low | `sender` and `sync_status` are CHECK-constrained text rather than enums, and `messages` ordering relies on `created_at` alone | READ |

**Anon view of the live project, as row counts**

| Table | Visible to anon |
|---|---|
| `profiles` | 22 |
| `doctor_profiles` | 22 |
| `doctor_specialties` | 7 |
| `specialties` | 3 |
| `availability_slots` | 122 |
| `appointments`, `conversations`, `messages`, `patient_symptom_sessions`, `audit_logs`, `doctor_credentials` | 0 |

The zero rows may mean RLS blocked them or that the tables are empty. This check cannot tell which.

## 3c. Auth

| Severity | Finding | Evidence |
|---|---|---|
| High | `ENVIRONMENT=test` accepts unsigned tokens with any role, and that code ships to production. `security.py:60`, `deps.py:67` | READ |
| High | Registration sets `email_confirm: True`, so anyone can claim anyone's email. `auth_service.py:32` | READ |
| High | No rate limiting on registration or login | READ |
| High | Raw upstream errors go back to the caller, which also reveals whether an email exists. `auth_service.py:59,131` | READ |
| Medium | API accepts 6-character passwords, while the web form asks for 8. `schemas/auth.py:8` | READ |
| Medium | A Supabase outage returns 401 rather than 503, which signs users out. `security.py:72` | READ |
| Medium | `login_service` signs in on the shared anon client, which may keep that user's session on a client shared across requests. `auth_service.py:188` | READ |
| Medium | Every request makes a network call to verify the token. There is no local check | READ |
| Medium | Registration is not atomic. A failed profile write leaves an orphaned auth user. `auth_service.py:63` | READ |
| Low | `POST /auth/login` is unused by the web app, which signs in directly with Supabase. API rate limits would not cover web sign-in | READ |

**Held up:** roles come from `profiles`, not token claims. `extra="forbid"` blocks role and status in `PATCH /me`. Signup cannot assign `admin`. A bad token returns 401 (PROVEN).

## 3d. Doctor Verification and Credentials

| Severity | Finding | Evidence |
|---|---|---|
| High | An approved doctor can change `full_name` and stay approved, so they could impersonate another doctor. `profile_service.py:95` | READ |
| High | `file_path` passes a prefix check only, so `uid/../other/x` is accepted. The web app does not use this field. `doctors.py:75` | PROVEN, see the update near the top |
| High | Uploads have no app-side size cap and are read fully into memory. `doctors.py:92` | READ |
| High | The content type comes from the client and the file bytes are not inspected, so a disguised file passes. `doctors.py:99` | READ |
| Medium | Blocking Storage calls run inside an `async def`, stalling the event loop. `doctors.py:96` | READ |
| Medium | Approval needs no credential on file. `admin_service.py:126` | READ |
| Medium | The "mandatory" rejection reason is defaulted away by the route. `admin.py:78` | READ |
| Medium | Audit failures are swallowed, so an admin action can leave no record. `audit_service.py:30` | READ |
| Medium | Credential views and link creation are not audited. `doctor_service.py:230` | READ |
| Medium | A suspended doctor's upcoming appointments stay booked with no notice to anyone | READ |

**Held up:** the bucket is private, links are signed for 5 minutes, and owner or admin is enforced. Every approve, reject and suspend writes an audit event when that write succeeds.

## 3e. AI and LangGraph

Graph: `safety_check`, `classify_intent`, `extract_symptoms`, `check_missing`, then `ask_followup` or `build_search_criteria`.

| Severity | Finding | Evidence |
|---|---|---|
| Critical | The final reply skips the output guard and includes the LLM-chosen `location`. `graph.py:311` | READ |
| High | Patient text goes to `nvidia/nemotron-3-ultra-550b-a55b:free`. Free endpoints often allow logging or training, and no-logging routing is not requested. This model's policy is unchecked. `llm.py:68` | READ |
| High | A turn can hold a worker for minutes: 2 calls, 3 attempts, 30 seconds each. `llm.py:29,46` | READ |
| High | 429 and 5xx responses are not retried. Only network errors and timeouts are. `llm.py:47` | READ |
| High | `MemorySaver` keeps patient symptoms in process memory with no TTL, per worker. Deletion cannot reach other workers. `graph.py:382` | READ |
| Medium | Prompt injection: patient text goes straight to the LLM, and `general_conversation` returns free text with only the guard behind it. No private data is in context, so the main risks are off-topic use and unsafe text | READ |
| Medium | Full history goes out twice per turn, with no truncation | READ |
| Medium | An LLM outage is not visible anywhere, since the fallback looks like normal output | READ |
| Medium | An unparseable reply is put into an exception and then logged. `llm.py:129` | READ |
| Low | The default model and `HTTP-Referer` are hard-coded | READ |

**Held up:** nodes use typed state, follow-ups stop at 3, structured output is validated with Pydantic, and specialties map only to database names. An LLM failure falls back to General Medicine.

## 3f. Safety

The test list was 118 phrases in English, Bengali script and transliterated Bangla. It is deliberately harsh and is not a clinical benchmark. Some phrases, such as "fell from the roof", need a clinician's judgement.

| Severity | Finding | Evidence |
|---|---|---|
| Critical | 93 of 118 emergency phrases were missed (79%) | PROVEN |
| Critical | The output guard passed 25 of 32 unsafe replies | PROVEN |
| Critical | The emergency reply depends on a database write succeeding first. `chat_service.py:199` | READ |
| High | 10 of 10 negated or historical phrases raised an alarm, such as "no chest pain" | PROVEN |
| Medium | The alert is English only, even for Bangla messages. `safety.py:76` | READ |
| Medium | `emergency_number` in the JSON file is ignored, because the function defaults to a literal `"999"`. `safety.py:76` | READ |
| Medium | Self-harm gets the generic alert, with no crisis support line | READ |
| Medium | Zero-width characters are not stripped, so some Bangla keyboards may slip past the patterns. `safety.py:30` | READ |

**Examples of missed emergencies**
- **Chest:** "pain in my chest", "my chest hurts", "my chest feels tight", "বুকে ব্যাথা", "buke batha"
- **Breathing:** "trouble breathing", "hard to breathe", "my lips are blue", "sash kosto"
- **Stroke:** "one side of my body is weak", "my mouth is twisted to one side", "এক পাশ অবশ হয়ে গেছে", "মুখ বাঁকা হয়ে গেছে"
- **Poisoning:** "swallowed bleach", "drank pesticide", "took rat poison", "আমি বিষ খেয়েছি", "কীটনাশক খেয়েছে", "bish kheyechi"
- **Self-harm:** "i want to end it all", "i don't want to wake up", "মরে যেতে চাই", "আর বাঁচতে ইচ্ছে করছে না", "more jete chai"
- **Bleeding:** "blood is not stopping", "রক্ত বন্ধ হচ্ছে না", "প্রসবের পর প্রচুর রক্তপাত", "rokto bondho hocche na"
- **Other:** "hit by a car", "পানিতে ডুবে গেছে", "সাপে কেটেছে", "baby not moving in my womb"

**Examples the output guard let through**
- **Reassurance:** "You'll be fine", "There is no need to see a doctor", "It should go away on its own", "চিন্তার কিছু নেই", "chinta korben na"
- **Diagnosis:** "Looks like a sinus infection", "You probably have meningitis", "I think it's GERD", "apnar dengue hoyeche"
- **Treatment:** "Take Ceftriaxone", "A course of antibiotics should clear this", "নাপা খান", "napa khan"

**The phrase list needs a clinician's review before real patients use this.**

**Held up:** detection is rule-based, runs before any LLM call, keeps patterns in a reviewable file, and fails loudly if they cannot load. Emergency turns carry no recommendations.

## 3g. Retrieval

Provider: Pinecone Inference with `llama-text-embed-v2`, 1024 dimensions. The live index dimension is unchecked here.

| Severity | Finding | Evidence |
|---|---|---|
| High | The eval passes the expected specialty as the input, then checks for that specialty in the top 3. It proves the filter works, not matching. The 100% score means nothing. `eval_recommendations.py` | READ |
| High | 15 of 22 public doctors are test records from `test_rls.py:118`, with emails for names and ৳0 fees | PROVEN |
| High | `builder.py:35` crashes on a specialty whose description is null, because `.get()` returns `None`. That doctor never gets indexed | READ |
| High | Bio and clinic text are embedded unredacted, so contact details can reach the provider. `builder.py:47` | READ |
| High | Sync runs inside the request. A failed sync has no retry, and `last_synced_at` updates even on failure. `sync.py:72` | READ |
| Medium | Specialty edits and deletions never re-sync vectors. `admin_service.py:304` | READ |
| Medium | Pinecone is queried with no metadata filter, and `top_k` 20 exceeds the 15 fetched. `recommend.py:292` | READ |
| Medium | Under 3 hybrid results discards them all for SQL results. `recommend.py:410` | READ |
| Medium | ৳0 fees get the top fee score, so empty profiles rank higher. `recommend.py:143` | READ |
| Medium | The SQL fallback has no limit, and it loads every slot for each doctor. `recommend.py:177` | READ |
| Medium | A mistyped `EMBEDDING_PROVIDER` silently uses fake vectors. `embeddings.py:171` | READ |
| Low | `retry_if_exception_type(Exception)` also retries permanent 4xx errors | READ |

**Held up:** names and fees are excluded from embedded text. Stale vectors are re-checked against Postgres for approval, budget, city, specialty and slots. Pinecone failure falls back to SQL.

## 3h. Appointments

| Severity | Finding | Evidence |
|---|---|---|
| High | Cancel checks status, then runs two separate updates. A double cancel can free a slot someone else has rebooked. The next booking then hits the unique index and returns 500. `appointment_service.py:456-467` | READ |
| High | Appointments can be completed before they happen, or completed twice. `appointment_service.py:511` | READ |
| Medium | Deleting a slot checks `is_booked` first and then deletes, which can race with a booking. `appointment_service.py:205` | READ |
| Medium | Database errors from the booking call are not handled, so a constraint failure is a 500. `appointment_service.py:219` | READ |
| Medium | No booking limit per patient, so one account can take every slot. Overlapping bookings are allowed | READ |
| Medium | Naive datetimes are treated as UTC. A Dhaka local time would be stored 6 hours off. `schemas/appointment.py:21` | READ |
| Medium | Patients see "UTC" in recommendation text. `recommend.py:80` | READ |

**Double-booking attack: PROVEN safe**, see the update near the top. The design is a row lock, then a partial unique index as the second guard, plus an overlap exclusion constraint.

## 3i. Privacy

| Severity | Finding | Evidence |
|---|---|---|
| High | Consent is enforced only by the web screen, so symptoms can be stored without it through the API. `chat_service.py:139` | READ |
| High | There is no retention rule or cleanup for messages or symptom sessions | READ |
| High | Matched patient phrases are logged at WARNING. `safety.py:68` | PROVEN |
| High | Emails appear in auth logs, and names and phones go into `audit_logs`, which survive account closure. `auth_service.py:56,76`, `profile_service.py:111` | READ |
| High | Redaction missed names and identifiers | PROVEN |
| Medium | A closed account keeps its vectors clean, but doctor accounts have no deletion path | READ |

**Redaction results**
- **Caught:** "My name is Rahim Uddin", "amar nam Karim", "আমার নাম করিম", emails, and phones including `+880` and Bangla digits.
- **Missed:** "call me Fatima", "Rahim here", "i'm rahim", "আমি করিম", "my wife Salma", "017 1234 5678", street addresses.
- **Partly caught:** a 16-digit NID became `199[PHONE REDACTED]`.

## 3j. Reliability and Operations

| Severity | Finding | Evidence |
|---|---|---|
| High | `/doctors/not-a-uuid`, `/doctors/not-a-uuid/slots` and `/doctors/search?page=999999999999` return a plain 500. Every other ID route takes the same unvalidated string | PROVEN for those three |
| High | No rate limiting on chat or uploads | READ |
| Medium | No error envelope, request IDs, structured logs or logging setup, so INFO logs are never emitted | READ |
| Medium | `/ready` returns 404, and `/health` checks nothing | PROVEN |
| Medium | `/docs` and `/redoc` are public, with no way to turn them off | PROVEN |
| Medium | No security headers on responses | PROVEN |
| Medium | `sort_by=bad` is accepted silently, and `city=%` matches everything | PROVEN |
| Medium | `qualifications`, `specialty_ids`, admin reasons and doctor `bio` via `PATCH /me` have no length caps | READ |
| Medium | Lists of slots, appointments and conversations have no pagination | READ |
| Medium | Services silently fall back to the anon client if the service key is missing | READ |
| Low | A new HTTP client and a new Pinecone client are made on each call. No graceful shutdown handling | READ |

**Held up:** CORS refused a foreign origin (PROVEN), and wildcard origins are rejected at startup. Most handlers are plain `def`, so they run in the thread pool. Settings use `pydantic-settings`.

## 3k. Dependencies and Secrets

| Severity | Finding | Evidence |
|---|---|---|
| High | `email-validator` is undeclared, so a clean install cannot start | PROVEN |
| High | Nothing is pinned, although `CLAUDE.md` calls `requirements.txt` frozen. A fresh install moved FastAPI from 0.125 to 0.162 and Starlette from 0.49 to 1.10 | PROVEN |
| Medium | `asyncpg`, `python-dotenv` and `gotrue` are declared but never imported. `gotrue` also overlaps with the newer `supabase-auth` | PROVEN |
| Medium | `pytest` and `ruff` are in runtime requirements | READ |
| Low | Python 3.14 on this machine, 3.12 in the docs, and `>=3.11` in `pyproject.toml` | PROVEN |

**No secret was found in git history or tracked files.**

## 3l. Contract with the Frontend

Every path in `web/src/api/client.ts` exists in the API. No missing endpoints were found.

| Severity | Finding | Evidence |
|---|---|---|
| Medium | 17 operations have untyped responses, so OpenAPI cannot describe what the web app relies on | PROVEN |
| Medium | The web app reads `detail` from errors, so any new envelope must keep it. `web/src/api/client.ts:46` | READ |
| Medium | A 500 returns plain text, which the web client turns into "Request failed with status 500" | PROVEN |
| Low | `GET /doctors/specialties` and `/api/v1/*` are unused by the web app | READ |
| Low | The `file_path` upload field is unused by the web app | READ |

## 4. Missing From the Project

No Dockerfile, docker-compose, CI, Makefile, pre-commit, mypy configuration or coverage configuration. `CLAUDE.md` and `docs/PLAN.md` overstate status, including the 100% eval score and the race test.

## 5. Fix Plan

Phase B in the brief's order, then Phase C:

| Step | Work | Estimate |
|---|---|---|
| 1 | Security, including user-scoped reads | 3 days |
| 2 | Database integrity | 1 day |
| 3 | Booking correctness | 0.5 day |
| 4 | Safety layer | 2 days |
| 5 | AI workflow | 1 day |
| 6 | Retrieval and sync | 1 day |
| 7 | Privacy | 1 day |
| 8 | Reliability | 1 day |
| 9 | API contract | 0.5 day |
| 10 | Quality | 1.5 days |
| 11 | Delivery | 1 day |

Total: about 14 working days.

## Recommendations

Outside the brief, so not planned:
- Notify patients when a doctor is suspended or cancels.
- Add a crisis support line for self-harm alerts, once its details are confirmed with a clinician.
- Add more specialties. Only 3 exist, so most symptoms lead to General Medicine.
