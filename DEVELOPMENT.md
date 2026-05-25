# Development Guide

Quick reference for developing and contributing to the Rental Fleet Manager.

## Project Structure

The project follows a **layered architecture** with clear separation of concerns:

### Backend Layers

1. **API Routes** (`backend/app/api/routes/`)
   - HTTP endpoint handlers
   - Request validation via Pydantic schemas
   - Response formatting
   - Files: `cars.py`, `rentals.py`, `system.py`

2. **Services** (`backend/app/services/`)
   - Business logic and rules
   - Coordinates repositories
   - Orchestrates complex operations
   - File: `fleet_service.py`

3. **Repositories** (`backend/app/repositories/`)
   - Data access layer
   - MongoDB queries
   - Maps documents ↔ Python objects
   - Files: `cars.py`, `rentals.py`

4. **Core** (`backend/app/core/`)
   - Configuration (`config.py`)
   - Custom errors (`errors.py`)
   - Logging setup (`logging.py`)
   - Metrics tracking (`metrics.py`)

5. **Models & Schemas** (`backend/app/models/`, `backend/app/schemas/`)
   - Domain models (`documents.py`)
   - Type definitions (`enums.py`)
   - Request validation (`schemas/`)

6. **Database** (`backend/app/db/`)
   - Connection management (`mongodb.py`)
   - Index creation (`indexes.py`)
   - ObjectId utilities (`object_ids.py`)

### Frontend Structure

1. **Pages** (`src/pages/`)
   - Full-page components
   - Main state orchestration
   - File: `DashboardPage.tsx`

2. **Features** (`src/features/`)
   - Feature-specific components
   - Grouped by domain (cars, rentals)
   - Subdirectories: `cars/`, `rentals/`

3. **Components** (`src/components/`)
   - Reusable, generic UI components
   - Status badge, summary tiles, header
   - No business logic

4. **API** (`src/api/`)
   - HTTP client (`http.ts`)
   - Typed API calls (`fleetApi.ts`)
   - Error handling

5. **Types** (`src/types/`)
   - TypeScript type definitions
   - File: `fleet.ts`

6. **Utils** (`src/utils/`)
   - Helper functions
   - Date handling, label formatting

## Common Tasks

### Adding a New Car Field

1. Update MongoDB schema → `backend/app/models/documents.py` (CarDocument)
2. Update Pydantic schemas → `backend/app/schemas/cars.py`
3. Update form → `frontend/src/features/cars/CarForm.tsx`
4. Update table → `frontend/src/features/cars/CarsTable.tsx`
5. Update frontend types → `frontend/src/types/fleet.ts` (if needed)

### Adding a New Endpoint

1. Create handler in `backend/app/api/routes/`
2. Add method to `FleetService` (if business logic needed)
3. Add method to repositories (if data access needed)
4. Create Pydantic schemas in `backend/app/schemas/`
5. Add frontend API call in `frontend/src/api/fleetApi.ts`
6. Use in component

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest

# Run specific test file
python -m pytest tests/backend/test_api.py

# Run with coverage
python -m pytest --cov=backend tests/
```

### Adding Business Logic

1. Add validation/logic to `FleetService` method
2. Raise `BusinessRuleError` if rule violated
3. Catch in FastAPI exception handler (already done in `main.py`)
4. Test error case in tests
5. Display error in UI via API error response

### Database Migrations

MongoDB is schemaless, but to add fields:

1. Update `CarDocument` or `RentalDocument` in `models/documents.py`
2. Update schemas in `schemas/`
3. Add indexes if needed in `db/indexes.py`
4. MongoDB will accept new fields automatically

### Performance Optimization

- **Indexes**: Add compound indexes in `db/indexes.py` for common filters
- **Queries**: Use `.find()` with filters instead of loading all data
- **Frontend**: React memoization already applied to computed values

## Code Conventions

### Python
- Type hints on all functions
- Docstrings for modules and public functions
- Async/await for I/O operations
- Use protocols for repository interfaces
- PEP 8 style

### TypeScript/React
- Functional components (hooks)
- Type all props and state
- Use `const` for components
- Document complex components
- Extract reusable logic to utils

### Naming
- Components: PascalCase (`DashboardPage`, `CarsTable`)
- Functions: camelCase (`listCars`, `handleDeleteCar`)
- Constants: UPPER_SNAKE_CASE
- Database fields: snake_case

## Debugging

### Backend
```bash
# Check logs
docker logs rental_backend_1

# Connect to MongoDB
docker exec -it rental_mongodb_1 mongosh

# View database
db.cars.find()
db.rentals.find()
```

### Frontend
- DevTools: F12 in browser
- Network tab: Check API requests/responses
- Console: JavaScript errors
- React DevTools extension

### Common Issues

**"MongoDB connection has not been initialized"**
- MongoDB service not started
- Solution: `docker-compose up` includes MongoDB

**"Backend API is not available"**
- Backend not running on port 8000
- Solution: `docker-compose up` or `uvicorn backend.app.main:app --reload`

**"Cannot delete car with an active rental"**
- This is a business rule (working as designed)
- Solution: End the rental first

**TypeScript type errors**
- Check that types match frontend/backend
- Verify imports
- Run `npm run build` to see all errors

## File Naming

- Python: `snake_case.py`
- TypeScript: `PascalCase.tsx` (components), `camelCase.ts` (utils)
- Directories: `lowercase`

## Documentation

- This file: Development workflow and common tasks
- `ARCHITECTURE.md`: System design and data model
- Docstrings: In the code for specific functions
- Comments: For "why", not "what"

## Testing

### Backend Tests Location
`tests/backend/`

Existing tests cover:
- API endpoints
- Fleet service business logic
- MongoDB repositories

### Frontend Tests
Currently not included. To add:
1. Create `frontend/src/__tests__/`
2. Use Vitest or Jest
3. Test components with React Testing Library

## Environment Variables

Backend uses `.env` file (defaults in `backend/app/core/config.py`):
```
APP_NAME=Rental Fleet Manager API
ENVIRONMENT=local
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rental_fleet
LOG_LEVEL=INFO
LOG_FILE=logs/rental_fleet.log
```

## Build & Deployment

### Docker Build
```bash
# Backend
docker build -f Dockerfile -t rental-backend .

# Frontend
docker build -f frontend/Dockerfile -t rental-frontend .
```

### Docker Compose (Development)
```bash
docker-compose up
```

Services:
- Frontend: port 5173
- Backend: port 8000
- MongoDB: port 27017

### Production Considerations
- Use separate database
- Enable authentication
- Add HTTPS/TLS
- Configure CORS properly
- Add rate limiting
- Monitor metrics
- Set resource limits

## Contributing

1. Create feature branch
2. Make changes with clear commits
3. Ensure types/tests pass
4. Document changes
5. Submit for review

## Resources

- FastAPI docs: https://fastapi.tiangolo.com
- MongoDB docs: https://docs.mongodb.com
- React docs: https://react.dev
- TypeScript docs: https://www.typescriptlang.org
