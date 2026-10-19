# RailOps AI frontend

Professional operations workspace for the RailOps AI synthetic railway simulation. The interface is not certified signaling software and must not be used to control real railway infrastructure.

## Local setup

```bash
npm install
cp ../.env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` to the FastAPI origin, without an `/api` suffix. The default local backend origin is `http://localhost:8000`.

## Validation

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

The production build uses Next.js with webpack because it is compatible with restricted build environments that do not allow Turbopack's internal worker port.
