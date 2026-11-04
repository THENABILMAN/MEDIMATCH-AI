# MediMatch AI Web App

The patient, doctor and admin portals, built with React, TypeScript, Vite, Tailwind CSS v4 and Radix.

## Run It

```bash
npm install
cp .env.example .env   # Public values only. Never add service-role, Pinecone or OpenRouter keys.
npm run dev
```

The app expects the API at `VITE_API_BASE_URL`, which defaults to `http://localhost:8000`. Apply every migration in `supabase/migrations/` first.

## Check It

```bash
npm run build            # Type-checks everything, then builds
npm test                 # Unit tests, including token contrast and translation keys
npx playwright test      # Browser tests, using your installed Chrome
```

Playwright runs against a mocked API (`e2e/support/`) and blocks every other outbound request, so it cannot reach the real project or paid AI services. It also regenerates `screenshots/`.

## Where Things Live

| Path | Contents |
|---|---|
| `src/styles/tokens.css` | Every colour and shared value |
| `src/components/ui/` | Primitives |
| `src/components/domain/` | Product components |
| `src/locales/en.json` | All copy. Bangla goes in `bn.json` using the same keys |
| `src/lib/format.ts` | Dates, times and currency, always in Asia/Dhaka |
| `src/api/` | API client and TanStack Query hooks |

`/dev/components` shows every primitive in every state during development. It is excluded from production builds.

Design rules are in `../docs/DESIGN.md` and `../docs/UI_PRINCIPLES.md`.
