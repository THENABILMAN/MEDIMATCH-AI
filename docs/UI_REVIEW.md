# MediMatch AI: UI Review Log

Critique of the web UI against `docs/UI_PRINCIPLES.md`, from reviewing the screenshots in `web/screenshots/` at 360x800, 768x1024 and 1440x900.

Screenshots use a mocked API (`web/e2e/support/`) shaped from `backend/scripts/seed.py`. Regenerate them with `npx playwright test screens` from `web/`.

## Round 1 findings and fixes

| Screen | Finding | Fix |
|---|---|---|
| All, 360px | The logo broke into "MediMatc / h" | Logo no longer wraps or shrinks |
| Chat, 360px | Title wrapped to two lines; placeholder was clipped | Smaller title on phones, shorter placeholder, composer grows with its text |
| Chat, 360px | Header actions overflowed once the title stopped wrapping (caught by the sideways-scroll test) | Text labels only on phones |
| Doctor detail | Rules broke between the columns of the facts list | One continuous rule per row |
| Admin doctors and patients, 360px | Status and Review sat off-screen in a scrolling table | Secondary columns hide on phones; name, status and action stay |
| Availability | Past days had shorter headers, so columns misaligned | Fixed header height |
| Availability, 360px | "Week of 2 Nov" wrapped | Kept on one line |
| Onboarding | A blank fee showed as 0, which reads as free | Unset fee shows an empty field |
| Verification | No route back to onboarding after "Finish Later" | "Continue Setup" link while in review |

## Bugs found by the test suite

| Bug | Fix |
|---|---|
| Tabs pointed at panels that did not exist (axe, serious) | `Tabs` now always renders a panel for every tab |
| Signing out or closing an account on a protected page landed on sign-in | Navigate home first, then end the session |
| A message sent while a conversation loaded on a slow network vanished | Send waits until the conversation is ready, and the text is kept |
| The composer reset when the conversation finished loading, wiping typed text | One stable route and composer instance |

## Round 2

All screens at all three sizes pass:
- No sideways scrolling, no console errors, no failed requests.
- axe reports no serious or critical issues.
- Keyboard-only paths work for sign in, sending a chat message, booking a slot and approving a doctor.
- Offline and throttled states work for chat and booking.

**Bangla:** a long Bangla name and biography render in Noto Sans Bengali at 360px with conjuncts intact and no overflow. `/dev/components` shows Bangla at every type size.

**Emergency notice:** full width, high contrast, verbatim backend text, `tel:` link, no dismiss control, no recommendations beneath it. It survives a reload.

**Lighthouse (production build, simulated mobile):** 100 for performance, accessibility and best practices on `/`, `/doctors`, `/login` and `/register`. Largest Contentful Paint 0.8s, Cumulative Layout Shift under 0.04. Signed-in routes need a live session, so they were not scored.

## Taste Skill lint

`lint.mjs` reports 29 failures and 3 warnings. These were reviewed and kept:

- **Hairline (28):** the page-level rule against thin dividers. These are app screens, where Taste's own `app-screens.md` allows quiet borders, and `docs/DESIGN.md` specifies borders first.
- **Emoji (2):** in test fixtures that copy the backend's emergency and disclaimer text verbatim.
- **Shadow (1):** an inset line on sticky table headers, which is a rule rather than elevation.
- **Pulse (2 warnings):** skeleton loading, which stops under reduced motion.
- **Em dash (1 warning):** `—` for empty table cells.
