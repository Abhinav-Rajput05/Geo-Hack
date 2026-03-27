# AI-Powered Global Ontology Engine

A real-time knowledge graph system that ingests multi-domain data (geopolitics, economics, defense, technology, climate, society) and generates AI-driven strategic insights.

## Local-First Runtime Model

- `Neo4j`: local installation (not Docker)
- `PostgreSQL`: local installation (not Docker)
- `Redis`: Docker only
- `Backend`, `Celery`, `Frontend`: run locally

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Redis only)
- Local Neo4j running on `bolt://localhost:7687`
- Local PostgreSQL running on `localhost:5432`

## Quick Start

1. Copy env file:
   ```powershell
   Copy-Item .env.example backend/.env
   ```

2. Update `backend/.env` with your credentials:
   - `NEO4J_PASSWORD`
   - `DATABASE_URL`
   - `OPENROUTER_API_KEY`
   - Optional: `NEWS_API_KEY`

3. Start Redis via Docker:
   ```powershell
   docker compose up -d redis
   ```

4. Install backend dependencies:
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

5. Run backend API:
   ```powershell
   1
   ```

6. In a second terminal, run Celery worker:
   ```powershell
   cd backend
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

7. In a third terminal, run Celery beat:
   ```powershell
   cd backend
   celery -A app.tasks.celery_app beat --loglevel=info
   ```

8. Run frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

## Helper Scripts (PowerShell)

- `scripts/redis-up.ps1`
- `scripts/redis-down.ps1`
- `scripts/backend-dev.ps1`
- `scripts/celery-worker.ps1`
- `scripts/celery-beat.ps1`
- `scripts/frontend-dev.ps1`

## Access URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Neo4j Browser (if enabled): http://localhost:7474

## Core Environment Variables

- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=<your_password>`
- `DATABASE_URL=postgresql://ontology_user:password@localhost:5432/ontology_db`
- `REDIS_URL=redis://localhost:6379/0`
- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/0`
- `OPENROUTER_API_KEY=<your_key>`

## Notes

- Dockerfiles are kept for optional container-based deployment, but local development is now local-first.
- `docker-compose.yml` now manages Redis only.
