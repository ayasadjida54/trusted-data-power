# Trusted Data Power

**Intelligent Data Reliability & Quality Assessment Platform.**

Upload a spreadsheet (or connect a Google Sheet) and get a transparent,
explainable **DataScore** — a 0–100 reliability score with an exact,
plain-language breakdown of *why* it's what it is, per-column detail,
version history, and a real one-click cleaning pipeline. Built for SMEs,
freelancers, and e-commerce businesses who need to know whether their
data can be trusted before they act on it — not just another BI dashboard.

## Features

- **DataScore** — a 0–100 reliability score built from six measurable
  quality dimensions (completeness, uniqueness, type consistency,
  formatting consistency, numerical quality, structural quality), each
  independently weighted and explained
- **Explainability by design** — every score comes with a plain-language
  breakdown of exactly which findings drove it, at both the dataset and
  the individual-column level. Nothing is a black box
- **Real cleaning, not a demo number** — the "Execute DataScore Pipeline"
  action actually fixes exact duplicates, whitespace, and inconsistent
  capitalization, then re-scores the real result. It deliberately never
  touches missing values or outliers, since those need a human judgment
  call, not a silent transformation
- **Version history, trends, and comparison** — repeat uploads to the
  same dataset build a real history; compare any two versions and see
  exactly what changed and why
- **Google Sheets connector** — point at any publicly-viewable sheet, no
  OAuth required, with optional automatic re-sync on a schedule
  (hourly/daily/weekly)
- **Automatic alerts** — get notified when a monitored dataset's score
  drops past a threshold you set, with the same plain-language "why"
- **Exportable, shareable reports** — a polished PDF report, a CSV
  export, and read-only public share links, no account required to view
- **Real accounts and workspaces** — email/password auth, with data
  scoped to a shared organization so a team sees the same datasets

## Tech stack

| Layer | Technology |
|---|---|
| Analysis engine | Python, pandas, numpy |
| Backend API | FastAPI, SQLAlchemy, Alembic, PostgreSQL (SQLite for local dev) |
| Auth | JWT bearer tokens, bcrypt |
| Reports | reportlab (PDF) |
| Scheduling | APScheduler (in-process) |
| Frontend | React (Vite), React Router, Tailwind CSS, Recharts |

## Project structure

```
trusted-data-power/
├── engine/              # Pure Python analysis core — profiling, quality
│                        # checks, scoring, explainability, comparison,
│                        # cleaning. No web framework, no UI code.
├── backend/             # FastAPI application
│   ├── api/             # Route handlers
│   ├── models/          # SQLAlchemy models
│   ├── migrations/      # Alembic migration history (see its README)
│   ├── schemas/         # Pydantic request/response models
│   ├── services/        # Business logic — auth, analysis, sheets,
│   │                    # monitoring, cleaning, reports, scheduling
│   └── tests/
├── frontend/            # React (Vite) application
│   └── src/
│       ├── api/         # Backend API client
│       ├── auth/        # Auth context, protected routes
│       ├── components/  # Reusable UI components
│       └── pages/       # Route-level pages
└── docs/
    └── trusted-data-power-spec.md   # Full architecture spec and phase-by-phase history
```

## Getting started

Requirements:
- Python 3.13
- Node.js
- npm

**Backend:**

1. Open PowerShell in the project root.
2. Create the virtual environment:
   ```powershell
   py -3.13 -m venv .venv
   ```
3. Install dependencies:
   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   ```
4. Run database migrations:
   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   ```
5. Start the backend:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
   ```

**Frontend:**

1. Open a second PowerShell window.
2. Go to frontend:
   ```powershell
   cd frontend
   ```
3. Install dependencies:
   ```powershell
   npm.cmd install
   ```
4. Start the frontend:
   ```powershell
   npm.cmd run dev
   ```

Open: http://localhost:5173

**Notes:**
- The backend uses a local SQLite database by default — nothing else to
  install or configure for local development. To use a real PostgreSQL
  instance instead, set the `DATABASE_URL` environment variable before
  running the commands above.
- Run `alembic upgrade head` again any time you pull a schema change —
  see [`backend/migrations/README.md`](backend/migrations/README.md) for
  details on creating and applying migrations.
- **Before deploying anywhere real:** set a proper `SECRET_KEY`
  environment variable (used to sign auth tokens) — the fallback in
  `backend/services/security.py` is for local development only and
  provides no real security. See `backend/.env.example`.
- To point the frontend at a different backend, set `VITE_API_BASE_URL`
  — see `frontend/.env.example`.

### Try it out

Register a workspace, upload `engine/tests/sample_messy_data.csv` (or your
own file), and explore from there — Dashboard, Columns, Findings, Trend,
Compare, and the Export & share panel.

## Running tests

```bash
pip install -r backend/requirements.txt   # includes engine + backend deps
python -m pytest engine/ backend/ -v
```

Engine and backend tests run independently of the frontend and require no
running server — the backend tests spin up an isolated FastAPI test
client against a disposable temporary SQLite database per test session.

## Database migrations

Schema changes are tracked with Alembic. See
[`backend/migrations/README.md`](backend/migrations/README.md) for how to
apply and create migrations.

