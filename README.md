# Decision Tracker

A lightweight app for tracking decisions with status, priority, and outcomes.

## Stack

| Layer     | Technology                              |
|-----------|----------------------------------------|
| Backend   | FastAPI + SQLAlchemy 2 + Alembic        |
| Database  | SQLite (`backend/data/decisiontracker.db`) |
| Frontend  | Vite + React 18 + Tailwind CSS v4 + shadcn/ui |
| Container | Docker Compose                          |

## Quick Start (Docker)

```bash
docker compose up --build
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://localhost:8000        |
| API docs | http://localhost:8000/api/v1/docs |

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` → `http://localhost:8000`.

### Database Migrations

```bash
cd backend
alembic upgrade head          # apply migrations
alembic revision --autogenerate -m "description"  # generate new migration
```

## Project Structure

```
decision-tracker/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # Route handlers
│   │   ├── core/               # Settings
│   │   ├── db/                 # SQLAlchemy engine + session
│   │   ├── models/             # ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   └── main.py
│   ├── alembic/                # Migrations
│   ├── data/                   # SQLite database (gitignored)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # React components + shadcn/ui
│   │   ├── lib/                # API client + utils
│   │   ├── pages/              # Page-level components
│   │   └── types/              # TypeScript types
│   └── package.json
├── docker-compose.yml
└── docker-compose.dev.yml
```

## API Endpoints

| Method | Path                    | Description             |
|--------|-------------------------|-------------------------|
| GET    | /api/v1/decisions/      | List (filterable)       |
| POST   | /api/v1/decisions/      | Create                  |
| GET    | /api/v1/decisions/{id}  | Get by ID               |
| PATCH  | /api/v1/decisions/{id}  | Update                  |
| DELETE | /api/v1/decisions/{id}  | Delete                  |
| GET    | /health                 | Health check            |
