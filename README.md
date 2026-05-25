# Rental Fleet Manager

Rental Fleet Manager is a full-stack car rental management system built with React, FastAPI, MongoDB, RabbitMQ, and Docker.

The project is designed as a professional multi-service system:

- React frontend for the user interface.
- FastAPI backend for REST API endpoints and business rules.
- MongoDB for persistent NoSQL document storage.
- RabbitMQ for message-queue-based backend communication.
- A separate worker process for asynchronous event processing.
- Docker Compose for running the whole system together.

Detailed extra notes are also available in [docs/system-design.md](docs/system-design.md), but this main README explains the complete architecture in detail.

## Table Of Contents

- [1. Full System Overview](#1-full-system-overview)
- [2. Backend Architecture](#2-backend-architecture)
- [3. Backend Layer By Layer](#3-backend-layer-by-layer)
- [4. Main Backend Functions](#4-main-backend-functions)
- [5. Message Queue Architecture](#5-message-queue-architecture)
- [6. Why The Queue Improves The System](#6-why-the-queue-improves-the-system)
- [7. Frontend Architecture](#7-frontend-architecture)
- [8. Frontend Components](#8-frontend-components)
- [9. Frontend To Backend Communication](#9-frontend-to-backend-communication)
- [10. Database Design](#10-database-design)
- [11. Docker Architecture](#11-docker-architecture)
- [12. How To Run](#12-how-to-run)
- [13. API Usage Examples](#13-api-usage-examples)

## 1. Full System Overview

The system has two kinds of communication:

- Synchronous communication: the browser sends HTTP requests to FastAPI and waits for a response.
- Asynchronous communication: the backend publishes business events to RabbitMQ, and a worker consumes them later.

```mermaid
flowchart LR
    User["User"]
    Browser["Browser"]
    React["React Frontend<br/>Vite + TypeScript"]
    Nginx["Nginx<br/>serves React and proxies /api"]
    API["FastAPI Backend<br/>REST + business logic"]
    Mongo["MongoDB<br/>cars, rentals, fleet_events"]
    Rabbit["RabbitMQ<br/>message queue"]
    Worker["Event Worker<br/>queue consumer"]
    Metrics["Prometheus Metrics<br/>/metrics"]

    User --> Browser
    Browser --> React
    React --> Nginx
    Nginx --> API
    API --> Mongo
    API --> Rabbit
    Rabbit --> Worker
    Worker --> Mongo
    API --> Metrics
```

The direct user flow is simple: the user clicks in the React app, React sends an API request, FastAPI validates and applies business rules, and MongoDB stores the result.

The message queue flow happens after important business changes. For example, after a car is created, FastAPI publishes a `car.created` event to RabbitMQ. The worker consumes that event and stores it in the `fleet_events` MongoDB collection. This proves the system is using queue-based communication and gives a clean audit trail.

## 2. Backend Architecture

The backend uses layered architecture, not classic MVC.

Layered architecture means every layer has one responsibility and communicates with the layer below it. The HTTP layer does not directly write MongoDB. The service layer does not know low-level database details. The repository layer does not decide business rules.

```mermaid
flowchart TB
    Routes["API Routes<br/>backend/app/api/routes"]
    Schemas["Schemas<br/>backend/app/schemas"]
    Dependencies["Dependency Injection<br/>backend/app/api/dependencies.py"]
    Service["Service Layer<br/>backend/app/services/FleetService"]
    Repositories["Repository Layer<br/>backend/app/repositories"]
    Models["Domain Models<br/>backend/app/models"]
    Database["MongoDB Connection<br/>backend/app/db"]
    Messaging["Messaging Layer<br/>backend/app/messaging"]
    Worker["Worker Layer<br/>backend/app/workers"]
    Core["Core Utilities<br/>backend/app/core"]

    Routes --> Schemas
    Routes --> Dependencies
    Dependencies --> Service
    Service --> Repositories
    Repositories --> Models
    Repositories --> Database
    Service --> Messaging
    Messaging --> Worker
    Routes --> Core
    Service --> Core
```

### Why This Architecture Was Chosen

This project needs clear separation because it has more than one concern:

- HTTP API endpoints.
- Business rules about cars and rentals.
- MongoDB persistence.
- RabbitMQ publishing.
- Background event processing.
- Metrics and logging.

If all of that lived in one file, the project would be hard to understand and hard to maintain. Layered architecture keeps the system professional: each folder has a clear job, and future changes can be made in the correct place.

## 3. Backend Layer By Layer

### Backend Layer Flow

```mermaid
sequenceDiagram
    participant Client as React Client
    participant Route as FastAPI Route
    participant Schema as Pydantic Schema
    participant Service as FleetService
    participant Repo as Repository
    participant DB as MongoDB
    participant Queue as RabbitMQ

    Client->>Route: HTTP request with JSON
    Route->>Schema: Validate request body and query parameters
    Route->>Service: Call business operation
    Service->>Repo: Request data operation
    Repo->>DB: Read or write document
    DB-->>Repo: Return document/result
    Repo-->>Service: Return domain model
    Service->>Queue: Publish domain event if state changed
    Service-->>Route: Return domain result
    Route-->>Client: Return JSON response
```

### 3.1 API Routes Layer

Location:

```text
backend/app/api/routes
```

Main files:

- `cars.py`
- `rentals.py`
- `events.py`
- `system.py`

What this layer receives:

- HTTP requests from the frontend or API client.
- JSON request bodies.
- URL path parameters such as `car_id`.
- Query parameters such as `status=available` or `open_only=true`.

What this layer does:

- Defines the public REST API endpoints.
- Uses FastAPI decorators such as `@router.post`, `@router.get`, `@router.patch`, and `@router.delete`.
- Converts incoming HTTP data into Pydantic schema objects.
- Calls the service layer.
- Does not contain business rules directly.
- Does not write MongoDB directly.

What this layer gives to the next layer:

- Validated Python objects such as `CarCreate`, `CarUpdate`, and `RentalCreate`.
- The route passes those objects into `FleetService`.

What it returns:

- JSON responses to the frontend.
- Correct HTTP status codes such as `201 Created`, `200 OK`, `204 No Content`, `404 Not Found`, and `409 Conflict`.

Main complex function of this layer:

- `start_rental` in `backend/app/api/routes/rentals.py`.

Why it matters:

- It receives a rental request from the frontend.
- It validates the request body as `RentalCreate`.
- It calls `service.start_rental(data)`.
- It returns the created rental as JSON.
- It leaves the real business decision to the service layer.

### 3.2 Schemas Layer

Location:

```text
backend/app/schemas
```

Main files:

- `cars.py`
- `rentals.py`
- `events.py`

What this layer receives:

- Raw request data from HTTP JSON bodies.
- Data returned from the service layer that needs to be serialized to JSON.

What this layer does:

- Uses Pydantic models to validate incoming data.
- Defines required fields and optional fields.
- Defines constraints such as minimum string length and valid year range.
- Defines API response shape.

What this layer gives to the next layer:

- Clean, typed Python objects.
- Example: a request body for creating a car becomes a `CarCreate` object.

Main complex function or model of this layer:

- `CarUpdate`.

Why it matters:

- `CarUpdate` allows partial updates.
- All fields are optional, so the frontend can send only `{ "status": "maintenance" }`.
- The repository then uses `exclude_none=True` so it only updates fields that were actually provided.

### 3.3 Dependency Injection Layer

Location:

```text
backend/app/api/dependencies.py
```

What this layer receives:

- FastAPI request context.
- Current MongoDB database connection.
- Event publisher attached to the FastAPI app state.

What this layer does:

- Builds the `FleetService`.
- Injects the MongoDB repositories into the service.
- Injects the RabbitMQ event publisher into the service.
- Keeps route files clean.

What this layer gives to the next layer:

- A ready-to-use `FleetService` object.

Main complex function of this layer:

- `get_fleet_service`.

Why it matters:

- Routes do not manually create repositories.
- Tests can override dependencies easily.
- This is one of the reasons the backend is maintainable.

### 3.4 Service Layer

Location:

```text
backend/app/services/fleet_service.py
```

What this layer receives:

- Validated schemas from API routes.
- Repository interfaces for cars and rentals.
- Event publisher interface for RabbitMQ.

What this layer does:

- Contains the business rules.
- Decides whether an operation is allowed.
- Coordinates multiple repositories in one operation.
- Refreshes metrics.
- Publishes domain events after important changes.

What this layer gives to the next layer:

- It sends data operations to the repository layer.
- It sends queue events to the messaging layer.
- It returns domain documents back to the API route.

Important business rules:

- Only available cars can be rented.
- A car with an active rental cannot be deleted.
- A car cannot be manually marked as rented. It must go through the rental flow.
- A rental cannot end before its start date.
- A rented car cannot be changed away from rented until the rental is ended.

Main complex function of this layer:

- `start_rental`.

What `start_rental` does step by step:

1. Receives a `RentalCreate` object from the API route.
2. Loads the requested car by id using the car repository.
3. If the car does not exist, raises `NotFoundError`.
4. If the car is not `available`, raises `BusinessRuleError`.
5. Checks if the car already has an active rental.
6. If there is already an active rental, rejects the request.
7. Creates a rental document in MongoDB through the rental repository.
8. Updates the car status to `rented`.
9. Refreshes Prometheus metrics.
10. Publishes a `rental.started` event to RabbitMQ.
11. Returns the created rental to the route.

This is complex because it coordinates multiple system parts: car state, rental creation, status update, metrics, and message queue publishing.

### 3.5 Repository Layer

Location:

```text
backend/app/repositories
```

Main files:

- `cars.py`
- `rentals.py`
- `events.py`

What this layer receives:

- Requests from the service layer such as create car, update car, list rentals, or save event.
- Validated schema objects or ids.

What this layer does:

- Talks directly to MongoDB collections.
- Converts MongoDB documents into internal Pydantic domain models.
- Hides MongoDB query details from the service layer.
- Handles ObjectId parsing.
- Runs queries with indexes.

What this layer gives to the next layer:

- MongoDB receives actual database commands.
- The service layer receives clean domain objects such as `CarDocument` and `RentalDocument`.

Main complex function of this layer:

- `MongoRentalRepository.active_for_car`.

Why it matters:

- This function checks whether a car currently has an open rental.
- The service layer uses it to prevent double-renting the same car.
- It queries MongoDB for a rental where `car_id` matches and `end_date` is `None`.

Another important function:

- `MongoCarRepository.count_by_status`.

Why it matters:

- It uses MongoDB aggregation to count cars by status.
- The metrics layer uses it to expose the number of available and rented cars.

### 3.6 Models Layer

Location:

```text
backend/app/models
```

Main files:

- `documents.py`
- `enums.py`

What this layer receives:

- Raw database documents converted by repositories.

What this layer does:

- Defines internal backend data shapes.
- Defines the `VehicleStatus` enum.
- Keeps statuses consistent: `available`, `rented`, `maintenance`.

What this layer gives to the next layer:

- Typed domain objects used by services and API responses.

Main complex model:

- `RentalDocument`.

Why it matters:

- It represents the actual rental state.
- If `end_date` is `None`, the rental is active.
- If `end_date` has a date, the rental is closed.

### 3.7 Database Layer

Location:

```text
backend/app/db
```

Main files:

- `mongodb.py`
- `indexes.py`
- `object_ids.py`

What this layer receives:

- Application settings such as `MONGODB_URI` and `MONGODB_DATABASE`.

What this layer does:

- Connects to MongoDB.
- Retries connection during Docker startup.
- Provides the active database object.
- Closes MongoDB connection on shutdown.
- Creates indexes for performance.

What this layer gives to the next layer:

- A MongoDB database object that repositories can use.

Main complex function:

- `connect_to_mongodb`.

Why it matters:

- Docker services do not always start in perfect order.
- The API may start before MongoDB is fully ready.
- The retry loop makes startup more reliable.

### 3.8 Core Layer

Location:

```text
backend/app/core
```

Main files:

- `config.py`
- `logging.py`
- `metrics.py`
- `errors.py`

What this layer receives:

- Environment variables.
- Application events.
- Exceptions.
- Metric updates from services.

What this layer does:

- Loads configuration.
- Configures logs.
- Defines expected application errors.
- Exposes Prometheus metrics.
- Tracks backend operation counts and duration.

What this layer gives to the next layer:

- Shared infrastructure used by all other backend layers.

Main complex function:

- `track_operation`.

Why it matters:

- It wraps service methods.
- It counts how many times each operation runs.
- It measures operation duration.
- It exposes this data through `/metrics`.

## 4. Main Backend Functions

### `FleetService.add_car`

Purpose:

- Adds a new car to the fleet.

Flow:

```mermaid
flowchart LR
    Input["CarCreate<br/>model, year, status"]
    Repo["MongoCarRepository.create"]
    Metrics["refresh_metrics"]
    Event["RabbitMQ car.created"]
    Output["CarDocument"]

    Input --> Repo
    Repo --> Metrics
    Metrics --> Event
    Event --> Output
```

Why it is important:

- It is the first point where user data becomes a real database record.
- It also publishes the first queue event for the new car.

### `FleetService.start_rental`

Purpose:

- Starts a rental for an available car.

Flow:

```mermaid
flowchart TB
    Request["RentalCreate"]
    LoadCar["Load car by id"]
    CheckStatus{"Is car available?"}
    CheckActive{"Already active rental?"}
    CreateRental["Create rental"]
    UpdateCar["Set car status to rented"]
    Metrics["Refresh metrics"]
    Queue["Publish rental.started"]
    Response["Return rental"]

    Request --> LoadCar
    LoadCar --> CheckStatus
    CheckStatus -->|No| Reject["409 Conflict"]
    CheckStatus -->|Yes| CheckActive
    CheckActive -->|Yes| Reject
    CheckActive -->|No| CreateRental
    CreateRental --> UpdateCar
    UpdateCar --> Metrics
    Metrics --> Queue
    Queue --> Response
```

Why it is complex:

- It touches both cars and rentals.
- It protects against invalid state.
- It updates the database and publishes an event.

### `FleetService.end_rental`

Purpose:

- Closes an active rental and makes the car available again.

Flow:

1. Load the rental.
2. Reject if it does not exist.
3. Reject if it is already closed.
4. Validate the end date.
5. Save the end date.
6. Update the car status back to `available`.
7. Refresh metrics.
8. Publish `rental.ended`.

## 5. Message Queue Architecture

The message queue requirement is implemented with RabbitMQ.

RabbitMQ is not used for the browser request itself. The browser still uses HTTP because a user action needs an immediate response. RabbitMQ is used behind the backend for asynchronous communication between the API and the worker.

### Queue Components

```mermaid
flowchart TB
    Service["FleetService"]
    EventFactory["events.py<br/>car_event / rental_event"]
    Publisher["RabbitMQEventPublisher"]
    Exchange["RabbitMQ Direct Exchange<br/>rental.fleet.events"]
    Queue["Durable Queue<br/>rental.fleet.events.audit"]
    Consumer["RabbitMQEventConsumer"]
    Worker["event_worker.py"]
    EventRepo["MongoEventRepository"]
    Mongo["MongoDB fleet_events"]

    Service --> EventFactory
    EventFactory --> Publisher
    Publisher --> Exchange
    Exchange --> Queue
    Queue --> Consumer
    Consumer --> Worker
    Worker --> EventRepo
    EventRepo --> Mongo
```

### Event Lifecycle

```mermaid
sequenceDiagram
    participant Service as FleetService
    participant Publisher as RabbitMQEventPublisher
    participant Rabbit as RabbitMQ
    participant Worker as Event Worker
    participant Repo as MongoEventRepository
    participant DB as MongoDB

    Service->>Publisher: publish(FleetEvent)
    Publisher->>Rabbit: send persistent message
    Rabbit-->>Publisher: accepted
    Rabbit-->>Worker: deliver message
    Worker->>Repo: save(event)
    Repo->>DB: upsert by event_id
    DB-->>Repo: saved
    Worker-->>Rabbit: ack message
```

### What The API Publishes

The backend publishes these domain events:

| Event | When it is published | Payload |
|---|---|---|
| `car.created` | After a car is added | Car id, model, year, status |
| `car.updated` | After a car is updated | Updated car state |
| `car.deleted` | After a car is deleted | Deleted car data |
| `rental.started` | After a rental starts | Rental id, car id, customer, start date |
| `rental.ended` | After a rental ends | Rental id, car id, customer, start date, end date |

### Main Queue Function: `RabbitMQEventPublisher.publish`

Location:

```text
backend/app/messaging/publisher.py
```

What it receives:

- A `FleetEvent` object from the service layer.

What it does:

1. Checks if a RabbitMQ exchange connection exists.
2. If not connected, it connects to RabbitMQ.
3. Converts the event to JSON.
4. Creates a persistent RabbitMQ message.
5. Publishes the message with routing key `fleet.event`.
6. Logs that the event was published.

What it gives to the next part:

- RabbitMQ receives the event message and stores it in the durable queue.

Why it is complex:

- It is responsible for crossing process boundaries.
- The API and worker are separate containers.
- The publisher must connect to RabbitMQ, declare exchange/queue, bind the routing key, and send a durable message.

### Main Worker Function: `RabbitMQEventConsumer._handle_message`

Location:

```text
backend/app/messaging/consumer.py
```

What it receives:

- A raw RabbitMQ message from the queue.

What it does:

1. Opens the RabbitMQ message processing context.
2. Parses the message body as a `FleetEvent`.
3. Calls the worker handler.
4. The handler saves the event through `MongoEventRepository`.
5. If everything succeeds, RabbitMQ receives an acknowledgement.
6. If processing fails, the message can be requeued.

What it gives to the next part:

- A validated event object is passed into the worker handler.

Why it is important:

- This function is the bridge between RabbitMQ and the backend application logic.
- It keeps queue processing separate from user-facing API requests.

## 6. Why The Queue Improves The System

The queue improves the system because it decouples immediate user actions from background processing.

Without a queue:

```mermaid
flowchart LR
    API["API request"]
    Work1["Database write"]
    Work2["Audit logging"]
    Work3["Future email/report/integration"]
    Response["Return response"]

    API --> Work1 --> Work2 --> Work3 --> Response
```

In this design, the user waits for every extra task.

With a queue:

```mermaid
flowchart LR
    API["API request"]
    Work1["Database write"]
    Publish["Publish event"]
    Response["Return response"]
    Queue["RabbitMQ"]
    Worker["Worker handles extra tasks"]

    API --> Work1 --> Publish --> Response
    Publish --> Queue --> Worker
```

The user waits only for the important main operation. The worker can process background work separately.

Benefits:

- Better performance: the API can return faster because background work is moved out of the request path.
- Better reliability: if the worker is temporarily down, RabbitMQ can keep messages until the worker returns.
- Better scalability: more workers can be added if there are many events.
- Better separation: the API focuses on business commands, the worker focuses on asynchronous processing.
- Better future growth: the same queue can later support emails, reports, notifications, billing, and external integrations.

Important note:

- The current event publishing is intentionally simple and appropriate for this exercise.
- A larger production system could add the outbox pattern to guarantee that database writes and event publishing are committed together.

## 7. Frontend Architecture

The frontend is built with React, Vite, and TypeScript.

It is organized by responsibility:

```mermaid
flowchart TB
    Main["main.tsx"]
    App["App.tsx"]
    Dashboard["DashboardPage.tsx"]
    API["api/fleetApi.ts"]
    HTTP["api/http.ts"]
    CarFeature["features/cars"]
    RentalFeature["features/rentals"]
    Components["components"]
    Types["types/fleet.ts"]
    Utils["utils"]
    Styles["styles/global.css"]

    Main --> App
    App --> Dashboard
    Dashboard --> API
    API --> HTTP
    Dashboard --> CarFeature
    Dashboard --> RentalFeature
    Dashboard --> Components
    Dashboard --> Types
    Dashboard --> Utils
    App --> Styles
```

The frontend does not contain database logic. It only manages UI state and sends API requests.

## 8. Frontend Components

### Main Integration Component: `DashboardPage`

Location:

```text
frontend/src/pages/DashboardPage.tsx
```

What it receives:

- It does not receive external props.
- It loads cars and rentals from the backend when the page opens.

What it does:

- Stores `cars`, `rentals`, filters, selected rental car id, loading state, saving state, success messages, and errors.
- Calls `listCars()` and `listRentals()` to load dashboard data.
- Passes data into child components.
- Receives form submissions from child components.
- Calls API functions to create cars, update statuses, delete cars, start rentals, and end rentals.
- Reloads the dashboard after every successful action.

What it gives to the next components:

- Car data goes to `CarsTable`.
- Rental data goes to `RentalsTable`.
- Available cars go to `RentalForm`.
- Callback functions go to forms and tables.

Main complex function:

- `runAction`.

Why it matters:

- All user actions share the same pattern: set saving state, clear old messages, run API call, reload data, show success or error.
- Instead of repeating that logic in every handler, `runAction` centralizes it.

### `CarForm`

Location:

```text
frontend/src/features/cars/CarForm.tsx
```

Purpose:

- Lets the user add a new car.

What it collects:

- Car model.
- Car year.
- Initial status.

What it sends upward:

- A `CarCreatePayload` object.

Integration:

- `DashboardPage` passes `handleCreateCar` into `CarForm`.
- `CarForm` submits the payload.
- `DashboardPage` calls `createCar(payload)`.

### `CarsTable`

Location:

```text
frontend/src/features/cars/CarsTable.tsx
```

Purpose:

- Shows all cars.
- Shows each car status.
- Shows active rental information.
- Provides actions: rent, maintenance/available toggle, delete.

What it receives:

- `cars`
- `rentals`
- `statusFilter`
- action callbacks

What it does:

- Filters cars by status.
- Finds active rental information for each car.
- Shows the `Rent` button only for available cars.
- Shows maintenance toggle only for cars that are not rented.

What it sends upward:

- Selected car id for rental.
- Status update requests.
- Delete requests.

### `RentalForm`

Location:

```text
frontend/src/features/rentals/RentalForm.tsx
```

Purpose:

- Starts a new rental.

What it receives:

- Only available cars.
- The currently selected car id.
- A callback to update selected car id.
- A submit callback.

What it does:

- Shows a dropdown of available cars.
- Collects customer name.
- Collects start date.
- Automatically resets the selected car if the old selected car is no longer available.

Why the selected-car logic matters:

- A car may move from available to maintenance or rented.
- The UI must not keep sending a stale car id.
- The form now ensures it submits a valid available car id.

### `RentalsTable`

Location:

```text
frontend/src/features/rentals/RentalsTable.tsx
```

Purpose:

- Shows rental records.
- Shows whether each rental is open or closed.
- Lets the user end an open rental.

What it receives:

- All cars.
- All rentals.
- An `onEndRental` callback.

What it does:

- Converts car ids into readable car names.
- Shows customer, start date, and end date.
- Shows `End rental` for open rentals.

### Shared Components

| Component | Location | Purpose |
|---|---|---|
| `AppHeader` | `frontend/src/components/AppHeader.tsx` | Top header and refresh action. |
| `StatusBadge` | `frontend/src/components/StatusBadge.tsx` | Visual status label for cars. |
| `SummaryTile` | `frontend/src/components/SummaryTile.tsx` | Dashboard summary numbers. |

## 9. Frontend To Backend Communication

The frontend uses a typed API client:

```text
frontend/src/api/fleetApi.ts
frontend/src/api/http.ts
```

`fleetApi.ts` defines the exact business requests. `http.ts` defines the generic `request<T>()` wrapper.

### Request Flow

```mermaid
sequenceDiagram
    participant Component as React Component
    participant Dashboard as DashboardPage
    participant ApiClient as fleetApi.ts
    participant Http as request wrapper
    participant Nginx as Nginx / Vite Proxy
    participant FastAPI as FastAPI

    Component->>Dashboard: user submits action
    Dashboard->>ApiClient: call typed API function
    ApiClient->>Http: typed request with path and options
    Http->>Nginx: fetch("/api/...")
    Nginx->>FastAPI: proxy to backend
    FastAPI-->>Nginx: JSON response
    Nginx-->>Http: HTTP response
    Http-->>ApiClient: typed result
    ApiClient-->>Dashboard: data
    Dashboard-->>Component: updated state
```

### API Functions In `fleetApi.ts`

| Function | HTTP request | Used for |
|---|---|---|
| `listCars(status?)` | `GET /api/cars` or `GET /api/cars?status=...` | Load cars for the dashboard. |
| `createCar(payload)` | `POST /api/cars` | Add a new car. |
| `updateCar(carId, payload)` | `PATCH /api/cars/{car_id}` | Change car status or details. |
| `deleteCar(carId)` | `DELETE /api/cars/{car_id}` | Remove a car. |
| `listRentals(openOnly?)` | `GET /api/rentals` | Load rental records. |
| `createRental(payload)` | `POST /api/rentals` | Start a rental. |
| `endRental(rentalId, endDate)` | `POST /api/rentals/{rental_id}/end?end_date=...` | Close a rental and free the car. |

### Example: Add Car From UI

```mermaid
sequenceDiagram
    participant User
    participant CarForm
    participant Dashboard
    participant APIClient
    participant Backend
    participant Mongo
    participant Rabbit

    User->>CarForm: fills model/year/status
    CarForm->>Dashboard: onSubmit(CarCreatePayload)
    Dashboard->>APIClient: createCar(payload)
    APIClient->>Backend: POST /api/cars
    Backend->>Mongo: insert car
    Backend->>Rabbit: publish car.created
    Backend-->>APIClient: created car JSON
    APIClient-->>Dashboard: Car
    Dashboard->>Backend: reload cars and rentals
    Dashboard-->>CarForm: clear/save complete
```

### Error Handling

`request<T>()` handles API errors in one place.

What it does:

- Sends JSON headers.
- Parses error response bodies.
- Turns backend errors into `ApiError`.
- Handles `204 No Content`.
- Shows a helpful message if `/api` is missing.

Example:

- If backend returns `409 Conflict` with `{ "detail": "Only available cars can be rented." }`, the frontend displays that backend message.

## 10. Database Design

MongoDB is used because the app is JSON-based, document-oriented, and event-friendly.

```mermaid
erDiagram
    CARS {
        ObjectId _id
        string model
        int year
        string status
    }

    RENTALS {
        ObjectId _id
        string car_id
        string customer_name
        date start_date
        date end_date
    }

    FLEET_EVENTS {
        string event_id
        string event_type
        string aggregate_type
        string aggregate_id
        datetime occurred_at
        object payload
    }

    CARS ||--o{ RENTALS : "car_id"
```

Collections:

| Collection | Purpose |
|---|---|
| `cars` | Stores the fleet. Each document has model, year, and status. |
| `rentals` | Stores rental records. Open rentals have `end_date = null`. |
| `fleet_events` | Stores events consumed from RabbitMQ. |

Indexes:

| Index | Why |
|---|---|
| `cars.status` | Fast filtering by car status. |
| `rentals.car_id + rentals.end_date` | Fast lookup of active rental by car. |
| `fleet_events.event_id` unique | Prevents duplicate event audit rows. |
| `fleet_events.occurred_at` | Fast sorting of recent queue events. |

Why NoSQL is a good choice here:

- The frontend and backend already exchange JSON.
- MongoDB stores JSON-like documents naturally.
- Event payloads can vary by event type.
- It is easy to add future fields such as branch, price, mileage, or customer metadata.
- MongoDB can scale horizontally with sharding if the dataset grows.

## 11. Docker Architecture

Docker runs the project as five services:

```mermaid
flowchart TB
    subgraph Compose["docker-compose.yml"]
        Frontend["frontend<br/>React build served by Nginx<br/>port 5173"]
        API["api<br/>FastAPI + Uvicorn<br/>port 8000"]
        Worker["worker<br/>Python event worker"]
        Mongo["mongo<br/>MongoDB 7<br/>port 27017"]
        Rabbit["rabbitmq<br/>RabbitMQ + management UI<br/>ports 5672 and 15672"]
    end

    Browser["Browser"]
    VolData["volume: rental-fleet-data"]
    VolLogs["volume: rental-fleet-logs"]
    VolRabbit["volume: rental-fleet-rabbitmq"]

    Browser -->|http://127.0.0.1:5173| Frontend
    Frontend -->|proxy /api| API
    API --> Mongo
    API --> Rabbit
    Rabbit --> Worker
    Worker --> Mongo
    Mongo --> VolData
    API --> VolLogs
    Worker --> VolLogs
    Rabbit --> VolRabbit
```

### Backend Dockerfile

Location:

```text
Dockerfile
```

Used by:

- `api`
- `worker`

What it does:

1. Starts from `python:3.12-slim`.
2. Sets `/app` as the working directory.
3. Copies `pyproject.toml` and `README.md`.
4. Copies the `backend` folder.
5. Installs the Python package using `pip install --no-cache-dir .`.
6. Exposes port `8000`.
7. Default command starts Uvicorn for the API.

Why the same Dockerfile is used for API and worker:

- Both are Python backend processes.
- Both need the same backend code and dependencies.
- The API uses the default Dockerfile command.
- The worker overrides the command in `docker-compose.yml`:

```yaml
command: ["python", "-m", "backend.app.workers.event_worker"]
```

### Frontend Dockerfile

Location:

```text
frontend/Dockerfile
```

Used by:

- `frontend`

It is a multi-stage Dockerfile:

```mermaid
flowchart LR
    Node["Stage 1<br/>node:22-alpine"]
    Build["npm ci<br/>npm run build"]
    Dist["dist files"]
    Nginx["Stage 2<br/>nginx:1.27-alpine"]
    Serve["Serve static React app"]

    Node --> Build
    Build --> Dist
    Dist --> Nginx
    Nginx --> Serve
```

Stage 1:

- Installs Node dependencies.
- Compiles TypeScript.
- Builds optimized static files into `dist`.

Stage 2:

- Uses Nginx instead of Node for runtime.
- Copies the production build into `/usr/share/nginx/html`.
- Copies `frontend/nginx.conf`.
- Serves the React app on port `80` inside the container.

Why this is better:

- The final frontend image is smaller.
- It does not need the full Node development environment at runtime.
- Nginx is efficient for serving static frontend files.

### Frontend Nginx Configuration

Location:

```text
frontend/nginx.conf
```

What it does:

- Serves React static files.
- Proxies `/api/` to `http://api:8000/api/`.
- Proxies `/health` to `http://api:8000/health`.
- Proxies `/metrics` to `http://api:8000/metrics`.
- Uses `try_files` so React routes still load correctly.

Why this matters:

- In the browser, the frontend can call `/api/cars`.
- Nginx forwards that request to the backend container named `api`.
- The browser does not need to know Docker internal container addresses.

### MongoDB Docker Setup

MongoDB does not use a custom Dockerfile.

In `docker-compose.yml`, it uses the official image:

```yaml
image: mongo:7
```

What Compose adds:

- Container name: `rental-fleet-mongo`.
- Port mapping: `27017:27017`.
- Volume: `rental-fleet-data:/data/db`.

Why the volume matters:

- MongoDB data survives container restarts.
- Without a volume, data would disappear when the container is removed.

### RabbitMQ Docker Setup

RabbitMQ also does not use a custom Dockerfile.

In `docker-compose.yml`, it uses:

```yaml
image: rabbitmq:3-management
```

What Compose adds:

- Container name: `rental-fleet-rabbitmq`.
- AMQP port: `5672`.
- Management UI port: `15672`.
- Volume: `rental-fleet-rabbitmq:/var/lib/rabbitmq`.

Why the management image is useful:

- It includes the RabbitMQ web dashboard.
- You can inspect queues, exchanges, and messages.
- Open it at `http://127.0.0.1:15672`.
- Login is `guest / guest`.

### How Docker Compose Integrates Everything

`docker-compose.yml` is the orchestrator. It decides:

- Which services exist.
- Which images are built or pulled.
- Which ports are exposed to your computer.
- Which environment variables each service receives.
- Which volumes persist data.
- Which services depend on other services.

Service integration:

| Service | Built from | Talks to | Purpose |
|---|---|---|---|
| `frontend` | `frontend/Dockerfile` | `api` | Serves React and proxies API requests. |
| `api` | root `Dockerfile` | `mongo`, `rabbitmq` | Handles REST API, business rules, metrics, and event publishing. |
| `worker` | root `Dockerfile` | `mongo`, `rabbitmq` | Consumes queue events and stores them in MongoDB. |
| `mongo` | `mongo:7` image | `api`, `worker` | Stores cars, rentals, and events. |
| `rabbitmq` | `rabbitmq:3-management` image | `api`, `worker` | Message queue between API and worker. |

Internal Docker networking:

- The API connects to MongoDB using `mongodb://mongo:27017`.
- The API connects to RabbitMQ using `amqp://guest:guest@rabbitmq:5672/`.
- The frontend Nginx proxy connects to the backend using `http://api:8000`.
- These names work because Docker Compose creates an internal network where services can reach each other by service name.

## 12. How To Run

### Run Everything With Docker

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental
docker compose up --build
```

Open:

```text
React app: http://127.0.0.1:5173
API docs: http://127.0.0.1:8000/docs
Metrics: http://127.0.0.1:8000/metrics
Queue events: http://127.0.0.1:8000/api/events?limit=5
RabbitMQ dashboard: http://127.0.0.1:15672
```

RabbitMQ login:

```text
guest / guest
```

Stop:

```powershell
docker compose down
```

Reset database and RabbitMQ volumes:

```powershell
docker compose down -v
```

### Run Backend Locally

You need MongoDB and RabbitMQ running first. Docker is the easiest way to run them.

Then:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

In another terminal, run the worker:

```powershell
.\.venv\Scripts\python.exe -m backend.app.workers.event_worker
```

### Run Frontend Locally

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

The Vite dev server proxies `/api` requests to the backend.

### Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### Build Frontend

```powershell
cd frontend
npm.cmd run build
```

## 13. API Usage Examples

### Add A Car

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/cars `
  -ContentType "application/json" `
  -Body '{"model":"Toyota Corolla","year":2024,"status":"available"}'
```

### List Cars

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/cars
```

### Start A Rental

Replace `CAR_ID_HERE` with an available car id.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/rentals `
  -ContentType "application/json" `
  -Body '{"car_id":"CAR_ID_HERE","customer_name":"Dana Levi","start_date":"2026-05-25"}'
```

### End A Rental

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/rentals/RENTAL_ID_HERE/end?end_date=2026-05-25"
```

### See Queue Events

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/events?limit=5
```

If the queue is working, actions like adding a car or starting a rental create events such as:

```json
{
  "event_type": "car.created",
  "aggregate_type": "car",
  "aggregate_id": "example-id",
  "payload": {
    "model": "Toyota Corolla",
    "year": 2024,
    "status": "available"
  }
}
```

## Final Architecture Summary

This project uses React for the user interface, FastAPI for backend API and business logic, MongoDB for NoSQL document storage, RabbitMQ for asynchronous queue-based communication, and Docker Compose to run all services together.

The most important design decision is separation of responsibilities. The frontend only handles UI and API calls. The API layer handles HTTP. The service layer handles business rules. The repository layer handles MongoDB. The messaging layer handles RabbitMQ. The worker handles asynchronous processing. Docker Compose connects all services into one runnable system.
