# MediMatch AI: UI Audit

Step 1 of the visual redesign, written 2026-11-05 before any code changed. It covers commit `5a3999a`, which has the paused navy and beige design.

## How This Was Done

- **Screenshots:** 76 full-page captures at 360x800, 768x1024 and 1440x900, in [`web/screenshots/before/`](../web/screenshots/before/). There are 25 screens at three sizes, plus one long Bangla profile at 360px. They use the mocked API, so the doctors and text are test data.
- **Automated checks:** all 76 tests passed on these captures. That covers no serious or critical axe issues, no console errors, no failed requests and no sideways scrolling.
- **Reviewed by eye:** every screen at all three sizes, using cropped contact sheets. On long pages only the top of the screen was reviewed this round: home, and the lower parts of account, doctor profile, admin queue and the component gallery on mobile.
- **Not captured:** loading and error states. Empty states were captured for appointments, search and credentials. Loading and error states are tested by behaviour, but they haven't been reviewed visually.
- **Skills:** the local copies in `.claude/skills/` were used, and every URL was fetched except one.

| Source | Result |
|---|---|
| Taste Skill site | Fetched |
| Web Design Guidelines, and the rules it points to | Fetched |
| Awesome Design | Fetched. It has no healthcare system. |
| Playwright CLI | Fetched |
| Image to Code on GitHub | **404.** The local copy in `.claude/skills/image-to-code/` is available. |

`docs/PLAN.md` no longer exists, because it was removed in the cleanup as stale. `docs/UI_REVIEW.md` was removed too, and the brief recreates it in Step 5.

## Summary

Nothing is broken. The problem is that the look is applied on top of the product instead of coming from it.

1. **The photographs have nothing to do with booking a doctor.** I added them in the last redesign. See the inventory below.
2. **The slip shape is decoration repeated everywhere.** The notched navy banner sits on top of 15 app screens, even when it only holds one word such as "Account". It pushes content down and breaks the rule in `docs/UI_PRINCIPLES.md` against hero headers inside the app.
3. **The app screens are thin.** Below the banner, most screens have a small cluster of content and then empty beige.
4. **The design rules were broken by the last redesign.** AI content lost its violet, the serif is gone, and the code now uses more than two radius values and motion longer than 200ms.
5. **Bangla can't be chosen.** There is no language switch, and `bn.json` holds only 3 strings. Bangla text from the API renders well, but the interface is English only.

## Image and Asset Inventory

### Proposed for deletion

| Asset | Used in | Shows | Relevant? | Why |
|---|---|---|---|---|
| `web/public/images/rickshaws.webp` | Home how-it-works, sign-in and register panel | Cycle rickshaws on a Dhaka street | **No** | A street scene. It doesn't help anyone book a doctor. |
| `web/public/images/ahsan-manzil.webp` | Home doctors section, in a circle | Part of a historic palace in Dhaka | **No** | A tourist landmark with no link to health care. |
| `web/public/images/buriganga.webp` | Home browse section | A man rowing on the Buriganga River | **No** | An unrelated landscape. |
| `web/public/images/dmc-1940s.webp` | Home hero, behind the live slip | Dhaka Medical College in the 1940s | **No** | The closest to relevant, but it's an 80-year-old archive photo, and it wrongly suggests a link with that hospital. |
| `web/src/locales/image-credits.json`, and the footer credits | Home footer | Credits for the four photos | **No** | Only needed for those photos. |
| `web/src/assets/hero.png` | Nothing | Purple abstract stacked 3D shapes | **No** | Vite template leftover. My cleanup missed it. |
| `web/src/assets/react.svg` | Nothing | React logo | **No** | Vite template leftover. |
| `web/src/assets/vite.svg` | Nothing | Vite logo | **No** | Vite template leftover. |

Also proposed for removal, because they are decorative shapes rather than files:

| Item | Where | Why |
|---|---|---|
| `.slip` and `.slip-stub` notched masks | `web/src/index.css`, used on banners, doctor rows, appointment rows, home and auth | Decoration repeated on every screen. |
| Slip logo mark | `web/src/components/layout/logo.tsx`, `web/public/favicon.svg` | The brief asks for a simple wordmark. On a phone the logo now shows only the mark. |
| Giant `MediMatch` footer wordmark | Home | Decoration that adds length. |
| Dashed tear line | Home live slip | Part of the slip idea. |

### Keeping

| Asset | Used in | Shows | Why it stays |
|---|---|---|---|
| Lucide icons | 29 files | Interface icons | The one icon set. It needs tidying: most use stroke 1.75, but 10 use 2 or 2.5, and sizes run from `size-3` up to `size-6`. |
| Doctor avatars | Doctor rows, doctor page | Initials on a tint | Matches the policy. |
| `noto-sans-bengali-bengali-wght-normal.woff2` | Bangla text | Font | Required. |

`dm-sans-latin-wght-normal.woff2` is a font rather than an image. It goes if the type system in the brief is used, and Instrument Sans and Source Serif come back.

### Checked and found clean

- No remote images, video or CSS background images.
- No gradients, except the ones used inside the slip masks.
- No emoji in the web source.

Two emoji do appear on screen, and they come from the backend: 🚨 in the emergency alert (`backend/app/ai/safety.py:152`) and ⚠️ in the greeting (`backend/app/services/chat_service.py:23`). The brief says emergency messages stay exactly as received, so the web app can't remove them. Removing them is a small backend text change, and it needs your approval.

## What Looks Template-Like

- The same navy banner opens every app screen, whatever the screen is for.
- Home is a long run of big headings, tiles and images: 7,341px on a phone, or about nine screens.
- The three tiles with a giant word ("BMDC", "Approved", "Reviewed") are the same three-card row the brief bans, in larger type.
- The disc-shaped photo is there for shape, not meaning.
- Filter bars, tables and forms sit straight on beige with no structure around them.
- The auth panel repeats the same promise that the home page already makes.

## Problems Across All Screens

| Area | Finding |
|---|---|
| **Hierarchy** | On app screens the banner is the loudest thing, even though it carries the least. A page title outweighs the patient's next appointment. |
| **Spacing** | Margins change by screen: 16 to 32px gutters on home, a 1280px column on others, full width in the portals, and a narrow column in chat. |
| **Alignment** | Forms stop at about 60% of the width and leave the right side empty. Account uses a two-column layout that no other screen has. |
| **Type** | One family at many sizes. The brief asks for a serif on titles and big numbers. The `font-serif` class still exists and now just gives DM Sans, so it is misleading. |
| **Colour** | The brief's teal and violet are gone. `--ai` is now a navy blue, so AI content has no colour of its own. The sidebar, banner, table headers and doctor stubs are all the same navy, so nothing stands out. |
| **Density** | Admin tables are comfortable but sit under a large banner. Patient screens are sparse rather than calm. |
| **Consistency** | Selected items use three styles: a filled beige bar in the sidebar, a pale grey tint in lists and slots, and an underline in tabs. Sidebar navigation only appears at desktop width. Below that, it moves into a sheet. |
| **Icons** | Sparkles marks AI content. It's a cliché and looks generic. |
| **Motion** | `rise-in` is defined twice in `web/src/index.css`, so the later 600ms style also changes the 200ms toast and sheet motion. Scroll-driven reveals on home break the brief's rule of animating state changes only. |
| **Radius** | Tokens define 4px and 8px, but circles and pill shapes are also used for avatars, step markers and the home disc. |
| **Bangla** | API text renders well at every size checked, with no overflow at 360px. Avatar initials also work. The interface itself can't be switched, and the home copy uses "serial", which needs a proper Bangla phrase. |
| **Empty states** | Written well, but each is a plain box. None has a drawing, and each looks the same as the others. |
| **Hard-coded values** | No raw colours or inline styles were found in components. The exceptions are a few arbitrary sizes in the new home page and `web/src/index.css`. |

## Screen by Screen

Links go to the desktop capture. Each folder also holds `tablet.png` and `mobile.png`.

### Public

| Screen | Critique |
|---|---|
| [Home](../web/screenshots/before/home/desktop.png) | The hero is strong, and the live slip is the best idea on the page because it shows real doctors and times. The rest is too long, and the photos are irrelevant. On mobile the slip's result falls below the first screen. On tablet the hero stacks with a large empty gap. The FAQ answers are hidden in closed panels, so the page shows little of its substance. |
| [Sign in](../web/screenshots/before/sign-in/desktop.png) | **Bug:** the panel headline runs over the join between photo and navy, so "Your Serial" sits half on the picture. Below desktop width the panel disappears, leaving a small form floating mid-screen. On mobile it has a large gap above it. |
| [Register](../web/screenshots/before/register/desktop.png) | Same panel and same overlap bug. The form itself is clear and well labelled. |
| [Not found](../web/screenshots/before/not-found/desktop.png) | Correct and clear, but bare. The rest of the screen is empty. |

### Patient

| Screen | Critique |
|---|---|
| [Chat](../web/screenshots/before/chat/desktop.png) | The strongest screen. It's a calm single column, clearly labelled, with a good ranked list. AI messages are marked only by a left rule and a small label, because the violet tint is gone. The shortlist's buttons are small, and the fee and soonest time are buried in a text line. On mobile a shortlist fills the whole screen and pushes out the assistant's text. |
| [Chat consent](../web/screenshots/before/chat-consent/desktop.png) | Clear, but it's plain text in a void, and the most important decision on the screen doesn't look like one. |
| [Chat emergency](../web/screenshots/before/chat-emergency/desktop.png) | Prominent and unmistakable, and the text is intact. The 999 button should be full width at every size, as it is on mobile. The 🚨 emoji comes from the backend. The greeting above it adds noise at the worst moment. |
| [Doctor search](../web/screenshots/before/doctor-search/desktop.png) | The fee is the biggest thing on each row, which is the wrong signal. Next available time, which is what a patient most wants, is missing. At tablet width the filters are cramped: "Any spe" and "For example, Dl" are both cut off. |
| [Search empty](../web/screenshots/before/doctor-search-empty/desktop.png) | Good copy. It looks like any other box. |
| [Doctor detail](../web/screenshots/before/doctor-detail/desktop.png) | The layout is the best of the app screens. The name is oversized compared with everything else. The day strip is sparse with only three days. The selected state is weak and pale. |
| [Appointments](../web/screenshots/before/appointments/desktop.png) | The time-first stub works. It's the one use of the slip that carries meaning, though the status badge is too faint. |
| [Appointments empty](../web/screenshots/before/appointments-empty/desktop.png) | Clear next step. It spends a banner and a box on one sentence. |
| [Account](../web/screenshots/before/account/desktop.png) | Well organised. The email field looks disabled but not clearly. The two destructive actions are close to each other, and the red button is the loudest thing on the page, which is wrong for a rare action. |

### Doctor

| Screen | Critique |
|---|---|
| [Onboarding](../web/screenshots/before/doctor-onboarding/desktop.png) | The stepper is too small to carry the page. The form stops at half width. On mobile the banner and stepper take up half of the screen before the first field. |
| [Profile](../web/screenshots/before/doctor-profile/desktop.png) | The warning about re-review is clear and in the right place. It's a long, single form with no grouping. The specialties grid is uneven. |
| [Credentials](../web/screenshots/before/doctor-credentials/desktop.png) | Two boxes sit side by side with no clear order. The empty state doesn't lead the doctor to the upload next to it. |
| [Verification](../web/screenshots/before/doctor-verification/desktop.png) | The timeline is right for this content. The status is the most important fact, yet it's a tiny badge inside the banner. |
| [Availability](../web/screenshots/before/doctor-availability/desktop.png) | The week grid is the right structure. Empty days dominate, and "No times" repeats seven times. On tablet and mobile it becomes a long list. Booked and free slots differ only by a pale tint and a lock. |
| [Appointments](../web/screenshots/before/doctor-appointments/desktop.png) | Same as the patient view, and fine. It's sparse for a doctor's working day. |

### Admin

| Screen | Critique |
|---|---|
| [Queue](../web/screenshots/before/admin-queue/desktop.png) | The split pane is right. The profile facts rule lines are heavy. Approve and Reject sit side by side at the top, before the admin has read the documents, so a slip is more likely. Tabs are cut off at 360px ("Susp"). |
| [Doctors](../web/screenshots/before/admin-doctors/desktop.png) | A solid table. A "Review" button on every row is repetitive, and the row itself could be the link. |
| [Patients](../web/screenshots/before/admin-patients/desktop.png) | Fine, but it's two rows and a huge banner on an empty page. |
| [Specialties](../web/screenshots/before/admin-specialties/desktop.png) | Fine. Red delete icons on every row are louder than the data. Descriptions disappear on mobile. |
| [Audit log](../web/screenshots/before/admin-audit-log/desktop.png) | The right structure. Raw codes such as `APPROVE_DOCTOR` and `old_status: pending` aren't human. At 360px the table scrolls sideways inside its box with no visible hint, and the date filters use the browser's `mm/dd/yyyy`, which is wrong for Bangladesh. |

### Internal

| Screen | Critique |
|---|---|
| [Component gallery](../web/screenshots/before/dev-components/desktop.png) | Development only, so not a patient concern. Useful for checking primitives in the redesign. |
| [Long Bangla profile](../web/screenshots/before/bangla/mobile.png) | Renders well, with no overflow at 360px. The Bangla headline is tall but readable. |

## What the Brief Says That Needs a Decision

1. **Colours and type.** This brief returns to the teal, violet and serif system. Your last request was navy and beige, because you didn't like the earlier look. This is the brief's own system, so I'll follow it unless you say otherwise.
2. **Density.** You told me the earlier version was too minimal, and this brief asks for generous whitespace. I propose keeping the brief's rules while making each screen fuller, with real content such as next available times, instead of large decorative areas.
3. **Backend emoji.** Removing 🚨 and ⚠️ means changing two backend strings. Everything else in this redesign stays in `web/`.
4. **Bangla.** The brief says Bangla must render well, but a language switch and full translation are a separate piece of work. Translating medical safety text needs a Bangla-speaking reviewer. I propose adding the switch only if you want it now, and leaving translation out of this redesign.
5. **Reference systems.** I propose IBM Carbon and Cal.com, which `docs/DESIGN.md` already names. Carbon suits dense tables, and Cal.com suits scheduling. Awesome Design lists no healthcare system.

## Next Step

Nothing proceeds to Step 2 until you approve the deletion list above.
