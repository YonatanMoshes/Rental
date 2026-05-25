# Documentation Index

Complete guide to all documentation files in the Rental Fleet Manager project.

## Quick Start

New to this project? Start here:

1. **[README.md](README.md)** - High-level overview, how to run locally
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and components
3. **[API.md](API.md)** - REST API endpoint reference
4. **[DEVELOPMENT.md](DEVELOPMENT.md)** - Developer guide and common tasks

## Documentation Files

### Project Overview

**[README.md](README.md)**
- Quick start guide
- Technology stack overview
- How to run backend, frontend, tests
- Links to API docs and metrics

**[ARCHITECTURE.md](ARCHITECTURE.md)**
- High-level system architecture
- Directory structure with explanations
- Data model (Car, Rental documents)
- API endpoints overview
- Business logic and rules
- Error handling strategy
- State management approach
- Development workflow
- Security considerations
- Performance optimization notes
- Monitoring and observability
- Deployment instructions

### Developer Reference

**[DEVELOPMENT.md](DEVELOPMENT.md)**
- Backend layered architecture explanation
- Frontend component structure
- Common tasks (adding fields, endpoints, business logic)
- Running tests
- Code conventions (Python, TypeScript, naming)
- Debugging tips
- Common issues and solutions
- File naming conventions
- Testing strategies
- Environment variables
- Build and deployment

**[API.md](API.md)**
- Complete REST API reference
- Authentication (currently none)
- Response formats and status codes
- All endpoints documented:
  - Cars (list, create, update, delete)
  - Rentals (list, start, end)
  - System (health, metrics)
- Error responses with examples
- Code examples (JavaScript, Python, cURL)
- CORS and rate limiting notes

### Source Code Documentation

**Backend Python Files** (`backend/app/`)

All Python files include:
- Module docstrings explaining purpose
- Function/class docstrings with parameters
- Business logic explanations
- Type hints throughout

Key files:
- `main.py` - FastAPI app setup and lifecycle
- `api/routes/` - HTTP endpoint handlers
- `services/fleet_service.py` - Business logic layer
- `repositories/` - MongoDB data access
- `models/` - Domain model definitions
- `schemas/` - Request/response validation
- `core/` - Configuration, errors, logging, metrics
- `db/` - Database connection and utilities

**Frontend TypeScript Files** (`frontend/src/`)

All TypeScript/React files include:
- File/component documentation at top
- Type definitions with JSDoc comments
- Prop descriptions
- Function parameter documentation

Key files:
- `main.tsx` - React entry point
- `App.tsx` - Root component
- `api/http.ts` - HTTP client utilities
- `api/fleetApi.ts` - Typed API calls
- `types/fleet.ts` - Type definitions
- `pages/DashboardPage.tsx` - Main state orchestrator
- `components/` - Reusable UI components
- `features/cars/`, `features/rentals/` - Feature components
- `utils/` - Helper functions

### Configuration Files

**[docker-compose.yml](docker-compose.yml)**
- Local development environment setup
- Service definitions (frontend, backend, MongoDB)
- Volume and port configuration
- Usage instructions in comments

**[Dockerfile](Dockerfile)** (Backend)
- Multi-stage build
- Python 3.12 slim base
- Dependency installation
- Uvicorn startup command
- Usage and build instructions in comments

**[frontend/Dockerfile](frontend/Dockerfile)**
- Multi-stage Node.js + Nginx build
- React bundle optimization
- Static file serving
- Usage and build instructions in comments

**[frontend/vite.config.ts](frontend/vite.config.ts)**
- Development server configuration
- API proxy setup for local development
- Build optimization settings
- Environment variable documentation

**[pyproject.toml](pyproject.toml)**
- Python project metadata
- Core and dev dependencies
- Test configuration

**[frontend/package.json](frontend/package.json)**
- Node.js dependencies
- Build and dev scripts
- TypeScript and Vite configuration

## How to Use This Documentation

### For New Contributors

1. Start with **README.md** to understand what the project does
2. Read **ARCHITECTURE.md** to learn the system design
3. Check **DEVELOPMENT.md** for your specific area:
   - Backend work → "Backend Layers" section
   - Frontend work → "Frontend Structure" section
4. Refer to **API.md** to understand endpoints
5. Check inline code documentation (docstrings) for implementation details

### For Backend Development

- **DEVELOPMENT.md**: Backend structure, common tasks, debugging
- **ARCHITECTURE.md**: Data model, business logic rules
- **API.md**: Endpoint specifications
- **Code comments**: Inline documentation in `backend/app/`

### For Frontend Development

- **DEVELOPMENT.md**: Frontend structure, component organization
- **ARCHITECTURE.md**: System design, state management
- **API.md**: How to use each endpoint
- **Code comments**: Inline documentation in `frontend/src/`

### For API Integration

- **API.md**: Complete endpoint reference with examples
- **README.md**: How to run the backend
- **ARCHITECTURE.md**: Data model and business rules

### For DevOps / Deployment

- **docker-compose.yml**: Local development setup
- **Dockerfile**, **frontend/Dockerfile**: Production builds
- **DEVELOPMENT.md**: Build and deployment section
- **ARCHITECTURE.md**: Deployment notes

### For Testing

- **DEVELOPMENT.md**: Testing section
- **README.md**: How to run tests
- `tests/backend/` directory for test examples

## Documentation Standards

All documentation follows these principles:

- **Keep it concise** - Get to the point quickly
- **Be informative** - Explain the "what" and "why"
- **Show examples** - Code samples where helpful
- **Stay current** - Update when architecture changes
- **Link between docs** - Cross-reference related topics

## Adding New Documentation

When adding new features, update:

1. **Inline code comments** - Always the first documentation
2. **Relevant .md file** - Architecture, API, development guide
3. **This index** - Add reference to new documentation

## File-by-File Guide

### Configuration & Setup
- `docker-compose.yml` - Local dev environment
- `Dockerfile` - Backend container
- `frontend/Dockerfile` - Frontend container
- `pyproject.toml` - Python dependencies
- `frontend/package.json` - Node dependencies

### Backend
- `backend/app/main.py` - App initialization
- `backend/app/api/routes/` - HTTP handlers
- `backend/app/services/` - Business logic
- `backend/app/repositories/` - Data access
- `backend/app/models/` - Domain models
- `backend/app/schemas/` - Validation
- `backend/app/core/` - Infrastructure
- `backend/app/db/` - Database utilities
- `tests/backend/` - Test cases

### Frontend
- `frontend/src/main.tsx` - React entry
- `frontend/src/App.tsx` - Root component
- `frontend/src/pages/` - Full pages
- `frontend/src/features/` - Feature areas
- `frontend/src/components/` - Reusable parts
- `frontend/src/api/` - API communication
- `frontend/src/types/` - Type definitions
- `frontend/src/utils/` - Helpers
- `frontend/src/styles/` - Styling

## Quick Links

- [Live API Documentation](http://127.0.0.1:8000/docs) (when running)
- [Prometheus Metrics](http://127.0.0.1:8000/metrics) (when running)
- [Frontend Dashboard](http://127.0.0.1:5173) (when running)

## Contributing

When modifying any file:

1. Keep docstrings up to date
2. Update relevant .md documentation
3. Add comments for non-obvious logic
4. Follow naming conventions from DEVELOPMENT.md
5. Ensure types/tests pass

## Questions?

- Technical details → Check inline code comments
- "How do I...?" → See DEVELOPMENT.md
- API usage → See API.md
- Architecture questions → See ARCHITECTURE.md
- General info → See README.md
