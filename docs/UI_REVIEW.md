# MediMatch AI: UI Review

Review of the 2026-11-05 redesign against `docs/UI_PRINCIPLES.md`. Before screenshots are in [`web/screenshots/before/`](../web/screenshots/before/) and after screenshots are in [`web/screenshots/after/`](../web/screenshots/after/), at 360x800, 768x1024 and 1440x900.

The review used contact sheets of the after screenshots and live scroll captures of the home page. All desktop screens were reviewed, plus 15 mobile screens. Tablet screens were checked by the automated tests but not reviewed by eye after the redesign, and neither were the remaining mobile screens.

## Automated Results

| Check | Result |
|---|---|
| Playwright, including axe, console, network and sideways scroll on every screen | 97 of 97 |
| Vitest | 46 of 46 |
| Type check, oxlint and production build | Pass, with 3 existing lint warnings |
| Backend tests that need no database | 652 of 653. The other one needs local Supabase, which wasn't running |
| Backend integration tests | Not run, because local Supabase wasn't running |

## Bugs Found During Review

| Bug | Fix |
|---|---|
| Doctor onboarding lost clicks on Save and Continue. Leaving a field cleared its error, the layout moved, and the click landed on nothing. | The button keeps focus until the click finishes, in `OnboardingPage.tsx`. |
| The sign-in panel headline ran across the photo edge. | The panel is now plain type on ink. |
| Search filters were cut off at tablet width. | They use two columns below `lg`. |
| The emergency call button wasn't full width on larger screens. | It's now full width at every size. |
| `rise-in` was defined twice in the CSS. | One definition remains. |

## Screen by Screen

| Screen | What improved | Still weak |
|---|---|---|
| **Home** | The first screen is a large serif headline on ink, with a working message box. A real product panel stays fixed while the conversation plays on scroll, with live doctors and times. | The panel is mostly empty on its first step. |
| **Sign in, register** | The photo is gone. The form sits beside a plain promise, and nothing overlaps. | The ink panel is hidden below `lg`. |
| **Not found** | Larger title. | Still a sparse screen. |
| **Chat** | AI messages use the violet tint again. Doctor names, rank and soonest time are easier to scan, and View and Book is the primary action. | A long shortlist still fills a phone screen. |
| **Chat consent** | Calmer without the banner. | Still plain text on an empty page. |
| **Emergency** | Call button is full width, and the emoji is gone. The text and red block are otherwise unchanged. | The greeting above it remains. |
| **Doctor search** | Soonest time now leads each row, and the fee no longer dominates. | One extra slots request per doctor shown. |
| **Doctor detail** | The selected day and time are solid teal, so they read at a glance. | Few details beyond the profile. |
| **Appointments** | The next visit stands out with a large serif time on a tint. Both patient and doctor views share this. | Sparse when there's one appointment. |
| **Account** | Close Account no longer shouts. | Unchanged layout. |
| **Onboarding** | A full-width stepper carries the page. | Form stays at two-thirds width. |
| **Verification** | The status is now the headline. | "Verification" and "Verified" sit close together. |
| **Availability** | Booked slots are solid teal, and desktop no longer repeats "No times". | Long list on tablet and mobile. |
| **Credentials** | Illustrated empty state. | Unchanged layout. |
| **Admin queue** | Approve and Reject moved below the documents, so admins read first. | No keyboard shortcuts. |
| **Admin tables** | Dense sidebar, no banner. Audit actions read as words. | Details in the audit log are still raw. |

## Remaining Visual Debt

- Date filters use the browser's `mm/dd/yyyy` format.
- Almost all of the interface is still in English, because `bn.json` has only a few strings.
- Loading and error states were not reviewed by eye.
- At 360px the audit table scrolls sideways inside its box, with no visible hint.
