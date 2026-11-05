# MediMatch AI: Design System

The source of truth for the web UI. Tokens live in `web/src/styles/tokens.css` and map into the Tailwind theme. Components never use raw colours or magic numbers. If this file and the code disagree, fix one of them in the same change.

**Tone:** calm, clinical but human, editorial. Striking on the home page through large type and real product, generous on patient screens, dense on admin screens.

## 1. Reference systems

Two references inform the structure. We borrow no colour, logo, typeface or brand expression from either. Both sources are analyses of the companies' marketing sites, so we borrow proportions and habits, not product components.

| Reference | What we borrow | What we leave |
|---|---|---|
| **IBM Carbon** | One accent carrying most actions; 1px hairlines and tone steps in place of shadows; underlined tabs; a compact 14px and 12px text pair for dense views; light-handed display type that stays calm at large sizes | Square corners, blue, Plex, the dark footer |
| **Cal.com** | The 4, 8, 12, 16, 24, 32, 48 spacing rhythm; 40px controls; real interface shown as imagery instead of illustration; scheduling surfaces built as plain grids | Black buttons, pill navigation, rating stars, testimonial cards, large rounded cards |

## 2. Colour

| Token | Value | Use |
|---|---|---|
| `--ink` | `#14122B` | Primary text |
| `--muted` | `#5C5A73` | Secondary text |
| `--surface` | `#FFFFFF` | Panels and inputs |
| `--canvas` | `#F6F6FA` | Page background |
| `--border` | `#E3E1F0` | Dividers and panel edges (decorative) |
| `--border-control` | `#8582A0` | Boundaries of inputs and controls |
| `--ink-field`, `--ink-raised`, `--ink-line` | `#14122B`, `#211F3D`, `#3A3859` | Ink fields on the home page and auth panel |
| `--on-ink`, `--on-ink-muted` | `#FFFFFF`, `#C8C6D9` | Text on ink |
| `--primary` | `#00806C` | Actions, links, focus |
| `--primary-hover` | `#00695A` | Hover; text on `--primary-tint` |
| `--primary-pressed` | `#005247` | Active state |
| `--primary-tint` | `#E6F4F1` | Selected rows and days |
| `--ai` | `#5A4BD1` | AI-generated content only |
| `--ai-tint` | `#EEECFB` | Background of AI content only |
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
| ink | surface / canvas | 18.24 / 16.92 |
| ink | primary-tint / ai-tint | 16.14 / 15.66 |
| muted | surface / canvas | 6.63 / 6.16 |
| muted | primary-tint / ai-tint | 5.87 / 5.70 |
| white | primary / hover / pressed | 4.88 / 6.63 / 9.14 |
| primary | surface / canvas | 4.88 / 4.53 |
| primary-hover | primary-tint | 5.86 |
| ai | surface / ai-tint | 6.25 / 5.36 |
| white | danger / danger-pressed | 6.54 / 9.11 |
| danger | surface / danger-tint | 6.54 / 5.67 |
| warning | surface / warning-tint | 6.33 / 5.76 |
| success | surface / success-tint | 5.38 / 4.79 |
| border-control | surface / canvas | 3.69 / 3.42 |

**Two rules these numbers create:**
- `--primary` as text on `--primary-tint` is only 4.32:1, so text on that tint always uses `--primary-hover`.
- `--border` is 1.29:1 and must never be the only boundary of a control.

No dark theme in this round.

## 3. Typography

Two families, plus a Bangla fallback, self-hosted as variable woff2 with `font-display: swap`. Instrument Sans is preloaded. Noto Sans Bengali uses `unicode-range`, so it downloads only when Bangla appears.

- **UI:** Instrument Sans, then Noto Sans Bengali, then `system-ui`.
- **Display:** Source Serif 4, for page titles and big numbers only, then Noto Sans Bengali for Bangla titles.

| Token | Size / line height | Use |
|---|---|---|
| `--text-xs` | 12 / 16 | Metadata and table captions; never for sentences a patient must read |
| `--text-sm` | 14 / 20 | Admin body, table cells, helper text |
| `--text-md` | 16 / 24 | Patient body, inputs (avoids iOS zoom), chat |
| `--text-lg` | 18 / 28 | Lead text, section titles |
| `--text-xl` | 24 / 32 | Subpage titles |
| `--text-2xl` | 32 / 40 | Mobile page titles (serif) |
| `--text-3xl` | 44 / 52 | Page titles and big numbers (serif) |
| `--text-4xl` | 64 / 68 | Home section titles (serif) |
| `--text-5xl` | 88 / 92 | Reserved for display (serif) |

- Weights: 400 for body, 500 for labels, 600 for emphasis. The serif stays at 400 so large type reads calm.
- Fees, times and counts use `font-variant-numeric: tabular-nums`.
- Prose is capped at 66ch, within the 60 to 75 character range.
- Headings use `text-wrap: balance`. Headings and buttons use Title Case; body text uses sentence case.
- Line heights above hold for Bangla conjuncts. This is verified with a long Bangla test string at every size.

## 4. Space, Layout and Shape

- **Spacing:** 4px base, from `--space-1` (4) through 8, 12, 16, 24, 32, 48, 64 and 96.
- **Grid:** 12 columns on desktop with 24px gutters and 1200px max width; 4 columns on mobile with 16px gutters and side margins.
- **Breakpoints:** 360 is the minimum supported width, then `md` 768 and `lg` 1024. Chat stays one column at 720px maximum.
- **Density:** patient screens use 16px text and 44px rows. Admin screens use 14px text and 40px rows on desktop.
- **Controls:** 40px high on desktop, 44px on touch and at mobile widths.
- **Radius:** `--radius-sm` 4px (inputs, buttons, badges) and `--radius-md` 8px (panels, dialogs). No other values.
- **Elevation:** borders first. `--shadow-overlay` is the only shadow, for popovers, dialogs and sheets. Page content never has one.
- **Focus:** a 2px `--primary` ring with 2px offset, identical everywhere.

## 5. Motion and Imagery

- Duration 150ms for small state changes and 200ms for overlays, `ease-out`, on `transform` and `opacity` only.
- No bouncing or parallax. Scrolling may change the state of the home page panel, but it never animates decoration. Under reduced motion, changes are immediate.
- Icons: Lucide at stroke width 1.75, in sizes 16, 20 and 24. They support labels and never replace them, except on `IconButton`, which requires an accessible name and a tooltip.

### Imagery

This policy exists because irrelevant photographs were added to the product once. Keep them out.

- **Banned:** stock photography, photos of doctors or patients, landmark or street photos, AI-generated art, decorative blobs and gradients.
- **Allowed:** (a) real product interface, (b) simple custom SVG drawings in our palette with one or two colours and a consistent stroke, used only for empty states and onboarding, (c) Lucide icons, (d) type and space.
- Doctor avatars are initials on a tint, unless the doctor uploaded a photo.
- The home page shows the product itself in `ProductStage`, with live data from the API, and marks it as an example.

## 6. Component Inventory

**Primitives** in `web/src/components/ui/`, on Radix with cva variants where a component has variants: Button, IconButton, Input, Textarea, Select, Combobox, Checkbox, Radio, Switch, Label and Field, Badge, Avatar, Tooltip, Dialog, Sheet, Popover, Tabs, Toast, Skeleton, Table, Pagination, EmptyState, Banner (info, warning, emergency). `ConfirmDialog` and `ErrorState` are shared compositions of these. Every state appears on `/dev/components`, a route excluded from production builds.

**Domain components:**
| Component | Note |
|---|---|
| DoctorCard | Compact and detailed variants; no stars, ever |
| VerificationBadge | States its status in words as well as colour |
| SlotPicker | Day strip and time grid, arrow-key navigation, Asia/Dhaka shown |
| AppointmentRow | Time first, tabular. The next visit is featured with a large serif time |
| ProductStage | The real chat on the home page, played step by step with live doctors. Inert, and labelled as an example |
| LanguageSwitch | Switches English and Bangla, and remembers the choice |
| ChatMessage | AI and patient differ by layout and an "AI-generated" label, on the violet tint |
| ChatComposer | Suggested-answer chips for follow-ups |
| EmergencyNotice | Full width, high contrast, verbatim text, `tel:` link, not dismissible, nothing beneath it |
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
- **AI is plainly AI.** "AI-generated. Not medical advice."
