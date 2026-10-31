# MITS AI Assistant — Frontend

## Stack

- **React 18 + TypeScript** — component architecture, type safety
- **Vite 5** — build tool, outputs to `../static/`
- **Tailwind CSS 3** — utility classes driven by CSS variables (theme tokens)
- **Framer Motion** — UI transitions, sidebar drawer animation
- **Three.js** — 3D hero scene (lazy-loaded, separate chunk)
- **Lucide React** — icons (no emojis)
- **marked + DOMPurify** — safe Markdown rendering
- **@fontsource/inter + @fontsource/space-grotesk** — self-hosted fonts

## Build & Run

```powershell
cd frontend
npm install
npm run build
```

The build outputs directly to `../static/` (the directory FastAPI serves).
Vite `base` is set to `/static/` so assets resolve through FastAPI's existing
`StaticFiles` mount — no backend change needed.

Then start the backend as usual:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Development

```powershell
cd frontend
npm run dev
```

This starts Vite's dev server (default `http://localhost:5173`).
Note: API calls use a relative `/ask` URL, so you need the FastAPI server
running on port 8000 simultaneously. Configure a Vite proxy in `vite.config.ts`
if you want the dev server to forward API requests.

## Old Frontend Backup

The previous vanilla HTML/CSS/JS frontend is backed up in `frontend/backup/`.
