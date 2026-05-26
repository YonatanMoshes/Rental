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
- [14. Testing Guide](#14-testing-guide)

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

The message queue flow happens after important fleet changes. For example, after a car is created, FastAPI publishes a `car.created` event to RabbitMQ and then the user-facing request can finish. The worker consumes that event later and handles the side jobs: it stores the event in the `fleet_events` MongoDB collection, writes the processed-event log line, and refreshes fleet gauge metrics. This proves the system is using queue-based communication and keeps slower observability work outside the main request path.

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
    Service -->|"records operation duration through decorators"| Core
    Worker -->|"writes action logs and refreshes fleet gauges"| Core
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

The service layer receives clean Python objects from the route layer, such as `CarCreate` or `RentalCreate`. Then it asks repositories for the current data it needs. If the request is legal, it tells repositories to save or update the required records. After the main data change succeeds, it publishes a RabbitMQ event and returns the result back to the route layer. Normal action logging and fleet gauge refreshes are handled by the worker after it consumes the event, so those side jobs do not slow down the HTTP response.

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
    Queue["RabbitMQ car.created"]
    Output["CarDocument"]

    Input -->|"service receives clean schema object"| Repo
    Repo -->|"repository inserts car into MongoDB"| Queue
    Queue -->|"publisher sends event and service returns created car"| Output
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
    Queue["Publish rental.started"]
    Response["Return rental"]

    Request -->|"frontend sends car_id, customer_name, start_date"| LoadCar
    LoadCar -->|"service loads requested car from repository"| CheckStatus
    CheckStatus -->|No| Reject["409 Conflict"]
    CheckStatus -->|Yes| CheckActive
    CheckActive -->|Yes| Reject
    CheckActive -->|No| CreateRental
    CreateRental -->|"repository saves rental document"| UpdateCar
    UpdateCar -->|"car becomes rented only if rental covers today"| Queue
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
7. Publish `rental.ended`.
8. The worker later logs the event, stores the event audit record, and refreshes fleet metrics.

## 5. Message Queue Architecture

The message queue requirement is implemented with RabbitMQ, and it is now used for the important architectural reason: it separates the immediate user request from the slower side work that does not need to block the user. The browser still communicates with the backend through HTTP because a user needs an immediate success or error response when adding a car, editing a car, scheduling a rental, or ending a rental. RabbitMQ is used after the main action succeeds, so the API can publish a small event and let a separate worker process handle the follow-up observability work.

In the current design, the API service focuses on the main legal action. For example, when a user creates a car, the API validates the request, checks the app logic, writes the car to MongoDB, publishes a `car.created` event, and returns the created car to the frontend. The API does not wait for the event audit write, the action log line, or the fleet gauge refresh to finish inside the same request. Those tasks are handled by the worker after it receives the message from RabbitMQ. This makes the request path smaller and faster because the main thread is responsible only for the work the user is directly waiting for.

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
    EventProcessor["process_fleet_event"]
    EventRepo["MongoEventRepository"]
    Metrics["refresh_metrics"]
    Logger["worker logger"]
    Mongo["MongoDB fleet_events"]
    Prometheus["Prometheus gauges"]
    LogFile["logs/rental_fleet.log"]

    Service -->|"after legal app action succeeds, create event"| EventFactory
    EventFactory -->|"builds FleetEvent JSON shape"| Publisher
    Publisher -->|"sends small persistent JSON message"| Exchange
    Exchange -->|"routes by routing key fleet.event"| Queue
    Queue -->|"stores message until a worker is ready"| Consumer
    Consumer -->|"parses message body into FleetEvent"| EventProcessor
    Worker -->|"runs the consumer callback"| EventProcessor
    EventProcessor -->|"saves audit record"| EventRepo
    EventProcessor -->|"refreshes fleet gauge values"| Metrics
    EventProcessor -->|"writes processed event line"| Logger
    EventRepo -->|"upserts event by event_id"| Mongo
    Metrics -->|"updates available/rented/open rental counts"| Prometheus
    Logger -->|"writes timestamped line"| LogFile
```

The most important component is `process_fleet_event` in `backend/app/workers/event_worker.py`. This function is the worker's real unit of work. It receives one validated `FleetEvent`, saves it through `MongoEventRepository`, refreshes the fleet metrics by asking the car and rental repositories for current counts, and writes a clear worker log line. Because this function runs inside the worker container, the API request that created the event does not have to wait for those side jobs.

### Event Lifecycle

```mermaid
sequenceDiagram
    participant Service as FleetService
    participant Publisher as RabbitMQEventPublisher
    participant Rabbit as RabbitMQ
    participant Worker as Event Worker
    participant Repo as MongoEventRepository
    participant Metrics as Metrics Refresh
    participant Logs as Worker Log
    participant DB as MongoDB

    Service->>Publisher: publish(FleetEvent)
    Publisher->>Rabbit: send persistent message
    Rabbit-->>Publisher: accepted
    Publisher-->>Service: publish finished
    Service-->>Service: return HTTP response to user
    Rabbit-->>Worker: deliver message
    Worker->>Repo: save(event audit)
    Repo->>DB: upsert by event_id
    DB-->>Repo: saved
    Worker->>Metrics: refresh car and rental gauges
    Worker->>Logs: write processed-event log line
    Worker-->>Rabbit: ack message
```

The lifecycle is intentionally split into two parts. The first part is the user-facing request: the service publishes the event and returns the HTTP response. The second part is the background worker: RabbitMQ delivers the event, the worker processes the side jobs, and only then acknowledges the message. If the worker is temporarily unavailable, RabbitMQ keeps the message in the durable queue until the worker can consume it.

### What The API Publishes

The backend publishes these domain events:

| Event | When it is published | Payload |
|---|---|---|
| `car.created` | After a car is added | Car id, model, year, status |
| `car.updated` | After a car is updated | Updated car state |
| `car.deleted` | After a car is deleted | Deleted car data |
| `rental.started` | After a rental starts | Rental id, car id, customer, start date |
| `rental.plan_updated` | After a planned rental end date is edited | Updated rental state |
| `rental.ended` | After a rental ends | Rental id, car id, customer, start date, end date |

### Main Queue Function: `RabbitMQEventPublisher.publish`

Location:

```text
backend/app/messaging/publisher.py
```

`RabbitMQEventPublisher.publish` receives a `FleetEvent` object from the service layer after the main database change has succeeded. Its responsibility is to cross the process boundary from the API container to RabbitMQ. The function makes sure there is an active RabbitMQ connection, converts the event into JSON, wraps it in a persistent RabbitMQ message, and publishes it with the routing key `fleet.event`. RabbitMQ then stores the message in the durable queue named `rental.fleet.events.audit`.

This function is important because the API and worker are separate processes. The service layer cannot directly call a worker function, because the worker is running in another container and may even be scaled into multiple worker containers later. RabbitMQ is the professional bridge between them. The API only needs to successfully publish the message; the worker can consume it independently.

### Main Worker Functions

The worker side has two important functions:

```text
backend/app/messaging/consumer.py
backend/app/workers/event_worker.py
```

`RabbitMQEventConsumer._handle_message` receives the raw message from RabbitMQ. It opens RabbitMQ's message-processing context, validates the JSON body as a `FleetEvent`, and then calls the handler function that was provided by the worker. If the handler finishes successfully, RabbitMQ receives an acknowledgement and removes the message from the queue. If processing fails, the message can be requeued instead of silently disappearing.

`process_fleet_event` receives the already validated event and performs the actual post-request work. It saves the event for auditing, refreshes the current fleet metrics, and writes the worker log entry. This is the function that proves the queue is not just decorative. It has real responsibilities that used to be part of the heavier request path.

## 6. Why The Queue Improves The System

The queue improves the system because it lets the API return after the required user-facing work is done, while a separate worker handles side work in the background. A request such as "add car" has one critical responsibility: validate the input and store the car. Logging the processed event, saving an audit copy of the event, and refreshing fleet gauge metrics are useful and professional, but the user should not have to wait for every one of those tasks before seeing the new car on the screen.

Without this queue-based split, the request path would be longer:

```mermaid
flowchart LR
    API["API request"]
    Work1["Database write"]
    Work2["Save event audit row"]
    Work3["Refresh fleet metrics"]
    Work4["Write action log"]
    Response["Return response"]

    API -->|"must finish before response"| Work1
    Work1 -->|"must finish before response"| Work2
    Work2 -->|"must finish before response"| Work3
    Work3 -->|"must finish before response"| Work4
    Work4 -->|"only then user gets answer"| Response
```

In that design, the user waits for work that is not required to answer the request. The car may already be created, but the response is still delayed because the same thread is also doing audit, metrics, and logging work.

With the queue, the request path is shorter:

```mermaid
flowchart LR
    API["API request"]
    Work1["Database write"]
    Publish["Publish event"]
    Response["Return response"]
    Queue["RabbitMQ"]
    Worker["Worker handles extra tasks"]
    Audit["Save event audit row"]
    Metrics["Refresh fleet metrics"]
    Logs["Write action log"]

    API -->|"does required database change"| Work1
    Work1 -->|"publishes small event message"| Publish
    Publish -->|"user gets response quickly"| Response
    Publish -->|"background work moves to queue"| Queue
    Queue -->|"worker consumes event later"| Worker
    Worker -->|"stores event for audit"| Audit
    Worker -->|"updates fleet gauges"| Metrics
    Worker -->|"writes processed-event log"| Logs
```

The user now waits only for the important main operation and the small event publish. The worker can process background work separately, and this is why the system is faster from the user's point of view. It is not that logging or metrics disappeared. They moved to the correct process. The API thread is now cleaner: it handles creating cars, updating cars, scheduling rentals, ending rentals, and checking that those requests do not violate the app logic. The worker handles the side jobs that are important for monitoring and auditing but not required before returning the user response.

This design also improves reliability and scalability. If the worker is temporarily down, RabbitMQ can keep messages until the worker returns. If the system receives many events in the future, more worker containers can be added to process queue messages in parallel. The API can remain focused on commands, while the worker focuses on asynchronous processing. The same pattern could later support email notifications, reports, billing integration, or external analytics without making the main user request slower.


## 7. Frontend Architecture

The frontend is built with React, Vite, and TypeScript. React was chosen because it lets the UI be built from small components instead of one large page file. Each component owns one clear part of the screen: a form, a table, a header, a summary card, or an observability panel. This makes the frontend easier to understand, easier to test manually, and easier to extend later. For example, adding a new field to the car form does not require changing the rental table, and changing the way status badges look does not require touching the API client.

TypeScript makes the React code more professional because the frontend knows the shape of the data it expects from the backend. The `Car`, `Rental`, `CarCreatePayload`, and `RentalCreatePayload` types in `frontend/src/types/fleet.ts` act like a contract between the frontend and the FastAPI backend. If the frontend tries to send the wrong field name or use a missing property, TypeScript can catch that during the build instead of letting the error appear only in the browser.

The structure follows the same idea as SOLID principles. The most important principle here is single responsibility: each file has one main reason to change. API files change when backend endpoints change. Form components change when user input changes. Table components change when display or table actions change. Utility files change when shared date or label formatting changes. This is not a formal class-based SOLID design, but the same professional idea is used: keep responsibilities separated so the project can grow without becoming messy.

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

The frontend does not contain database logic, queue logic, or backend validation logic. It manages what the user sees, keeps temporary UI state such as loading and selected car values, and sends typed requests to the backend. The backend remains responsible for deciding whether a requested action is legal, because a user can bypass the UI and call the API directly. This separation keeps the frontend focused on user experience and keeps the backend responsible for protecting the app state.

## 8. Frontend Components

### Main Integration Component: `DashboardPage`

Location:

```text
frontend/src/pages/DashboardPage.tsx
```

`DashboardPage` is the integration component for the whole screen. It does not receive props from another page because this app has one main dashboard view. When the page opens, it calls the API client to load cars, rentals, and operation statistics. It stores the main frontend state: the array of cars, the array of rentals, the selected status filter, the selected car for scheduling, loading state, saving state, success messages, and error messages.

This component is responsible for connecting the smaller components together. It passes car data into `CarsTable`, rental data into `RentalsTable`, reservable cars into `RentalForm`, and action callbacks into the forms and tables. The child components do not know how to call the backend directly. They only say what the user wants to do, and `DashboardPage` decides which API function should run. This keeps the child components reusable and focused on UI.

The most important function in this component is `runAction`. Every user action has the same basic flow: clear old messages, mark the screen as saving, run the API call, reload the dashboard data, show a success message if it worked, or show the backend error message if it failed. Instead of duplicating that flow in every handler, `runAction` centralizes it. This follows the DRY idea and makes future changes safer, because the loading and error behavior can be improved in one place.

### `CarForm`

Location:

```text
frontend/src/features/cars/CarForm.tsx
```

`CarForm` is responsible only for collecting the information needed to create a car. It owns local input state for the model, year, and initial status. When the form is submitted, it creates a `CarCreatePayload` and passes that payload upward through the `onSubmit` callback. It does not import `fleetApi.ts`, and it does not know whether the backend uses MongoDB, SQL, or anything else. This keeps the component simple: its job is user input, not persistence.

This component shows why React components are useful. The form can clear itself after a successful submit, validate required fields through normal input attributes, and disable the button while a save is running. All of that UI behavior stays inside the form, while `DashboardPage` remains responsible for the actual API action.

### `CarsTable`

Location:

```text
frontend/src/features/cars/CarsTable.tsx
```

`CarsTable` is responsible for displaying the fleet and exposing car-related actions. It receives cars, rentals, the current status filter, and callback functions from `DashboardPage`. It filters the visible cars by status, finds the current active rental for each car when one exists, and renders the correct action buttons. For example, the `Rent` button appears only for available cars, and the maintenance toggle is hidden for cars that are currently rented.

The table does not directly change the backend. When the user clicks an action, the table calls a callback such as `onUpdateStatus`, `onDeleteCar`, or `onSelectForRental`. This keeps the component aligned with single responsibility: it displays cars and reports user intent, while the parent component decides how to execute that intent.

### `RentalForm`

Location:

```text
frontend/src/features/rentals/RentalForm.tsx
```

`RentalForm` is responsible for scheduling a new rental. It receives the cars that are allowed to be reserved, the currently selected car id, and the callbacks needed to change the selected car or submit the rental. It collects the customer name, planned start date, and planned return date. The date inputs prevent choosing past dates in the UI, and the backend repeats the same validation so the rule is protected even if someone bypasses the browser.

The selected-car logic is important because frontend state can become stale. A user may select a car, then another action may make that car unavailable or move it to maintenance. `RentalForm` watches the available car list and resets the selected id if the old id is no longer valid. This avoids sending a bad request when the UI already knows the selected car should not be used.

### `RentalsTable`

Location:

```text
frontend/src/features/rentals/RentalsTable.tsx
```

`RentalsTable` is responsible for displaying current, future, and closed rentals. It receives all cars and all rentals so it can turn a rental's `car_id` into a readable car name. It shows the customer, planned start date, planned return date, actual end date, and the correct action for the rental state.

Open rentals can have their planned return date edited from the table, and rentals that have already started can be ended immediately with the `End now` action. Future rentals are shown as scheduled instead of being treated as active rentals today. This distinction matters because a future reservation should block overlapping future reservations, but it should not make the car appear rented right now.

### Shared Components

| Component | Location | Purpose |
|---|---|---|
| `AppHeader` | `frontend/src/components/AppHeader.tsx` | Renders the title area, the Logs link, the Statistics link, and the Refresh button. It keeps these global navigation actions out of the dashboard body. |
| `StatusBadge` | `frontend/src/components/StatusBadge.tsx` | Converts backend status values into consistent visual labels. This avoids rewriting status styling in every table. |
| `SummaryTile` | `frontend/src/components/SummaryTile.tsx` | Displays dashboard totals such as total cars, available cars, maintenance cars, and open rentals in a reusable visual format. |
| `OperationStatisticsPanel` | `frontend/src/features/observability/OperationStatisticsPanel.tsx` | Shows average request/operation timing per backend operation and the overall average across all measured operations. |

These shared components make the frontend easier to maintain because repeated UI ideas live in one place. This is the React component model in practice: the app is built from small pieces, and each piece can be understood without reading the entire project.

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

Nginx is the web server inside the frontend container. The React build produces static files: `index.html`, JavaScript files, and CSS files. Nginx serves those files efficiently to the browser. This is why the final Docker image does not need to run the Vite development server or keep Node.js running in production mode.

Nginx also works as a reverse proxy for backend calls. The React code can call `/api/cars`, `/api/rentals`, `/api/logs`, or `/api/operation-statistics` as normal browser paths. Nginx receives those requests and forwards them to `http://api:8000`, where `api` is the Docker Compose service name for the FastAPI container. This is useful because the browser does not need to know Docker's internal network addresses. The browser only talks to `http://127.0.0.1:5173`, and Nginx quietly forwards backend requests inside the Docker network.

The `try_files $uri $uri/ /index.html;` line is also important for React. A React app is a single-page application, which means the browser loads `index.html` and React controls what appears on the screen. If a user refreshes a frontend route, Nginx should still return `index.html` so React can render the page. Without `try_files`, direct refreshes on frontend routes can become 404 errors.

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
| `api` | root `Dockerfile` | `mongo`, `rabbitmq` | Handles REST API, app logic checks, required database writes, operation timing, and event publishing. |
| `worker` | root `Dockerfile` | `mongo`, `rabbitmq` | Consumes queue events, stores event audits, writes processed-event logs, and refreshes fleet metrics. |
| `mongo` | `mongo:7` image | `api`, `worker` | Stores cars, rentals, and events. |
| `rabbitmq` | `rabbitmq:3-management` image | `api`, `worker` | Message queue between API and worker. |

Internal Docker networking:

- The API connects to MongoDB using `mongodb://mongo:27017`.
- The API connects to RabbitMQ using `amqp://guest:guest@rabbitmq:5672/`.
- The frontend Nginx proxy connects to the backend using `http://api:8000`.
- These names work because Docker Compose creates an internal network where services can reach each other by service name.

The API and worker containers also receive `LOG_TIMEZONE=Asia/Jerusalem` and `TZ=Asia/Jerusalem`. This matters because containers often default to UTC time. The backend logging formatter reads `LOG_TIMEZONE`, so log lines in `logs/rental_fleet.log` use the same local hour that you see on your computer in Israel time.

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
## 14. Testing Guide

The backend test suite currently contains 24 passing tests. These tests are important because they prove the main app logic works without needing to manually click through the UI every time. The tests are separated by responsibility in the same way as the backend code: service tests check the logic directly, API tests check the FastAPI routes, repository tests check MongoDB adapter behavior, worker tests check the RabbitMQ event-worker responsibilities, and logging tests check infrastructure behavior such as timestamp formatting.

To run the full backend test suite, open PowerShell in the project root and run:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental
.\.venv\Scripts\python.exe -m pytest
```

Current passing output looks like this:

```text
........................                                                 [100%]
24 passed
```

Running all tests is the normal command before committing because it proves the backend still works as one system. When you are working on one area, you can run only the related file or even one exact test. This is faster while developing and more professional than clicking randomly through the app.

### Service Unit Tests

The service tests are in `tests/backend/test_fleet_service.py`. They call `FleetService` directly with in-memory repositories, so they do not need Docker, MongoDB, or RabbitMQ. These are true unit tests for the app logic. They prove rules such as "a car in maintenance cannot be rented", "future reservations do not make the car rented today", "overlapping reservations are rejected", and "ending a current rental makes the car available again".

Run all service unit tests:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental
.\.venv\Scripts\python.exe -m pytest tests/backend/test_fleet_service.py
```

Run one exact service test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_fleet_service.py::test_future_rentals_keep_car_available_and_reject_only_overlaps
```

| Test | File | What it proves |
|---|---|---|
| `test_add_and_list_cars` | `tests/backend/test_fleet_service.py` | Proves `FleetService.add_car` creates a car and `FleetService.list_cars` returns it without using a real database. |
| `test_add_car_publishes_queue_event` | `tests/backend/test_fleet_service.py` | Proves that adding a car publishes a `car.created` event, which is the service-to-queue integration point. |
| `test_future_rentals_keep_car_available_and_reject_only_overlaps` | `tests/backend/test_fleet_service.py` | Proves a future reservation does not make the car rented today, while overlapping reservations for the same date range are rejected. |
| `test_rented_filter_returns_only_cars_rented_today` | `tests/backend/test_fleet_service.py` | Proves the service-level rented filter returns only cars that have a rental active today, not future reservations or closed rentals. |
| `test_rejects_past_rental_dates` | `tests/backend/test_fleet_service.py` | Proves the backend rejects planned start dates and planned return dates that are already in the past. |
| `test_update_rental_planned_end_date` | `tests/backend/test_fleet_service.py` | Proves an open rental can update its planned return date when the new date is legal. |
| `test_end_rental_marks_car_available` | `tests/backend/test_fleet_service.py` | Proves ending a current rental closes the rental and returns the car to `available` when no other current rental exists. |

### API Tests

The API tests are in `tests/backend/test_api.py`. They use FastAPI's `TestClient`, so they call the backend through HTTP routes instead of calling `FleetService` directly. This is useful because it proves the route layer, schema validation, dependency injection, service layer, and error handlers work together. These tests still use in-memory repositories, so they remain fast and do not require Docker.

Run all API tests:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental
.\.venv\Scripts\python.exe -m pytest tests/backend/test_api.py
```

Run one exact API test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_api.py::test_car_and_rental_flow_over_api
```

| Test | File | What it proves |
|---|---|---|
| `test_car_and_rental_flow_over_api` | `tests/backend/test_api.py` | Proves the real HTTP endpoints can create a car, schedule a rental, update the planned return date, end the rental, and return the car to `available`. |
| `test_rejects_second_active_rental_for_same_car` | `tests/backend/test_api.py` | Proves the API returns `409 Conflict` when another rental overlaps the same car's date range. |
| `test_future_rentals_do_not_make_car_rented_now` | `tests/backend/test_api.py` | Proves future reservations can be created without making the car unavailable today. |
| `test_rented_status_filter_returns_only_currently_rented_cars` | `tests/backend/test_api.py` | Proves `GET /api/cars?status=rented` returns only cars being rented today, excluding future and closed rentals. |
| `test_operation_statistics_endpoint_is_available` | `tests/backend/test_api.py` | Proves `/api/operation-statistics` returns the timing data used by the Statistics UI. |
| `test_logs_endpoint_is_available` | `tests/backend/test_api.py` | Proves `/api/logs` returns plain text so the UI's Logs button has a real backend endpoint. |

### Worker And Queue Tests

The worker test is in `tests/backend/test_event_worker.py`. It does not start a real RabbitMQ server. Instead, it tests the worker's event-processing function directly with fake repositories and a fake logger. This proves the worker is responsible for the post-request jobs: saving the consumed event, refreshing metrics, and logging the processed event.

Run the worker test:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental
.\.venv\Scripts\python.exe -m pytest tests/backend/test_event_worker.py
```

Run the exact worker test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_event_worker.py::test_worker_processes_event_logging_and_metrics
```

| Test | File | What it proves |
|---|---|---|
| `test_worker_processes_event_logging_and_metrics` | `tests/backend/test_event_worker.py` | Proves one queue event causes the worker to save the event, refresh fleet metrics, and write the processed-event log call. |

### Repository Tests

The repository test is in `tests/backend/test_mongo_repositories.py`. It uses fake MongoDB collection objects to check repository behavior without starting a real MongoDB server. This is useful because repository bugs can be caught quickly, while full Docker-based checks can be saved for final verification.

Run the repository test file:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental
.\.venv\Scripts\python.exe -m pytest tests/backend/test_mongo_repositories.py
```

Run the exact repository test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_mongo_repositories.py::test_count_by_status_awaits_async_mongo_aggregate
```

| Test | File | What it proves |
|---|---|---|
| `test_count_by_status_awaits_async_mongo_aggregate` | `tests/backend/test_mongo_repositories.py` | Proves the Mongo car repository correctly awaits MongoDB aggregation before reading car status counts for metrics. |

### Logging Test

The logging test is in `tests/backend/test_logging.py`. It checks the timezone formatter directly. This matters because Docker containers often use UTC time by default, but the project should show log timestamps in Israel time when `LOG_TIMEZONE=Asia/Jerusalem` is configured.

Run the logging test file:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental
.\.venv\Scripts\python.exe -m pytest tests/backend/test_logging.py
```

Run the exact logging test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_logging.py::test_timezone_formatter_uses_configured_timezone
```

| Test | File | What it proves |
|---|---|---|
| `test_timezone_formatter_uses_configured_timezone` | `tests/backend/test_logging.py` | Proves a UTC log record from `14:06` is rendered as `17:06` when the configured timezone is `Asia/Jerusalem`. |

### Frontend Build Check

The frontend check is not a pytest test. It is a TypeScript and Vite build check. It proves that the React code compiles, the TypeScript types are valid, and the production frontend bundle can be generated.

Run this command:

```powershell
cd C:\Users\User\OneDrive\Desktop\Rental\frontend
npm.cmd run build
```

Expected successful result includes Vite's build success line:

```text
built
```

## Final Architecture Summary

This project uses React for the user interface, FastAPI for backend API and app logic checks, MongoDB for NoSQL document storage, RabbitMQ for asynchronous queue-based communication, and Docker Compose to run all services together.

The most important design decision is separation of responsibilities. The frontend only handles UI and API calls. The API layer handles HTTP. The service layer checks whether requested app actions are legal. The repository layer handles MongoDB. The messaging layer handles RabbitMQ. The worker handles asynchronous processing. Docker Compose connects all services into one runnable system.
