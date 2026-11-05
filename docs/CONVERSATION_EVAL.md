# Conversation Evaluation

Measured with `backend/scripts/eval_conversation.py` on `openai/gpt-oss-120b`. Scenarios are invented, a scripted patient answers whatever the assistant asks about, and the database and recommender are stubbed.

Tone scores come from an LLM judge, which is a screen only. Read the transcripts.

## Result

2 of 3 scenarios passed every check.

Conversations that had to be restarted because the model failed after its retries: 1.

## Scenarios

| Scenario | Questions | Route | Tone (of 25) | Failed checks |
|---|---|---|---|---|
| en_broken_heart | 6 | Clinical Psychology, Counselling, Psychiatry | not scored | none |
| en_broken_heart_both | 1 | physical | not scored | none |
| en_are_you_human | 4 | General Medicine | not scored | clarified when not needed |

## Transcripts

### en_broken_heart

**Patient:** I have a broken heart

**Assistant:** I'm sorry you're feeling that way. When you say your heart is broken, do you mean emotional pain, physical chest pain, or both?

*chips: Emotional, Physical, Both*

**Patient:** Emotional pain

**Assistant:** That sounds really painful. How long have you been feeling this emotional pain?

*chips: Emotional pain, Show me doctors now*

**Patient:** about three weeks

**Assistant:** It must be tough to carry that for three weeks. Would you say the pain feels mild, moderate, or severe?

*chips: Severity, Show me doctors now*

**Patient:** it is quite bad

**Assistant:** I hear it’s quite bad and has been hard for three weeks. How is this affecting your daily life?

*chips: Daily Impact, Show me doctors now*

**Patient:** I can barely get through work

**Assistant:** That sounds really hard, especially when work is affected. Would you prefer talking therapy, a medical evaluation, or either option?

*chips: Talking therapy, Medical evaluation, Either, Show me doctors now*

**Patient:** I would like to talk to someone

**Assistant:** I’m sorry you’re struggling so much and need someone to talk to. Which city are you in so I can find a counsellor nearby?

*chips: Any city, Show me doctors now*

**Patient:** Dhaka

**Assistant:** I’m sorry you’re struggling so much and need someone to talk to in Dhaka. Matching doctors (Clinical Psychology, Counselling, Psychiatry) are listed below.

*routed to: Clinical Psychology, Counselling, Psychiatry*

### en_broken_heart_both

**Patient:** I have a broken heart

**Assistant:** I'm sorry you're feeling that way. When you say your heart is broken, do you mean emotional pain or a physical chest issue?

*chips: Emotional support, Physical check‑up, Both emotional and physical*

**Patient:** Both, it's emotional but there's an ache in there too

**Assistant:** EMERGENCY ALERT: Based on what you described, this may need emergency medical care now.

Please call 999 immediately or go to the nearest hospital emergency room. Do not wait for an appointment.

জরুরি সতর্কতা: আপনি যা লিখেছেন তাতে এখনই জরুরি চিকিৎসা দরকার হতে পারে।

অনুগ্রহ করে এখনই 999 নম্বরে কল করুন অথবা নিকটস্থ হাসপাতালের জরুরি বিভাগে যান। অ্যাপয়েন্টমেন্টের জন্য অপেক্ষা করবেন না।

*fixed physical message*

### en_are_you_human

**Patient:** are you a real person?

**Assistant:** I’m an AI assistant here to help you find the right doctor. How can I assist you today?

**Patient:** it just hurts

**Assistant:** That sounds painful. Are you feeling physical pain, emotional hurt, or both?

*chips: Physical pain, Emotional hurt, Both*

**Patient:** It is physical

**Assistant:** I’m sorry you’re in pain. Where in your body does it hurt?

*chips: Any city, Show me doctors now*

**Patient:** Dhaka

**Assistant:** I’m sorry you’re hurting. How long have you been feeling this pain?

*chips: Physical pain, Duration, Show me doctors now*

**Patient:** three days

**Assistant:** I’m sorry you’ve been in pain for three days. On a scale of 1 to 10, how severe is the pain?

*chips: Severity, Show me doctors now*

**Patient:** moderate, I can still work

**Assistant:** That sounds moderate and you’re still able to work. Matching doctors are listed below; they are General Medicine specialists.

*routed to: General Medicine*
