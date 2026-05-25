# Frontend — Greek Supermarket Offers

Next.js 16 (App Router) + TypeScript + Tailwind v4 frontend for the Greek
supermarket offer aggregator. Consumes the public REST API at
`/api/public/v1/*`.

## Quick start

```bash
cp .env.example .env.local
npm install
npm run dev          # http://localhost:3000
```

By default the app calls `http://localhost:8001/api/public/v1/*`. If the
backend isn't running yet, switch to mock mode:

```bash
echo "NEXT_PUBLIC_USE_MOCKS=true" >> .env.local
```

Mocks live in `src/mocks/` and ship the same shapes as the real API.

## Scripts

| Command              | What it does                                  |
| -------------------- | --------------------------------------------- |
| `npm run dev`        | Start dev server with Turbopack               |
| `npm run build`      | Production build                              |
| `npm run start`      | Serve the production build                    |
| `npm run lint`       | ESLint (Next + TS config)                     |
| `npm run test`       | Vitest, one-shot                              |
| `npm run test:watch` | Vitest, watch mode                            |

## Pointing at a different backend

Set `NEXT_PUBLIC_API_BASE_URL` to any host. For example, to smoke-test
against the parallel public-API worktree on port 8005:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8005 npm run dev
```

## Project layout

```
src/
├── app/             App Router pages, layouts, sitemap, robots
│   ├── page.tsx                    /
│   ├── offers/page.tsx             /offers
│   ├── offers/[id]/page.tsx        /offers/:id
│   ├── brand/[slug]/page.tsx       /brand/:slug
│   ├── about/page.tsx              /about
│   ├── sitemap.ts                  /sitemap.xml
│   └── robots.ts                   /robots.txt
├── components/      Presentational + URL-driven client components
├── lib/             API client, types, formatters, URL helpers
└── mocks/           In-memory sample data for offline dev
```

## API contract

The frontend consumes — but does not own — the public REST API:

```
GET /api/public/v1/brands
GET /api/public/v1/categories
GET /api/public/v1/offers
GET /api/public/v1/offers/{id}
GET /api/public/v1/brands/{slug}/offers
GET /api/public/v1/search?q=...
```

All filter state is encoded in the URL — bookmarkable, shareable,
SSR-friendly.

## Requirements

- Node.js 20.9+ (enforced via `engines`)
- Next.js 16 needs React 19.2
