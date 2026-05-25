# Rental Fleet Manager

Rental Fleet Manager is a full-stack car rental management system with a React frontend, FastAPI backend, MongoDB database, RabbitMQ message queue, and background event worker.

Current frontend: React + Vite in the `frontend/` folder.
Current backend: FastAPI + MongoDB + RabbitMQ in the `backend/` folder.

Detailed system design, diagrams, API examples, and scaling explanation:

- [docs/system-design.md](docs/system-design.md)

## Architecture

```text
React frontend
        -> FastAPI routes
        -> FleetService business logic
        -> MongoDB repositories
        -> MongoDB

FleetService
        -> RabbitMQ event queue
        -> Event worker
        -> MongoDB fleet_events audit collection
```

This project uses layered architecture:

- `backend/app/api`: HTTP endpoints.
- `backend/app/services`: business rules.
- `backend/app/repositories`: MongoDB data access.
- `backend/app/schemas`: request and response validation.
- `backend/app/models`: internal domain models.
- `backend/app/core`: settings, logging, metrics, and errors.
- `backend/app/db`: MongoDB connection and indexes.
- `backend/app/messaging`: RabbitMQ event publisher and consumer.
- `backend/app/workers`: background worker processes.
- `frontend/src/api`: typed API calls from React to FastAPI.
- `frontend/src/components`: reusable UI pieces.
- `frontend/src/features`: feature-specific UI for cars and rentals.
- `frontend/src/pages`: full page screens.

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Run Backend Locally

Start MongoDB locally on port `27017` and RabbitMQ locally on port `5672`, then run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

In a second terminal, run the queue worker:

```powershell
.\.venv\Scripts\python.exe -m backend.app.workers.event_worker
```

Open:

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Metrics: http://127.0.0.1:8000/metrics
- Queue events: http://127.0.0.1:8000/api/events

## Run React Frontend Locally

Start the backend first, then open a second terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` requests to the FastAPI backend on port `8000`.

## Build React Frontend

```powershell
cd frontend
npm.cmd run build
```

## Run With Docker

```powershell
docker compose up --build
```

Open:

- React app: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs
- MongoDB: localhost:27017
- RabbitMQ dashboard: http://127.0.0.1:15672

RabbitMQ login:

```text
guest / guest
```

Stop:

```powershell
docker compose down
```
