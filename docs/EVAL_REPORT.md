# MediMatch AI: Evaluation Report

Results from 2026-11-04. All phrases and queries were written for testing. No patient data was used.

**Summary:** rules catch direct statements, and the model catches indirect ones, so neither is enough alone. Recommendation precision is modest, partly because of how little demo data exists. The earlier 100% score was not a real measurement.

## Emergency Detection

### Rules on Wording They Had Not Seen

Scores on phrases the rules were built from mean nothing, so each batch was measured once, before any rule was added for it.

| Batch | Phrases | Missed | Notes |
|---|---|---|---|
| Audit, original rules | 118 | 93 (79%) | Includes common wording such as "my chest hurts" |
| Batch 2, after the first rewrite | 80 | 49 (61%) | Plain phrasing, English, Bangla and Banglish |
| Batch 3, after adding concept matching | 81 | 71 (88%) | Deliberately indirect, such as "half his smile is gone" |

**Conclusion:** rules alone cannot keep up with how people describe an emergency. All of these phrases now pass as regression tests, but that says nothing about the next unseen phrase.

False alarms on ordinary messages, measured on the same unseen batches:

| Batch | Ordinary messages | False alarms |
|---|---|---|
| Batch 2 | 24 | 0 |
| Batch 3 | 48 | 2 (4%), both then fixed |

Mentions of past events, such as "my grandfather had a stroke last year", trigger the alert on purpose.

### The Classifier as a Second Layer

The real LLM was tested on its own, using batches 2 and 3, with `nvidia/nemotron-3-ultra-550b-a55b:free`.

| Result | Count |
|---|---|
| Emergencies flagged | 23 of 24 |
| Ordinary messages wrongly flagged | 1 of 12 |

This included Bangla and transliterated Bangla.

**Three limits on that result:**
1. **The sample is small.**
2. **It measured an earlier prompt.** That prompt flagged a plain headache as an emergency during the end-to-end run, so it was tightened to name danger signs. The new prompt passed the end-to-end run, but its score is **not measured**: a rerun hit the free tier's limit of 50 requests a day. Treat 23 of 24 as an upper estimate until it is rerun.
3. **It depends on the provider.** When the LLM is down or rate limited, only the rules run. That is what happened during the rerun.

Rerun with:

```bash
python backend/scripts/eval_emergency.py --emergencies 30 --ordinary 15
```

### Fixed Tests

| Test | Result |
|---|---|
| Must trigger, including negation and keyboard variants | 119 of 119 |
| Regression phrases from batches 2 and 3 | 161 of 161 |
| Must not trigger | 113 of 113 |
| Prompt injection against a model returning unsafe text in every field | 8 of 8 blocked |

## Output Guard

| Measure | Result |
|---|---|
| Audit, original guard | Let 25 of 32 unsafe replies through |
| Rewritten guard, on replies it was tuned on | 33 of 33 blocked |
| Rewritten guard, on 16 unseen replies | **Let all 16 through** |

The guard is not a reliable filter. **Since 2026-11-05 the model writes normal replies**, so this gap can reach a patient: the system prompt and this guard are the only checks on what it says. Review real conversations before patients use this.

## Recommendations

The old eval passed the expected specialty in as the query, so it could not fail. Its 100% score is withdrawn.

The new eval gives retrieval symptom text only, with every specialty allowed, using the real embedding model and index.

| Measure | Result |
|---|---|
| Queries | 28, across 3 specialties, including Banglish |
| Hit@3, at least one right doctor in the top 3 | **96.4%** (27 of 28) |
| Precision@3, share of the top 3 that are right | **38.1%** |
| Retrieval mode | Vector search on all 28 |

**How to read this:**
- **Precision is capped by the demo data.** With 3 specialties and few doctors in each, the top 3 often cannot all match. A precision of 33% is roughly what random choice among 3 specialties gives, so ranking is adding little.
- **This is retrieval alone.** In the real flow, the assistant also picks specialties and filters by them, so what a patient sees should be better. That full path was not measured, because the LLM limit was reached.
- **Only 5 of 7 approved doctors were indexed** when this ran.

The one failure was Banglish: "matha betha ar matha ghurano".

Rerun with `python backend/scripts/eval_recommendations.py`.

## Not Measured

- The tightened classifier prompt.
- Recommendation quality through the full assistant flow.
- Any phrase set reviewed by a clinician. **All emergency phrases here were written without clinical input.**
