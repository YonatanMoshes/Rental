# Architecture Overview

This document describes the system architecture of the Rental Fleet Manager application.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser                              │
│         React + TypeScript + Vite                       │
│     (Frontend on port 5173 during development)          │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP/REST
                  │ JSON
                  ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend                            │
│          Python + Async I/O                             │
│     (Backend on port 8000 during development)           │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │         API Routes (HTTP endpoints)              │   │
│  │  /api/cars, /api/rentals, /health, /metrics      │   │
│  └──────────────────────────────────────────────────┘   │
│                       │                                  │
│  ┌────────────────────▼───────────────────────────────┐ │
│  │         Business Logic (FleetService)             │ │
│  │   - Validates business rules                      │ │
│  │   - Coordinates car and rental operations         │ │
│  │   - Tracks metrics                                │ │
│  └─────────────┬──────────────────┬──────────────────┘ │
│               │                  │                      │
│    ┌──────────▼────────┐   ┌─────▼──────────────┐      │
│    │ Car Repository    │   │ Rental Repository  │      │
│    │ (MongoDB)         │   │ (MongoDB)          │      │
│    └──────────────────┘   └─────┬──────────────┘      │
│                                  │                      │
└──────────────────────────────────┼──────────────────────┘
                                   │ Binary Protocol
                                   ▼
                     ┌──────────────────────────┐
                     │    MongoDB Database      │
                     │  - cars collection       │
                     │  - rentals collection    │
                     │  (on port 27017)         │
                     └──────────────────────────┘
```

## Directory Structure

```
Rental/
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── main.py                   # App factory, lifespan management
│   │   ├── api/
│   │   │   ├── routes/               # HTTP endpoint handlers
│   │   │   │   ├── cars.py           # Car CRUD operations
│   │   │   │   ├── rentals.py        # Rental operations
│   │   │   │   └── system.py         # Health & metrics
│   │   │   └── dependencies.py       # Dependency injection
│   │   ├── services/
│   │   │   └── fleet_service.py      # Business logic layer
│   │   ├── repositories/             # Data access layer
│   │   │   ├── cars.py               # MongoDB car queries
│   │   │   └── rentals.py            # MongoDB rental queries
│   │   ├── models/
│   │   │   ├── documents.py          # Internal domain models
│   │   │   └── enums.py              # Status enumerations
│   │   ├── schemas/                  # Request/response validation
│   │   │   ├── cars.py
│   │   │   └── rentals.py
│   │   ├── core/
│   │   │   ├── config.py             # Settings management
│   │   │   ├── errors.py             # Custom exceptions
│   │   │   ├── logging.py            # Logging configuration
│   │   │   └── metrics.py            # Prometheus metrics
│   │   └── db/
│   │       ├── mongodb.py            # Connection management
│   │       ├── indexes.py            # Database indexes
│   │       └── object_ids.py         # ObjectId utilities
│   └── __init__.py
│
├── frontend/                         # React + TypeScript application
│   ├── src/
│   │   ├── main.tsx                  # React entry point
│   │   ├── App.tsx                   # Root component
│   │   ├── api/
│   │   │   ├── http.ts               # Fetch wrapper & error handling
│   │   │   └── fleetApi.ts           # Typed API client
│   │   ├── types/
│   │   │   └── fleet.ts              # TypeScript type definitions
│   │   ├── components/               # Reusable UI components
│   │   │   ├── AppHeader.tsx         # Application header
│   │   │   ├── StatusBadge.tsx       # Status display
│   │   │   └── SummaryTile.tsx       # Metric tiles
│   │   ├── features/                 # Feature-specific components
│   │   │   ├── cars/
│   │   │   │   ├── CarForm.tsx       # Add car form
│   │   │   │   └── CarsTable.tsx     # Car list/management
│   │   │   └── rentals/
│   │   │       ├── RentalForm.tsx    # Start rental form
│   │   │       └── RentalsTable.tsx  # Rental list/management
│   │   ├── pages/
│   │   │   └── DashboardPage.tsx     # Main page (state orchestrator)
│   │   ├── utils/
│   │   │   ├── dates.ts              # Date helpers
│   │   │   └── labels.ts             # Display formatting
│   │   └── styles/
│   │       └── global.css            # Global styles
│   ├── index.html                    # HTML entry point
│   ├── vite.config.ts                # Vite build configuration
│   ├── tsconfig.json                 # TypeScript configuration
│   ├── Dockerfile                    # Container image for production
│   └── package.json                  # Dependencies & scripts
│
├── docker-compose.yml                # Local dev: starts backend + frontend + MongoDB
├── Dockerfile                        # Backend container image
├── pyproject.toml                    # Python dependencies & metadata
├── README.md                         # Quick start guide
└── ARCHITECTURE.md                   # This file
```

## Technology Stack

### Backend
- **Framework**: FastAPI (async web framework)
- **Database**: MongoDB (NoSQL document store)
- **ORM/Query**: motor (async MongoDB driver)
- **Validation**: Pydantic (request/response validation)
- **Monitoring**: Prometheus (metrics collection)
- **Server**: Uvicorn (ASGI server)

### Frontend
- **Library**: React 18 (UI framework)
- **Language**: TypeScript (static typing)
- **Bundler**: Vite (fast build tool)
- **HTTP**: Fetch API (native browser)
- **Icons**: Lucide React (SVG icons)
- **Styling**: CSS (vanilla, no framework)

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Development**: Local dev with hot-reload
- **Production**: Containerized services

## Data Model

### Car Document
```typescript
{
  _id: ObjectId,              // MongoDB auto-generated ID
  model: string,              // e.g., "Toyota Corolla"
  year: number,               // e.g., 2021
  status: "available" | "rented" | "maintenance"
}
```

### Rental Document
```typescript
{
  _id: ObjectId,              // MongoDB auto-generated ID
  car_id: string,             // Reference to car's _id
  customer_name: string,      // e.g., "Dana Levi"
  start_date: date,           // ISO format: 2024-05-25
  end_date: date | null       // null means rental is open/active
}
```

## API Endpoints

### Cars
- `GET /api/cars` - List all cars (optional `?status=available` filter)
- `POST /api/cars` - Create a new car
- `PATCH /api/cars/{car_id}` - Update car details
- `DELETE /api/cars/{car_id}` - Delete a car

### Rentals
- `GET /api/rentals` - List all rentals (optional `?open_only=true` filter)
- `POST /api/rentals` - Start a new rental
- `POST /api/rentals/{rental_id}/end` - End a rental

### System
- `GET /health` - Health check (returns `{"status": "ok"}`)
- `GET /metrics` - Prometheus metrics

## Business Logic & Rules

### Car Management
- Cars start in **AVAILABLE** status
- **AVAILABLE** cars can be rented
- **RENTED** cars cannot be deleted
- Cars can be marked for **MAINTENANCE** (except while rented)

### Rental Management
- Only **AVAILABLE** cars can be rented
- Each car can only have one active (open) rental at a time
- Marking a car **RENTED** must go through the rental flow (not direct car update)
- When a rental ends, the car returns to **AVAILABLE** status

### Metrics Tracking
- Every operation (add_car, list_cars, update_car, etc.) is tracked
- Operation count and duration histograms are recorded
- Fleet statistics (available, rented, maintenance cars, open rentals) are updated

## Error Handling

### HTTP Status Codes
- `200 OK` - Successful GET, PATCH operations
- `201 Created` - Successful POST (new resource created)
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid request data (Pydantic validation failure)
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Business rule violated (e.g., cannot delete rented car)
- `500 Internal Server Error` - Unexpected server error

### Custom Exceptions
- `NotFoundError` → HTTP 404
- `BusinessRuleError` → HTTP 409 Conflict

## State Management

### Frontend
- **Component State**: Cars, rentals, loading, error messages managed at DashboardPage level
- **No external store**: Uses React hooks (useState, useMemo, useEffect)
- **Data flow**: Backend API calls → state update → re-render

### Backend
- **Stateless**: Each request is independent
- **Database as source of truth**: MongoDB holds all persistent data
- **Metrics stored in-memory**: Prometheus client manages aggregation

## Development Workflow

### Local Setup
```bash
# Start all services
docker-compose up

# Backend: http://127.0.0.1:8000
#   - API docs: http://127.0.0.1:8000/docs
#   - Metrics: http://127.0.0.1:8000/metrics

# Frontend: http://127.0.0.1:5173

# MongoDB: 127.0.0.1:27017
```

### Hot Reload
- **Backend**: Uvicorn watches Python files, auto-reloads
- **Frontend**: Vite watches TypeScript/React files, hot module replacement

### Database Persistence
- MongoDB data is persisted in a Docker volume
- Use `docker-compose down -v` to reset database

## Security Considerations

⚠️ This is a demo application. For production:
- Add authentication (JWT, OAuth)
- Implement authorization (role-based access control)
- Add CORS configuration
- Use HTTPS/TLS
- Validate and sanitize all inputs
- Implement rate limiting
- Add database connection pooling
- Use environment-specific configs

## Performance

- **Indexes**: Database indexes on `status` and `[car_id, end_date]` for fast queries
- **Async/await**: Backend uses async operations for I/O-bound tasks
- **Type checking**: TypeScript prevents runtime type errors
- **Caching**: Settings cached with `@lru_cache` decorator

## Monitoring & Observability

- **Metrics**: Prometheus-format output at `/metrics`
- **Tracked metrics**:
  - `rental_fleet_operations_total` - Operation counts by type
  - `rental_fleet_operation_duration_seconds` - Latency histograms
  - `rental_fleet_available_cars` - Current available car count
  - `rental_fleet_rented_cars` - Current rented car count
  - `rental_fleet_open_rentals` - Active rental count
- **Logging**: Structured logs to console and file
- **Health check**: `/health` endpoint for monitoring

## Deployment

See individual README sections for deployment instructions. The application is designed to run as containerized services:
- Backend container (FastAPI + Uvicorn)
- Frontend container (Nginx serving static SPA)
- MongoDB container (database)

All connected via Docker Compose for local development and deployable to any container orchestration platform (Kubernetes, ECS, etc.).
