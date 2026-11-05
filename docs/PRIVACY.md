# MediMatch AI: Privacy

What personal data the backend holds, where it goes, and how long it stays. This describes the code, and is not legal advice.

## Data Stored in Supabase

| Data | Table | Removed when |
|---|---|---|
| Name, phone, role | `profiles` | Patient closes the account: name and phone are cleared, the row stays because appointments reference it |
| Email, password hash | `auth.users` | Patient closes the account: email is replaced, password randomized, sign-in banned |
| Chat messages | `messages` | Patient erases chat history, closes the account, or the retention period ends |
| Assistant progress | `conversations.graph_state` | Same as messages, since it is on the conversation |
| Symptoms and emergency flag | `patient_symptom_sessions` | Same as messages |
| Appointments | `appointments` | Kept as records of care. A closed account shows as "Deleted Patient" |
| Doctor credentials | `doctor_credentials`, private bucket | No deletion path yet |
| Audit events | `audit_logs` | Kept. Entries hold ids and field names, not names, emails or phone numbers |

**Consent:** the API refuses to store symptoms until the patient has agreed, recorded in `profiles.ai_consent_at`. An emergency still gets its alert without consent, and nothing the patient wrote is stored.

**Retention:** chats untouched for `CHAT_RETENTION_DAYS` (365 by default) are erased by `backend/scripts/purge_expired.py`, which must be scheduled daily.

## Sent to Third Parties

| Provider | What it receives | What it does not receive |
|---|---|---|
| **Groq** | The latest 12 chat messages after redaction for the hidden analysis step, and the latest 8 for the reply, plus the system prompts. A turn makes two calls, or three if a reply needs rewriting. Emotional topics, including self-harm the rules did not catch, reach Groq redacted | Patient ids, account details, stored names |
| **Pinecone**, embedding | Redacted symptom keywords for search. For doctors: specialties, qualifications, years of experience, redacted bio and clinic, city | Doctor names, fees, phone numbers, emails |
| **Pinecone**, index | Each approved doctor's vector, id, specialty names and ids, city and status | Any patient data |
| **Supabase** | Everything in the table above, as the database host | Nothing is held back |

Emergency messages caught by the rules go to no third party. Messages the rules do not catch reach Groq, redacted.

## Redaction Limits

`backend/app/ai/privacy.py` removes emails, phone numbers, long ID numbers, street-level addresses and names in common phrasings, in English and Bangla. Rules cannot find every name: "the doctor said Rahim should rest" is not redacted. Treat redaction as reducing exposure, not ending it.

## Before Real Patients

- **Model provider terms:** redacted patient text goes to Groq. Check Groq's current data retention and training terms for this account, and decide whether they are acceptable.
- Sign data processing agreements with Groq, Pinecone and Supabase, as required.
- Have a lawyer review the consent wording and retention period against Bangladeshi law.

## Logs

Logs are JSON with a request id, method, path, status and timing. They hold no message text, query strings, emails or phone numbers, and exceptions are logged by type only. Tests enforce this for the safety module, the LLM client and request logging.

## Conversation State

- The patient's emotional state is inferred for one reply's tone. It is never saved.
- `conversations.graph_state` holds the details gathered, specialty scores and goal labels for the questions asked. It holds no message text, and it is erased with the conversation.
- `routing_log` in that state records why a route was chosen: specialty, confidence, reason, and labels for the answers that drove it. It stays out of `audit_logs` on purpose, because audit logs outlive chat deletion and would keep a mental-health route tied to a patient.
- The log line for a route holds the specialty and confidence with no ids, so it cannot be tied to a patient.
- Self-harm messages are stored like any other message when the patient has consented, and also in `patient_symptom_sessions` as an emergency record. Without consent nothing is stored.
