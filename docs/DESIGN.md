# MediMatch AI: Design System

The source of truth for the web UI. Tokens live in `web/src/styles/tokens.css` and map into the Tailwind theme. Components never use raw colours or magic numbers. If this file and the code disagree, fix one of them in the same change.

**Tone:** calm, clinical but human, editorial. Generous on patient screens, dense on admin screens.

## 1. Reference systems

Two references inform the structure. We borrow no colour, logo, typeface or brand expression from either. Both sources are analyses of the companies' marketing sites, so we borrow proportions and habits, not product components.

| Reference | What we borrow | What we leave |
|---|---|---|
| **IBM Carbon** | One accent carrying most actions; 1px hairlines and tone steps in place of shadows; underlined tabs; a compact 14px and 12px text pair for dense views; light-handed display type that stays calm at large sizes | Square corners, blue, Plex, the dark footer |
| **Cal.com** | The 4, 8, 12, 16, 24, 32, 48 spacing rhythm; 40px controls; real interface shown as imagery instead of illustration; scheduling surfaces built as plain grids | Black buttons, pill navigation, rating stars, testimonial cards, large rounded cards |

## 2. Colour

Navy and beige. The values live in `web/src/styles/tokens.css`, and `web/tests/design-tokens.test.ts` fails if a pairing drops below AA, which is 4.5:1 for text and 3:1 for control boundaries.

| Token | Use |
|---|---|
| `--ink`, `--muted` | Primary and secondary text |
| `--surface`, `--canvas`, `--sand` | Panels, page background, filled tiles |
| `--border`, `--border-control` | Dividers, and the boundaries of inputs and controls |
| `--navy`, `--navy-raised`, `--on-navy`, `--on-navy-muted` | Navy fields and the text on them |
| `--primary`, `--primary-hover`, `--primary-pressed`, `--primary-tint`, `--on-primary` | Actions, links, focus, selected rows |
| `--ai`, `--ai-tint` | AI-generated content only |
| `--danger`, `--danger-pressed`, `--danger-tint` | Emergencies and destructive actions only |
| `--warning`, `--warning-tint`, `--success`, `--success-tint` | Status |

`.on-navy` flips these tokens for everything inside a navy field, so components need no dark variant.

**Rules:**
- Text on `--primary-tint` uses `--primary-hover`.
- `--border` must never be the only boundary of a control.

No dark theme in this round.

## 3. Typography

One family, plus a Bangla fallback, self-hosted as variable woff2 with `font-display: swap`. DM Sans is preloaded. Noto Sans Bengali uses `unicode-range`, so it downloads only when Bangla appears.

- DM Sans, then Noto Sans Bengali, then `system-ui`, for everything.

| Token | Size / line height | Use |
|---|---|---|
| `--text-xs` | 12 / 16 | Metadata and table captions; never for sentences a patient must read |
| `--text-sm` | 14 / 20 | Admin body, table cells, helper text |
| `--text-md` | 16 / 24 | Patient body, inputs (avoids iOS zoom), chat |
| `--text-lg` | 18 / 28 | Lead text, section titles |
| `--text-xl` | 24 / 32 | Subpage titles |
| `--text-2xl` | 32 / 40 | Page titles |
| `--text-3xl` | 44 / 52 | Big numbers |

- Weights: 400 for body, 500 for labels, 600 for emphasis.
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
- No bouncing, parallax or scroll effects. Under reduced motion, changes are immediate.
- Icons: Lucide at stroke width 1.75, in sizes 16, 20 and 24. They support labels and never replace them, except on `IconButton`, which requires an accessible name and a tooltip.
- Imagery: real product interface, simple palette-only SVG, or typography. No stock photographs of doctors.

## 6. Component Inventory

**Primitives** in `web/src/components/ui/`, on Radix with cva variants where a component has variants: Button, IconButton, Input, Textarea, Select, Combobox, Checkbox, Radio, Switch, Label and Field, Badge, Avatar, Tooltip, Dialog, Sheet, Popover, Tabs, Toast, Skeleton, Table, Pagination, EmptyState, Banner (info, warning, emergency). `ConfirmDialog` and `ErrorState` are shared compositions of these. Every state appears on `/dev/components`, a route excluded from production builds.

**Domain components:**
| Component | Note |
|---|---|
| DoctorCard | Compact and detailed variants; no stars, ever |
| VerificationBadge | States its status in words as well as colour |
| SlotPicker | Day strip and time grid, arrow-key navigation, Asia/Dhaka shown |
| AppointmentRow | Time first, tabular |
| ChatMessage | AI and patient differ by layout and an "AI-generated" label, plus the violet tint |
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
