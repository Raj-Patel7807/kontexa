# Kontexa Frontend

The frontend is a Next.js App Router application. Its current page is a status dashboard at `/`.
It polls `/api/health` every 15 seconds and displays the backend, PostgreSQL, and Redis readiness
state.

`next.config.ts` rewrites `/api/:path*` to `BACKEND_URL/:path*`. `BACKEND_URL` is server-side;
it is not exposed to browser code.

## Run locally

```bash
npm install
npm run dev
```

By default, the rewrite targets `http://localhost:8000`. Set `BACKEND_URL` in `frontend/.env` to
use another backend address. See [docs/development/setup.md](../docs/development/setup.md) for the
full local stack instructions.

## Verification

```bash
npm run lint
npm run typecheck
npm run build
```
