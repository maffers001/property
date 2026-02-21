# Property Review Frontend

React (Vite + TypeScript) app for the property design/review workflow and reports.

## Setup

```bash
npm install
```

## Run (development)

1. Start the backend from the repo root (see `backend/README.md`), e.g. port 8000.
2. Start the frontend:

```bash
npm run dev
```

The app will proxy `/api` to the backend (see `vite.config.ts`). Open http://localhost:5173 and log in with `REVIEW_APP_PASSWORD`.

## Build

```bash
npm run build
```

Output is in `dist/`. Serve it with any static server; set the API base URL or reverse-proxy `/api` to the backend.
