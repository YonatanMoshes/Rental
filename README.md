# Rental Fleet Manager

Rental Fleet Manager is a MongoDB-backed FastAPI service for managing cars and rentals in a car rental company.

Current stage: backend only. The React frontend will be added in the next stage.
Current frontend: React + Vite in the `frontend/` folder.

## Architecture

```text
Client / React / Swagger
        -> FastAPI routes
        -> FleetService business logic
        -> MongoDB repositories
        -> MongoDB
```

This project uses layered architecture:

- `backend/app/api`: HTTP endpoints.
- `backend/app/services`: business rules.
- `backend/app/repositories`: MongoDB data access.
- `backend/app/schemas`: request and response validation.
- `backend/app/models`: internal domain models.
- `backend/app/core`: settings, logging, metrics, and errors.
- `backend/app/db`: MongoDB connection and indexes.
- `frontend/src/api`: typed API calls from React to FastAPI.
- `frontend/src/components`: reusable UI pieces.
- `frontend/src/features`: feature-specific UI for cars and rentals.
- `frontend/src/pages`: full page screens.

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Run Backend Locally

Start MongoDB locally on port `27017`, then run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Open:

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Metrics: http://127.0.0.1:8000/metrics

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

Stop:

```powershell
docker compose down
```
