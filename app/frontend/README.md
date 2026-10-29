# Frontend (Vite + React + TypeScript + React Flow)

## Run
```
cd app/frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # typecheck + production build
```
Backend base URL: `VITE_API_BASE` (default `http://localhost:8000/api`).

If the backend is unreachable, the app falls back to labelled mock fixtures
(`src/fixtures/mock.ts`) and shows a "Demo data: backend offline" badge. Mock data
contains no code facts; Section C rows show "unresolved (needs corpus lookup)".

Layout: `src/api.ts` (single API client), `src/components.tsx` (mind map, chips, glossary),
`src/App.tsx` (applicant and reviewer screens), `src/styles.css` (CSS variables, AA contrast).
