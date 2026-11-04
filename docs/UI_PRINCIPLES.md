# MediMatch AI: UI Principles

A patient may open this product frightened, on a mid-range Android phone, on a slow network. Every rule here serves that person first. `docs/DESIGN.md` holds the exact values.

**When rules conflict:** (1) accessibility and the safety rules in `CLAUDE.md`, (2) Web Interface Guidelines, (3) Taste Skill, (4) the project brief.

## Safety comes before design
- Emergency text appears exactly as the backend sent it: full width, never softened, collapsed or dismissible, with no doctors beneath it.
- AI output is always labelled, by structure as well as colour. Violet means AI and nothing else.
- Red means emergency or a destructive action and nothing else.
- Never invent doctors, ratings, reviews or statistics, and show only what the API returns.

## Make decisions, not defaults (Taste Skill)
- A screen should show which product it belongs to. If it could be anyone's, it isn't finished.
- Portals are places people work in: flat surfaces, thin rules, small labels and repeated panels are fine. Numbers are set as type, not tiles. No hero headers inside the app.
- Banned: gradients, glows, glass, soft shadows under every card, icons in tinted circles, emoji as icons, tiny uppercase labels above headings, pill badges used as decoration, and rows of three identical cards.
- Structure follows content: lists, tables, split panes, timelines and definition lists. A ranked shortlist is a list, not a carousel.
- Removing decoration isn't enough, because thin pages read as empty. Replace it with larger type, real content and real interface.
- Copy states specifics, and a button names its action.

## Build it correctly (Web Interface Guidelines)
- Semantic HTML first: `button` for actions, links for navigation, real tables, ordered headings, a skip link, landmarks, and accessible names on icon buttons.
- Focus is always visible through `:focus-visible` and never hidden by sticky bars.
- Forms have visible labels, correct `type` and `autocomplete`, errors beside the field, focus on the first error, and an enabled submit button until the request starts. Never block paste or zoom.
- Filters, tabs, pagination and selection live in the URL, and the Back button works.
- Destructive actions need a specific confirmation or an undo.
- Dates, times, numbers and currency go through `Intl`, in Asia/Dhaka, with tabular numerals where values compare.
- Animate only `transform` and `opacity`, never `transition: all`, and respect reduced motion.
- Text survives very long content and very long Bangla. Use `…` and curly quotes.

## Every view is complete
Each interactive element has hover, focus-visible, active, disabled and loading states. Each data view has designed loading, empty, error and partial states. Empty says what to do next; an error says what happened and how to retry.

## Built for real conditions
- Works at 360px with no horizontal scroll, and with 44px touch targets on mobile.
- Keep the bundle light: split routes, self-host fonts, download Bangla only when needed.
- English and Bangla share every layout, so fixed-width text containers are not allowed.

## Proof, not opinion
A screen is done only when screenshots at three sizes have been reviewed by eye, the console and network are clean, axe finds no serious or critical issues, and the keyboard path works. `Playwright CLI` does this after every screen, and the critique goes in `docs/UI_REVIEW.md`.

`Image to Code` applies only when a mockup is supplied: extract layout and spacing, map them onto our tokens, add no new colours, and diff the render against the image.
