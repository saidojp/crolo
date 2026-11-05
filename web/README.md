# Crolo · Web

Minimal dark UI for the Crolo API, built with **React 19 + Vite 8 + Chakra UI v3**.

## Requirements

- Node.js `^20.19.0` or `>=22.12.0` (Vite 8 requirement)
- The FastAPI backend from `../api` running on `http://127.0.0.1:8000`

## Getting started

```bash
npm install
cp .env.example .env   # optional
npm run dev            # http://localhost:5173
```

Start the backend in a second terminal:

```bash
cd ../api
./venv/bin/uvicorn main:app --reload
```

Requests to `/api/*` are proxied by Vite to `http://127.0.0.1:8000/*`
(see `vite.config.ts`), so the browser stays on a single origin and the API needs
no CORS configuration. Override the target with `VITE_API_URL` when needed.

## Scripts

| Script              | Description                                    |
| ------------------- | ---------------------------------------------- |
| `npm run dev`       | Dev server with HMR on port `5173`             |
| `npm run build`     | Type-check, then bundle into `dist/`           |
| `npm run preview`   | Serve the production build on port `4173`      |
| `npm run typecheck` | TypeScript only (`tsc --noEmit`)               |

## Auth flow

| Backend endpoint       | Used by                                              |
| ---------------------- | ---------------------------------------------------- |
| `POST /token`          | `LoginPage` — OAuth2 password grant (form-encoded)   |
| `POST /register/`      | `RegisterPage` — then signs in automatically         |
| `GET /users/me`        | `AuthProvider` — session restore and post-login whoami |
| `GET /protected`       | `DashboardPage` — verifies the bearer token works    |

The access token is kept in `localStorage` under `crolo.access_token` and sent as
`Authorization: Bearer <token>`. It expires after 30 minutes (backend setting);
an expired token is dropped on boot and the user is sent back to `/login`.

> **Security note:** `localStorage` is readable by any script on the origin. For
> production, prefer an httpOnly cookie issued by the backend.

## Structure

```
src/
├── App.tsx                    route table
├── main.tsx                   root render + providers
├── auth/AuthProvider.tsx      session state, login/register/logout
├── components/
│   ├── AuthShell.tsx          centered layout for auth screens
│   ├── BrandMark.tsx          wordmark
│   └── ui/                    Chakra CLI snippets (provider, toaster, password input)
├── layout/AppLayout.tsx       app shell: header, user menu, footer
├── lib/api.ts                 typed fetch client + ApiError
├── pages/                     Login, Register, Dashboard, Settings
├── routes/RouteGuards.tsx     ProtectedRoute / GuestRoute
└── theme/index.ts             Crolo design system (tokens, semantic colors)
```

## Theming

`src/theme/index.ts` extends Chakra's default config with:

- a tuned neutral ramp (`gray`) for dark surfaces,
- a single `brand` accent palette,
- semantic tokens (`bg.panel`, `fg.muted`, `border.muted`, …) used across the UI.

The app is intentionally **dark-only**: `index.html` sets `class="dark"` and
`color-scheme: dark`, and the semantic tokens resolve to their `_dark` values.
To add light mode later, wire up `next-themes` (Chakra's `color-mode` snippet) and
remove the hard-coded `dark` class.
