# MediMatch AI: Design System

The source of truth for the web UI. Tokens live in `web/src/styles/tokens.css` and map into the Tailwind theme. Components never use raw colours or magic numbers. If this file and the code disagree, fix one of them in the same change.

**Tone:** calm, clinical but human. Striking on the home page through large type and real product, generous on patient screens, dense on admin screens.

**Source:** the visual and copy rules here follow the landing page design skill the owner adopted on 2026-11-06. `web/tests/design-rules.test.ts` enforces them. Where this file and the skill differ, the exception is listed under "Exceptions".

## 1. Reference systems

Two references inform the structure. We borrow no colour, logo, typeface or brand expression from either. Both sources are analyses of the companies' marketing sites, so we borrow proportions and habits, not product components.

| Reference | What we borrow | What we leave |
|---|---|---|
| **IBM Carbon** | One accent carrying most actions; 1px hairlines and tone steps in place of shadows; underlined tabs; a compact 14px and 12px text pair for dense views; light-handed display type that stays calm at large sizes | Square corners, blue, Plex, the dark footer |
| **Cal.com** | The 4, 8, 12, 16, 24, 32, 48 spacing rhythm; 40px controls; real interface shown as imagery instead of illustration; scheduling surfaces built as plain grids | Black buttons, pill navigation, rating stars, testimonial cards, large rounded cards |

## 2. Colour

| Token | Value | Use |
|---|---|---|
| `--ink` | `#000000` | Primary text |
| `--muted` | `#494949` | Secondary text |
| `--surface` | `#FFFFFF` | Panels and inputs |
| `--canvas` | `#EAEAEA` | Page background |
| `--border` | `#D8D8D8` | Dividers and panel edges (decorative) |
| `--border-control` | `#595959` | Boundaries of inputs and controls |
| `--primary` | `#161616` | Actions, links, focus |
| `--primary-hover` | `#333333` | Hover |
| `--primary-pressed` | `#000000` | Active state |
| `--primary-tint` | `#F4F4F4` | Selected rows and days, and the how it works, closing and sign-in fields |
| `--ai` | `#805090` | AI-generated content only |
| `--ai-tint` | `#F3ECF6` | Background of AI content only |
| `--danger` | `#B3261E` | Emergencies and destructive actions only |
| `--danger-pressed` | `#8C1D18` | Active destructive button |
| `--danger-tint` | `#FCEBEA` | Destructive confirmation backgrounds |
| `--warning` | `#8A5300` | Warning text and icons |
| `--warning-tint` | `#FDF3E3` | Warning backgrounds |
| `--success` | `#1E7A3C` | Success text and icons |
| `--success-tint` | `#E8F5EC` | Success backgrounds |

### Contrast matrix

Measured, not estimated. AA requires 4.5:1 for text and 3:1 for control boundaries. A unit test enforces this table.

| Foreground | Background | Ratio |
|---|---|---|
| ink | surface / canvas | 21.00 / 17.46 |
| ink | primary-tint / ai-tint | 19.09 / 18.14 |
| muted | surface / canvas | 9.00 / 7.48 |
| muted | primary-tint / ai-tint | 8.19 / 7.78 |
| white | primary / primary-hover / primary-pressed | 18.10 / 12.63 / 21.00 |
| primary | surface / canvas | 18.10 / 15.04 |
| primary-hover | primary-tint | 11.49 |
| ai | surface / ai-tint | 6.06 / 5.23 |
| white | danger / danger-pressed | 6.54 / 9.11 |
| danger | surface / danger-tint | 6.54 / 5.67 |
| warning | surface / warning-tint | 6.33 / 5.76 |
| success | surface / success-tint | 5.38 / 4.79 |
| border-control | surface / canvas | 7.00 / 5.82 |

`--border` is 1.43:1 and must never be the only boundary of a control.

The look is black and white on grey. Violet appears only on AI content and red only on emergencies and destructive actions. The values were sampled from the MyDNA concept by Levi Wilson, and MediMatch is inspired by it, not affiliated with it. See `design-system/source/report.md`.

No dark theme in this round.

## 3. Typography

One typeface, Manrope, self-hosted as variable woff2 and preloaded. Noto Sans Bengali is its Bangla fallback and downloads only when Bangla appears through `unicode-range`. No italics, and nothing above weight 600.

Every piece of text uses a named style, defined once with `@utility` in `web/src/index.css`. Never set a loose size or weight. Sizes are Tailwind scale steps.

| Group | Styles | Use |
|---|---|---|
| Heading | `heading-1` 60/60, `heading-2` 48/48, `heading-3` 36/40, `heading-4` 30/36, `heading-5` 24/32, `heading-6` 20/28, all semibold | Page and section headings. `heading-1` is the hero |
| Title | `title-1` 20/28, `title-2` 18/28, `title-3` 16/24, `title-4` 14/20, `title-5` 12/16, all medium | Card titles, labels that lead a block |
| Body | `body-1` to `body-3` 16/24 semibold, medium, regular; `body-4` to `body-6` 14/20 semibold, medium, regular; `body-7` 18/28 regular; `body-8` 20/28 regular | Running text. 7 and 8 are lead text |
| Button | `button-lg` 18/28, `button-md` 16/24, `button-sm` 14/20, `button-xsm` 12/16, all semibold | Text inside buttons only |
| Caption | `caption-1` 14/20 medium, `caption-2` 14/20 regular, `caption-3` to `caption-5` 12/16 semibold, medium, regular | Metadata and fine print |

- Fees, times and counts use `font-variant-numeric: tabular-nums`.
- Prose is capped at 66ch. The hero heading and subheading are capped at 680px, with line breaks where the thought breaks.
- Headings use `text-wrap: balance` and running text `text-wrap: pretty`. Headings and buttons use sentence case.
- The hero heading alone has a left to right gradient on its text, `#000000` to `#666666`.
- No hyphens inside copy, no exclamation marks.

## 4. Space, Layout and Shape

- **Spacing:** only 0, 2, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80 and 96px.
- **Grid:** 1200px maximum in the app and 1440px on the home page, with 16px side margins on mobile.
- **Breakpoints:** 360 is the minimum supported width, then `md` 768 and `lg` 1024. Chat stays one column at 720px maximum.
- **Density:** patient screens use 16px text. Admin screens use 14px text.
- **Controls:** buttons have 8px vertical and 12px horizontal padding. They are at least 40px high on desktop and 44px at mobile widths.
- **Radius:** Tailwind values only. `rounded-full` for buttons and navigation links, `rounded-lg` 8px for fields, `rounded-xl` 12px for panels, `rounded-2xl` 16px for the floating bar, the home message box and the hero, which is a white card on the grey page. When a shape sits inside another with a gap under 32px, inner radius = outer radius minus the gap, applied only if the result is above 2.
- **Borders:** all the way around a card or not at all. Hairlines between rows of a list are dividers, not card borders.
- **Backgrounds:** flat, never a gradient. No dark theme yet; if one is added, use only `#000000`, `#181818`, `#1F1F1F`, `#272727`, `#313131` and `#131209`.
- **Elevation:** borders first. `--shadow-overlay` is the only shadow, for popovers, dialogs and sheets.
- **Focus:** a 2px `--primary` ring with 2px offset, identical everywhere.

## 5. Motion and Imagery

- Every transition uses `cubic-bezier(0.22, 1, 0.36, 1)`, 300ms for colour and opacity on hover, 500ms for position. Never shorter than 200ms.
- Animate position only through `transform`. Under reduced motion, movement becomes a plain opacity change.
- **Navigation:** a compact translucent bar floats off the top edge, centred and sized to its content. The menu icon turns into a cross. On mobile the menu is a full height panel whose links arrive 60ms apart, capped at 400ms.
- **Scroll reveals:** home sections rise 32px and fade over 700ms, once, through `IntersectionObserver`.
- **Hero scroll:** the hero card sinks back up to 8% and fades by half as the first screen leaves. In how it works, the progress bar follows the scroll, later steps wait at 30% opacity and the shortlist arrives row by row. Scroll position reaches CSS through one variable, written at most once a frame, and the hero stays still under reduced motion.
- **Tagline reveal:** on the home page, one large statement starts at 30% opacity. Words reach full colour one at a time through a scroll listener throttled with `requestAnimationFrame`, and stay lit once read.
- **Loading:** skeletons shaped like the layout. A button that is busy pulses, with no spinner.
- Icons: Phosphor, in sizes 16, 20 and 24. They support labels and never replace them, except on `IconButton`, which requires an accessible name and a tooltip.

### Exceptions

- Noto Sans Bengali sits beside Manrope because Manrope has no Bangla.
- Bangla headings use a line height of 1.25, because conjuncts clip at 1.
- Buttons are 44px high at mobile widths, for touch targets.
- Buttons are always pills, so the nested radius formula does not apply to them, on the owner's choice.
- There are no testimonials or customer logos, because none exist. The live doctor register is the proof.

### Imagery

This policy exists because irrelevant photographs were added to the product once. Keep them out.

- **Banned:** stock photography, photos of doctors or patients, landmark or street photos, AI-generated art, decorative blobs and gradients.
- **Allowed:** (a) real product interface, (b) simple custom SVG drawings in our palette with one or two colours and a consistent stroke, used only for empty states and onboarding, (c) Phosphor icons, (d) type and space.
- Doctor avatars are initials on a tint, unless the doctor uploaded a photo.
- The home page shows the product itself in `ProductStage`, with live data from the API, and marks it as an example.
- `ProductStage` holds no inputs or buttons. A visitor must never mistake the example for the real message box.

## 6. Component Inventory

**Primitives** in `web/src/components/ui/`, on Radix with cva variants where a component has variants: Button, IconButton, Input, Textarea, Select, Combobox, Checkbox, Radio, Switch, Label and Field, Badge, Avatar, Tooltip, Dialog, Sheet, Popover, Tabs, Toast, Skeleton, Table, Pagination, EmptyState, Banner (info, warning, emergency). `ConfirmDialog` and `ErrorState` are shared compositions of these. Every state appears on `/dev/components`, a route excluded from production builds.

**Domain components:**
| Component | Note |
|---|---|
| DoctorCard | Compact and detailed variants; no stars, ever |
| VerificationBadge | States its status in words as well as colour |
| SlotPicker | Day strip and time grid, arrow-key navigation, Asia/Dhaka shown |
| AppointmentRow | Time first, tabular. The next visit is featured with a large time |
| ProductStage | The real chat on the home page, played step by step with live doctors. Inert, and labelled as an example |
| LanguageSwitch | Switches English and Bangla, and remembers the choice |
| ChatMessage | AI and patient differ by layout and a "Written by AI" label, on the violet tint |
| ChatComposer | Chips from the assistant, or fixed suggestions for older replies, and "Show me doctors now". That control is hidden before the first message, after an alert or a shortlist, and in any conversation that touched self-harm |
| EmergencyNotice | Full width, high contrast, verbatim text, `tel:` link, not dismissible, nothing beneath it |
| CrisisNotice | Self-harm only. Verbatim text, `tel:` link, not dismissible, nothing beneath it. Calm: white with no red and no siren |
| AIDisclaimer | Persistent, short, not a modal |
| FilterBar | All state in the URL; a Sheet on mobile |
| StatusTimeline | Doctor verification history, including reasons |
| CredentialViewer | Opens files through short-lived signed links |
| CredentialUploader | Checks type and size first, and reports real upload progress |
| RecommendationList | A ranked list with the reason, soonest time and fee; never a carousel |
| AuditLogTable | Sticky header, filters, dense |

## 7. Voice and Tone

We write for someone who is worried and short of time. Plain English, short sentences, second person. Text is written for translation, so strings are whole sentences held in i18n keys, never assembled from fragments.

- **Be specific.** "Tuesday 4 Nov, 7:30 PM (Dhaka time)", not "soon".
- **Don't reassure about symptoms, and don't alarm.** Never "don't worry" or "it's probably nothing". Say what happens next.
- **Name the action.** "Book This Slot", "Cancel Appointment", not "Submit" or "Confirm".
- **Errors say what happened and what to do.** "We couldn't reach the server. Your message is saved here. Try again."
- **Empty states point forward.** "No appointments yet. Describe your symptoms to find a doctor."
- **No filler.** No "Welcome back, Karim!", "Oops!" or exclamation marks.
- **Confirmations name the consequence.** "Cancel your appointment with Dr. Hasan on Tuesday at 7:30 PM? This frees the slot for other patients."
- **AI is plainly AI.** "Written by AI. Not medical advice."
