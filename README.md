# Rental Fleet Manager

Rental Fleet Manager is a full-stack car rental management system built with React, FastAPI, MongoDB, RabbitMQ, and Docker.

The project is designed as a professional multi-service system:

- React frontend for the user interface.
- FastAPI backend for REST API endpoints and app logic checks.
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
- [14. File And Function Guide](#14-file-and-function-guide)
- [15. Testing Guide](#15-testing-guide)

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
    API["FastAPI Backend<br/>REST + app logic"]
    Mongo["MongoDB<br/>cars, rentals, fleet_events"]
    Rabbit["RabbitMQ<br/>message queue"]
    Worker["Event Worker<br/>queue consumer"]
    Metrics["Prometheus Metrics<br/>/metrics"]

    User -->|"uses the app in"| Browser
    Browser -->|"loads and runs"| React
    React -->|"sends fetch requests to"| Nginx
    Nginx -->|"proxies /api calls to"| API
    API -->|"reads/writes documents in"| Mongo
    API -->|"publishes domain events to"| Rabbit
    Rabbit -->|"delivers queued events to"| Worker
    Worker -->|"stores consumed events in"| Mongo
    API -->|"exposes measurements at"| Metrics
```

The direct user flow is simple: the user clicks in the React app, React sends an API request, FastAPI validates the data, the service checks whether the requested action is legal for this app, and MongoDB stores the result.

The message queue flow happens after important business changes. For example, after a car is created, FastAPI publishes a `car.created` event to RabbitMQ. The worker consumes that event and stores it in the `fleet_events` MongoDB collection. This proves the system is using queue-based communication and gives a clean audit trail.

## 2. Backend Architecture

The backend uses layered architecture, not classic MVC.

Layered architecture means every layer has one responsibility and communicates with the layer below it. The HTTP layer does not directly write MongoDB. The service layer checks the app logic but does not know low-level database details. The repository layer talks to MongoDB but does not decide whether a rental action is legal.

```mermaid
flowchart TB
    Routes["API Routes<br/>backend/app/api/routes"]
    Schemas["Schemas<br/>backend/app/schemas"]
    Dependencies["Dependency Injection<br/>backend/app/api/dependencies.py"]
    Service["Service Layer<br/>backend/app/services/FleetService<br/>app logic and legal action checks"]
    Repositories["Repository Layer<br/>backend/app/repositories"]
    Models["Domain Models<br/>backend/app/models"]
    Database["MongoDB Connection<br/>backend/app/db"]
    Messaging["Messaging Layer<br/>backend/app/messaging"]
    Worker["Worker Layer<br/>backend/app/workers"]
    Core["Core Utilities<br/>backend/app/core"]

    Routes -->|"receives HTTP data and asks schemas to parse it"| Schemas
    Routes -->|"asks FastAPI to inject ready objects"| Dependencies
    Dependencies -->|"builds FleetService with repositories and publisher"| Service
    Service -->|"asks for saved/loaded fleet data"| Repositories
    Repositories -->|"returns clean domain objects"| Models
    Repositories -->|"runs actual MongoDB queries"| Database
    Service -->|"publishes events after successful changes"| Messaging
    Messaging -->|"queue consumer runs in"| Worker
    Routes -->|"uses shared errors and responses"| Core
    Service -->|"updates metrics and logs app actions"| Core
```

### Why This Architecture Was Chosen

This project needs clear separation because it has more than one concern:

- HTTP API endpoints.
- App logic about which car and rental actions are legal.
- MongoDB persistence.
- RabbitMQ publishing.
- Background event processing.
- Metrics and logging.

If all of that lived in one file, the project would be hard to understand and hard to maintain. Layered architecture keeps the system professional: each folder has a clear job, and future changes can be made in the correct place.

## 3. Backend Layer By Layer

The diagram below shows the exact path of data through the backend. The words on the arrows explain what each layer gives to the next layer.

```mermaid
flowchart TD
    Client["Frontend / Browser"]
    API["API Routes Layer<br/>FastAPI route functions"]
    Schemas["Schema Layer<br/>Pydantic models"]
    Service["Service Layer<br/>app logic and legal action checks"]
    LogicCheck["Legal Action Check<br/>example: car cannot be in maintenance"]
    Repository["Repository Layer<br/>MongoDB access"]
    Models["Models Layer<br/>CarDocument / RentalDocument"]
    Mongo["MongoDB"]
    Queue["RabbitMQ Publisher"]

    Client -->|"sends HTTP request with JSON body, URL params, or query params"| API
    API -->|"uses function type hints to know which schema should parse the JSON"| Schemas
    Schemas -->|"returns clean Python objects like CarCreate or RentalCreate"| API
    API -->|"passes validated object to FleetService"| Service
    Service -->|"checks if requested action is legal in this app"| LogicCheck
    LogicCheck -->|"if action is allowed, continue"| Repository
    Repository -->|"converts MongoDB documents into domain models"| Models
    Repository -->|"reads and writes documents"| Mongo
    Models -->|"returns typed objects back to service"| Service
    Service -->|"publishes event after successful change"| Queue
    Service -->|"returns final result to route"| API
    API -->|"returns JSON response and HTTP status"| Client
```

### 3.1 API Routes Layer

Location:

```text
backend/app/api/routes
```

The API routes layer is the first backend layer that receives a request from the frontend. It receives an HTTP request, and that request may include a JSON body, a path value like `car_id`, or a query value like `status=available`. The important idea is that this layer translates web data into Python data. For example, when the frontend sends `POST /api/cars` with JSON like `{ "model": "Mazda 3", "year": 2026 }`, the `add_car` route expects a `CarCreate` object in its function signature. FastAPI reads that type hint and understands that the JSON body must be transformed into a `CarCreate` object. If the JSON is missing a required field or the year is invalid, FastAPI rejects it before the service layer is called.

After the API route has a clean object, it passes that object to the service layer. The route itself should stay thin: it should not decide if a car can be rented, it should not manually write to MongoDB, and it should not publish queue messages directly. Its main job is to receive the HTTP request, let the schema validate it, call the correct service function, and return a clear JSON response with the correct HTTP status.

Example: `add_car(data: CarCreate, service: FleetService = Depends(...))` receives a JSON request from React, FastAPI converts that JSON into `CarCreate`, and then the route calls `service.add_car(data)`.

### 3.2 Schemas Layer

Location:

```text
backend/app/schemas
```

Schemas are a layer, but they are a small supporting layer, not a logic layer. They do not decide what the app is allowed to do. Instead, they define the shape of the data that moves between layers. A schema answers questions like: What fields are required? Which fields are optional? What type should each field be? What range is legal for a number? What should the API response look like?

For example, `CarCreate` defines that a new car must have a `model`, a `year`, and can optionally have a `status`. The year must be between 1886 and 2100. This means that if the frontend sends `"year": "hello"` or sends an empty model, the request is not accepted as valid data. The route layer receives the clean `CarCreate` object only after the schema has checked the data format.

Another example is `CarUpdate`. This schema has optional fields because updating a car may only change one value. The frontend can send only `{ "status": "maintenance" }`, and the backend understands that only the status should change.

### 3.3 Dependency Injection Layer

Location:

```text
backend/app/api/dependencies.py
```

The dependency layer builds the objects that routes need before the route function runs. The route does not manually create the service, the car repository, the rental repository, or the RabbitMQ publisher. FastAPI uses `Depends(...)` to call dependency functions and give the route a ready-to-use `FleetService`.

The main example is `get_fleet_service`. This function receives the active MongoDB database object, creates `MongoCarRepository` and `MongoRentalRepository`, receives the RabbitMQ event publisher from the app state, and then returns one `FleetService` object. This keeps the route clean because the route only says it needs a `FleetService`; it does not care how that service is created.

This layer also makes testing easier. In tests, the real MongoDB repositories can be replaced with in-memory repositories, so the service can be tested without running a real database.

### 3.4 Service Layer

Location:

```text
backend/app/services/fleet_service.py
```

The service layer is the app logic layer. This is where the backend checks whether the requested action is legal in this rental system. A clearer way to describe it is: this layer protects the app from actions that do not make sense. For example, it prevents renting a car that is in maintenance, prevents deleting a car that has an open rental, and prevents ending a rental before its start date.

The service layer receives clean Python objects from the route layer, such as `CarCreate` or `RentalCreate`. Then it asks repositories for the current data it needs. If the request is legal, it tells repositories to save or update data. After the data change succeeds, it refreshes metrics and publishes a RabbitMQ event. Finally, it returns the result back to the route layer.

Example: `start_rental` receives a `RentalCreate` object. It loads the car, checks if the car exists, checks if the car status is `available`, checks if there is already an active rental for that car, creates the rental, updates the car status to `rented`, publishes `rental.started`, and returns the created rental. This function is the best example of why the service layer exists: many things must happen in the correct order, and this logic should not be inside the route or the database repository.

### 3.5 Repository Layer

Location:

```text
backend/app/repositories
```

The repository layer is the database access layer. It receives requests from the service layer such as "create this car", "find this car by id", "list all rentals", or "save this consumed event". It does not decide whether the requested action is legal. It only knows how to talk to MongoDB and how to convert MongoDB documents into clean Python domain objects.

For example, `MongoCarRepository.create` receives a `CarCreate` object from the service. It converts that object into JSON-like data, inserts it into the `cars` collection, loads the created MongoDB document, and returns a `CarDocument`. The service layer does not need to know how MongoDB `_id` values work or how the query is written.

Another example is `MongoRentalRepository.active_for_car`. The service uses this when it needs to know whether a car already has an open rental. The repository checks MongoDB for a rental with the same `car_id` and `end_date = None`, then returns a `RentalDocument` if one exists.

### 3.6 Models Layer

Location:

```text
backend/app/models
```

The models layer defines the internal objects that the backend uses after data has already been validated or loaded. The schemas layer describes API input and output. The models layer describes records used inside the backend itself. This keeps the code clear because a raw MongoDB document is not passed everywhere; it is converted into a typed model such as `CarDocument` or `RentalDocument`.

For example, `RentalDocument` represents a rental after it exists in the system. If `end_date` is `None`, the rental is still open. If `end_date` has a date, the rental is closed. The service layer can read this model and make decisions without needing to inspect raw MongoDB dictionaries.

The `VehicleStatus` enum also lives here. It keeps status values consistent, so the app uses `available`, `rented`, and `maintenance` in one controlled way instead of writing random strings in different files.

### 3.7 Database Layer

Location:

```text
backend/app/db
```

The database layer manages the MongoDB connection itself. It receives configuration values such as `MONGODB_URI` and `MONGODB_DATABASE`, opens the connection when the API starts, gives repositories access to the active database, and closes the connection when the app shuts down. This layer also creates indexes that make important queries faster.

The most important function is `connect_to_mongodb`. Docker containers do not always become ready at the exact same second. The API container may start before MongoDB is fully ready to accept connections. Because of that, `connect_to_mongodb` uses a retry loop. It keeps trying to ping MongoDB before it gives up. This makes the Docker startup more stable.

The `indexes.py` file is also important. It creates indexes for `cars.status`, active rentals by `car_id` and `end_date`, and consumed event lookup by `event_id`. These indexes help the app stay fast as the data grows.

### 3.8 Core Layer

Location:

```text
backend/app/core
```

The core layer contains shared infrastructure that other backend layers need. It does not represent one feature like cars or rentals. Instead, it provides common support such as configuration, logging, metrics, and expected error types.

For example, `config.py` reads environment variables like the MongoDB URL, RabbitMQ URL, log level, and queue names. `errors.py` defines expected app errors, such as "not found" or "this requested action is not legal in the current app state", and FastAPI converts those errors into clean HTTP responses. `metrics.py` tracks how many operations happened, how long they took, and how many cars are available or rented.

The most complex helper is `track_operation`. It wraps service functions, measures how long they take, counts how many times they run, and exposes the results through `/metrics`. This is useful because a real system should not only work; it should also be observable.

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

    Input -->|"service receives clean schema object"| Repo
    Repo -->|"repository inserts car into MongoDB"| Metrics
    Metrics -->|"system counters are recalculated"| Event
    Event -->|"publisher sends car.created to RabbitMQ"| Output
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

    Request -->|"frontend sends car_id, customer_name, start_date"| LoadCar
    LoadCar -->|"service loads requested car from repository"| CheckStatus
    CheckStatus -->|No| Reject["409 Conflict"]
    CheckStatus -->|Yes| CheckActive
    CheckActive -->|Yes| Reject
    CheckActive -->|No| CreateRental
    CreateRental -->|"repository saves rental document"| UpdateCar
    UpdateCar -->|"car becomes rented"| Metrics
    Metrics -->|"available/rented/open-rental counts refresh"| Queue
    Queue -->|"rental.started event is published"| Response
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

    Service -->|"after legal app action succeeds, create event"| EventFactory
    EventFactory -->|"builds FleetEvent JSON shape"| Publisher
    Publisher -->|"sends persistent message"| Exchange
    Exchange -->|"routes by routing key fleet.event"| Queue
    Queue -->|"holds message until worker consumes it"| Consumer
    Consumer -->|"parses message body into FleetEvent"| Worker
    Worker -->|"asks repository to audit the event"| EventRepo
    EventRepo -->|"upserts event by event_id"| Mongo
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

    API -->|"must finish before response"| Work1
    Work1 -->|"must finish before response"| Work2
    Work2 -->|"must finish before response"| Work3
    Work3 -->|"only then user gets answer"| Response
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

    API -->|"does required database change"| Work1
    Work1 -->|"publishes small event message"| Publish
    Publish -->|"user gets response quickly"| Response
    Publish -->|"background work moves to queue"| Queue
    Queue -->|"worker handles it later"| Worker
```

The user waits only for the important main operation. The worker can process background work separately.

Benefits:

- Better performance: the API can return faster because background work is moved out of the request path.
- Better reliability: if the worker is temporarily down, RabbitMQ can keep messages until the worker returns.
- Better scalability: more workers can be added if there are many events.
- Better separation: the API focuses on business commands, the worker focuses on asynchronous processing.
- Better future growth: the same queue can later support emails, reports, notifications, billing, and external integrations.


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

    Main -->|"mounts React root"| App
    App -->|"renders the main screen"| Dashboard
    Dashboard -->|"calls typed API functions"| API
    API -->|"uses shared fetch wrapper"| HTTP
    Dashboard -->|"passes car data and callbacks"| CarFeature
    Dashboard -->|"passes rental data and callbacks"| RentalFeature
    Dashboard -->|"uses reusable visual pieces"| Components
    Dashboard -->|"uses shared TypeScript shapes"| Types
    Dashboard -->|"uses date and label helpers"| Utils
    App -->|"loads global app styling"| Styles
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
    API -->|"connects using mongodb://mongo:27017"| Mongo
    API -->|"publishes events using amqp://rabbitmq:5672"| Rabbit
    Rabbit -->|"delivers queued events to"| Worker
    Worker -->|"stores consumed event documents in"| Mongo
    Mongo -->|"persists database files in"| VolData
    API -->|"writes app logs to"| VolLogs
    Worker -->|"writes worker logs to"| VolLogs
    Rabbit -->|"persists queue broker data in"| VolRabbit
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

    Node -->|"installs dependencies and compiles React"| Build
    Build -->|"outputs static production files"| Dist
    Dist -->|"copies files into runtime image"| Nginx
    Nginx -->|"serves index.html and assets"| Serve
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
| `api` | root `Dockerfile` | `mongo`, `rabbitmq` | Handles REST API, app logic checks, metrics, and event publishing. |
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
Download the project from Git, open the main folder and type:
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
  -Body '{"car_id":"CAR_ID_HERE","customer_name":"Dana Levi","start_date":"2026-05-26","planned_end_date":"2026-05-28"}'
```

### End A Rental

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/rentals/RENTAL_ID_HERE/end?end_date=2026-05-26"
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

## 14. File And Function Guide

This section is a compact map of the project files. It is meant to help a reader understand where every important responsibility lives without reading every line of code first.

### Backend Files

| File | Main classes / functions | What it does |
|---|---|---|
| `backend/app/main.py` | `create_app` | Creates the FastAPI app, connects MongoDB and RabbitMQ during startup, registers routers, and converts expected app errors into clean HTTP responses. |
| `backend/app/api/dependencies.py` | `get_event_publisher`, `get_fleet_service` | Builds the service layer dependencies for route functions. It connects routes to repositories and the RabbitMQ publisher. |
| `backend/app/api/routes/cars.py` | `add_car`, `list_cars`, `update_car`, `delete_car` | Defines HTTP endpoints for car management and passes validated data to `FleetService`. |
| `backend/app/api/routes/rentals.py` | `start_rental`, `list_rentals`, `update_rental`, `end_rental` | Defines rental endpoints for scheduling rentals, editing planned return dates, listing rentals, and ending current rentals. |
| `backend/app/api/routes/events.py` | `list_events` | Returns the stored queue/audit events that the worker consumed from RabbitMQ. |
| `backend/app/api/routes/system.py` | `health`, `metrics`, `operation_statistics`, `logs` | Provides health checks, raw Prometheus metrics, UI-friendly operation statistics, and the current log file. |
| `backend/app/core/config.py` | `AppSettings`, `get_settings` | Loads environment variables such as MongoDB URL, RabbitMQ URL, queue names, and log-file location. |
| `backend/app/core/errors.py` | `ApplicationError`, `NotFoundError`, `BusinessRuleError` | Defines expected application errors so the API can return readable `404` and `409` responses. |
| `backend/app/core/logging.py` | `configure_logging` | Sends logs to both the console and the configured log file. |
| `backend/app/core/metrics.py` | `track_operation`, `refresh_metrics`, `metrics_response`, `operation_statistics_snapshot` | Counts backend operations, measures operation duration, updates fleet gauges, exposes raw metrics, and builds the UI statistics summary. |
| `backend/app/db/mongodb.py` | `MongoDatabase`, `connect_to_mongodb`, `close_mongodb_connection`, `get_database` | Owns the MongoDB connection lifecycle and gives repositories the active database object. |
| `backend/app/db/indexes.py` | `ensure_database_indexes` | Creates MongoDB indexes used for faster car, rental, and event queries. |
| `backend/app/db/object_ids.py` | `parse_object_id` | Safely converts string ids from API routes into MongoDB `ObjectId` values. |
| `backend/app/messaging/events.py` | `FleetEvent`, `car_event`, `rental_event` | Defines the event shape sent through RabbitMQ and helper functions for car/rental events. |
| `backend/app/messaging/publisher.py` | `EventPublisher`, `NoOpEventPublisher`, `RabbitMQEventPublisher` | Publishes events to RabbitMQ, while allowing tests to run without a real queue. |
| `backend/app/messaging/consumer.py` | `RabbitMQEventConsumer` | Reads events from RabbitMQ and hands them to a callback for processing. |
| `backend/app/workers/event_worker.py` | `run_worker`, `main` | Runs the background worker process that consumes queue events and stores them in MongoDB. |
| `backend/app/models/documents.py` | `CarDocument`, `RentalDocument` | Defines the internal typed records returned from repositories after reading MongoDB. |
| `backend/app/models/enums.py` | `VehicleStatus` | Keeps vehicle status values consistent: `available`, `rented`, and `maintenance`. |
| `backend/app/schemas/cars.py` | `CarCreate`, `CarUpdate`, `CarRead` | Defines the request and response shapes for car API data. |
| `backend/app/schemas/rentals.py` | `RentalCreate`, `RentalUpdate`, `RentalRead` | Defines the request and response shapes for rental scheduling and rental updates. |
| `backend/app/schemas/events.py` | `FleetEventRead` | Defines the API response shape for consumed queue events. |
| `backend/app/repositories/cars.py` | `MongoCarRepository` | Reads, creates, updates, deletes, and counts cars in MongoDB. |
| `backend/app/repositories/rentals.py` | `MongoRentalRepository` | Stores rental records, finds current rentals, detects date-range conflicts, and closes rentals. |
| `backend/app/repositories/events.py` | `MongoEventRepository` | Stores consumed RabbitMQ events and lists recent event records for auditing. |
| `backend/app/services/fleet_service.py` | `FleetService`, `CarRepository`, `RentalRepository` | Contains the main app logic: legal action checks, scheduled rental conflict rules, status updates, metrics refresh, and queue publishing. |

### Frontend Files

| File | Main components / functions | What it does |
|---|---|---|
| `frontend/src/main.tsx` | React render setup | Starts the React app and mounts it into the browser page. |
| `frontend/src/App.tsx` | `App` | Loads the main dashboard component. |
| `frontend/src/pages/DashboardPage.tsx` | `DashboardPage`, action handlers | Owns dashboard state, loads cars/rentals/statistics, calls API functions, and connects all forms and tables together. |
| `frontend/src/api/http.ts` | `ApiError`, `request` | Provides one typed fetch wrapper with JSON parsing and consistent error messages. |
| `frontend/src/api/fleetApi.ts` | `listCars`, `createCar`, `updateCar`, `deleteCar`, `listRentals`, `createRental`, `updateRental`, `endRental`, `getOperationStatistics` | Contains all frontend-to-backend API calls used by React components. |
| `frontend/src/types/fleet.ts` | TypeScript types | Defines the frontend data contracts for cars, rentals, request payloads, and operation statistics. |
| `frontend/src/components/AppHeader.tsx` | `AppHeader` | Shows the title, refresh button, logs button, and statistics navigation button. |
| `frontend/src/components/SummaryTile.tsx` | `SummaryTile` | Displays one dashboard number such as total cars or open rentals. |
| `frontend/src/components/StatusBadge.tsx` | `StatusBadge` | Shows a styled label for each car status. |
| `frontend/src/features/cars/CarForm.tsx` | `CarForm` | Lets the user create a new car with model, year, and status. |
| `frontend/src/features/cars/CarsTable.tsx` | `CarsTable` | Shows all cars, their current status, current rental information, and action buttons. |
| `frontend/src/features/rentals/RentalForm.tsx` | `RentalForm` | Lets the user schedule a rental with planned start and planned return dates. |
| `frontend/src/features/rentals/RentalsTable.tsx` | `RentalsTable` | Shows rentals, scheduled/current/closed state, editable planned return dates, and the `End now` action when legal. |
| `frontend/src/features/observability/OperationStatisticsPanel.tsx` | `OperationStatisticsPanel`, `formatMilliseconds` | Shows average request/operation time per backend operation and the average across all operations together. |
| `frontend/src/utils/dates.ts` | `todayIsoDate` | Returns today as `YYYY-MM-DD` for HTML date inputs and API payloads. |
| `frontend/src/utils/labels.ts` | `carDisplayName` | Builds a readable car label from model, year, and status. |
| `frontend/src/styles/global.css` | CSS rules | Defines the layout, tables, forms, buttons, badges, responsive behavior, and statistics panel styling. |

### Configuration And Docker Files

| File | What it does |
|---|---|
| `Dockerfile` | Builds the FastAPI backend and worker image from the Python project. |
| `docker-compose.yml` | Runs the full system: React frontend, FastAPI API, worker, MongoDB, and RabbitMQ. |
| `.dockerignore` | Keeps unnecessary files out of Docker build context so builds stay smaller and cleaner. |
| `.env.example` | Documents environment variables that can configure the backend locally. |
| `pyproject.toml` | Defines the Python package metadata, dependencies, and pytest configuration. |
| `frontend/Dockerfile` | Builds the React production assets and serves them with Nginx. |
| `frontend/nginx.conf` | Serves the React app and proxies `/api`, `/metrics`, and other backend paths to the API container. |
| `frontend/package.json` | Defines frontend scripts and dependencies such as React, Vite, TypeScript, and lucide icons. |
| `frontend/package-lock.json` | Locks exact frontend dependency versions for reproducible installs. |
| `frontend/vite.config.ts` | Configures the Vite dev server and backend API proxy during local frontend development. |
| `frontend/tsconfig.json` and `frontend/tsconfig.node.json` | Configure TypeScript rules for browser code and Vite/node tooling. |
| `API.md`, `ARCHITECTURE.md`, `DEVELOPMENT.md`, `DOCUMENTATION.md`, `docs/system-design.md` | Extra documentation files that explain API usage, architecture, development workflow, and system design notes. |

Generated folders such as `.venv`, `node_modules`, `dist`, `.pytest_cache`, and `rental_fleet_manager.egg-info` are not part of the source design. They are created by Python, Node, pytest, or build commands.

### Test Files

| File | Main tests / helpers | What it does |
|---|---|---|
| `tests/backend/conftest.py` | `InMemoryCarRepository`, `InMemoryRentalRepository`, `fleet_service`, `client` | Provides test doubles and fixtures so service/API tests can run without a real MongoDB server. |
| `tests/backend/test_fleet_service.py` | service unit tests | Tests the app logic directly: car creation, queue event publishing, rental scheduling, date conflict prevention, past-date rejection, and status changes. |
| `tests/backend/test_api.py` | API tests | Tests real FastAPI routes using `TestClient`, including car/rental flow, conflict responses, metrics, logs, and operation statistics. |
| `tests/backend/test_mongo_repositories.py` | repository unit test | Tests that the car repository correctly awaits MongoDB aggregation and returns status counts. |

## 15. Testing Guide

The project has more than four working tests. At the time of this README update, the backend test suite contains 20 passing tests. These tests are important because they prove the main app logic works without needing to manually click through the UI every time.

Run all backend tests:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental
.\.venv\Scripts\python.exe -m pytest
```

Current passing output:

```text
....................                                                     [100%]
20 passed in 0.97s
```

### Important Unit Tests

| Test | File | What it proves |
|---|---|---|
| `test_add_and_list_cars` | `tests/backend/test_fleet_service.py` | Proves `FleetService.add_car` creates a car and `FleetService.list_cars` returns it. This is a basic unit test for the service layer without using the real database. |
| `test_add_car_publishes_queue_event` | `tests/backend/test_fleet_service.py` | Proves that when a car is added, the service publishes a `car.created` event. This checks the message-queue integration point without needing RabbitMQ in the unit test. |
| `test_future_rentals_keep_car_available_and_reject_only_overlaps` | `tests/backend/test_fleet_service.py` | Proves future rentals do not immediately change a car to `rented`, and also proves overlapping rental dates for the same car are rejected. |
| `test_rejects_past_rental_dates` | `tests/backend/test_fleet_service.py` | Proves the service rejects rental schedules that start in the past or return in the past. This protects the backend even if the UI is bypassed. |
| `test_update_rental_planned_end_date` | `tests/backend/test_fleet_service.py` | Proves an open rental can have its planned return date edited when the new date is legal. |
| `test_end_rental_marks_car_available` | `tests/backend/test_fleet_service.py` | Proves ending a current rental closes the rental and returns the car to `available` when no other current rental exists. |

### Important API Tests

| Test | File | What it proves |
|---|---|---|
| `test_car_and_rental_flow_over_api` | `tests/backend/test_api.py` | Proves the real FastAPI endpoints can create a car, schedule a rental, update the planned return date, end the rental, and return the car to `available`. |
| `test_rejects_second_active_rental_for_same_car` | `tests/backend/test_api.py` | Proves the API returns `409 Conflict` when another rental overlaps the same car's date range. |
| `test_future_rentals_do_not_make_car_rented_now` | `tests/backend/test_api.py` | Proves future reservations can be created without making the car unavailable today. |
| `test_operation_statistics_endpoint_is_available` | `tests/backend/test_api.py` | Proves `/api/operation-statistics` returns the timing data used by the statistics UI. |
| `test_logs_endpoint_is_available` | `tests/backend/test_api.py` | Proves `/api/logs` returns plain text so the UI's `Logs` button has a real backend endpoint. |

### Repository Test

| Test | File | What it proves |
|---|---|---|
| `test_count_by_status_awaits_async_mongo_aggregate` | `tests/backend/test_mongo_repositories.py` | Proves the Mongo car repository handles async MongoDB aggregation correctly when counting cars by status. |

### Frontend Build Check

Run this to verify the React code compiles:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental\frontend
npm.cmd run build
```

Expected successful result:

```text
built successfully
```

## Final Architecture Summary

This project uses React for the user interface, FastAPI for backend API and app logic checks, MongoDB for NoSQL document storage, RabbitMQ for asynchronous queue-based communication, and Docker Compose to run all services together.

The most important design decision is separation of responsibilities. The frontend only handles UI and API calls. The API layer handles HTTP. The service layer checks whether requested app actions are legal. The repository layer handles MongoDB. The messaging layer handles RabbitMQ. The worker handles asynchronous processing. Docker Compose connects all services into one runnable system.
