# Crolo · Web

## Requirements

- Node.js `^20.19.0` or `>=22.12.0` (Vite 8 requirement)
- npm (or another package manager)
- The API from `../api` running on `http://127.0.0.1:8000`

## Setup

```bash
cd web
npm install
```

## Environment

Environment variables are optional; copy the example if you need to override defaults:

```bash
cp .env.example .env
```

| Variable       | Default | Description                                                                 |
| -------------- | ------- | --------------------------------------------------------------------------- |
| `VITE_API_URL` | `/api`  | Base URL for the API. Leave unset to use Vite's `/api` proxy (recommended). |

When `VITE_API_URL` points to another origin, the backend must enable CORS.

## Run

Start the API first:

```bash
cd ../api
source venv/bin/activate
uvicorn main:app --reload
```

Then start the dev server:

```bash
npm run dev
```

- App: `http://localhost:5173`
- Requests to `/api/*` are proxied to `http://127.0.0.1:8000/*` (see `vite.config.ts`), so no CORS setup is needed in development.

## Scripts

| Script              | Description                                    |
| ------------------- | ---------------------------------------------- |
| `npm run dev`       | Dev server with HMR on port `5173`             |
| `npm run build`     | Type-check, then bundle into `dist/`           |
| `npm run preview`   | Serve the production build on port `4173`      |
| `npm run typecheck` | TypeScript only (`tsc --noEmit`)               |

## Production

```bash
npm run build
npm run preview     # or serve dist/ with any static host
```

The preview server uses the same `/api` proxy. On a static host without a proxy, set
`VITE_API_URL` at build time and enable CORS on the backend.

## Build config

- `vite.config.ts` — dev/preview ports (`5173` / `4173`), `/api` proxy, and the `@` → `src` alias.
- `tsconfig.json` — strict TypeScript, `@/*` path alias, bundler module resolution.
- `index.html` — app entry, dark `color-scheme`.
