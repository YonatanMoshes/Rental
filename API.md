# API Reference

Complete documentation of all REST API endpoints for the Rental Fleet Manager.

## Base URL

- **Development**: `http://127.0.0.1:8000`
- **Docker**: `http://localhost:8000`
- **API Docs (Swagger UI)**: `http://127.0.0.1:8000/docs`
- **API Docs (ReDoc)**: `http://127.0.0.1:8000/redoc`

## Authentication

Currently, the API has no authentication. All endpoints are publicly accessible.

> **Security Note**: For production, implement JWT or OAuth2 authentication.

## Response Format

All successful responses return JSON with appropriate HTTP status codes:

```json
{
  "id": "507f1f77bcf86cd799439011",
  "model": "Toyota Corolla",
  "year": 2021,
  "status": "available"
}
```

Error responses:

```json
{
  "detail": "Car not found"
}
```

## Status Codes

- `200 OK` - Successful GET, PATCH
- `201 Created` - Successful POST (resource created)
- `204 No Content` - Successful DELETE (no body)
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Business rule violation
- `500 Internal Server Error` - Unexpected server error

---

## Endpoints

### Cars

#### List Cars

**Endpoint**: `GET /api/cars`

**Description**: Get all cars, optionally filtered by status.

**Query Parameters**:
- `status` (optional): Filter by status - `available`, `rented`, or `maintenance`

**Example Requests**:
```bash
# All cars
curl http://127.0.0.1:8000/api/cars

# Only available cars
curl "http://127.0.0.1:8000/api/cars?status=available"

# Only rented cars
curl "http://127.0.0.1:8000/api/cars?status=rented"
```

**Response** (200 OK):
```json
[
  {
    "id": "507f1f77bcf86cd799439011",
    "model": "Toyota Corolla",
    "year": 2021,
    "status": "available"
  },
  {
    "id": "507f1f77bcf86cd799439012",
    "model": "Honda Civic",
    "year": 2022,
    "status": "rented"
  }
]
```

---

#### Create Car

**Endpoint**: `POST /api/cars`

**Description**: Add a new car to the fleet.

**Request Body**:
```json
{
  "model": "Toyota Corolla",
  "year": 2021,
  "status": "available"
}
```

**Field Validation**:
- `model`: 1-120 characters (required)
- `year`: 1886-2100 (required)
- `status`: `"available"` (default), `"maintenance"` (optional)

**Example Request**:
```bash
curl -X POST http://127.0.0.1:8000/api/cars \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Tesla Model 3",
    "year": 2024,
    "status": "available"
  }'
```

**Response** (201 Created):
```json
{
  "id": "507f1f77bcf86cd799439013",
  "model": "Tesla Model 3",
  "year": 2024,
  "status": "available"
}
```

**Errors**:
- `400 Bad Request` - Invalid model length or year out of range
- `422 Unprocessable Entity` - Missing required fields

---

#### Update Car

**Endpoint**: `PATCH /api/cars/{car_id}`

**Description**: Update car details (model, year, status). Only provided fields are updated.

**Path Parameters**:
- `car_id`: Car ID (string, required)

**Request Body** (all optional):
```json
{
  "model": "Updated Model",
  "year": 2023,
  "status": "maintenance"
}
```

**Business Rules**:
- Cannot change status away from `"rented"` while a rental is active
- Cannot set status to `"rented"` directly (use rental flow instead)

**Example Request**:
```bash
curl -X PATCH http://127.0.0.1:8000/api/cars/507f1f77bcf86cd799439011 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "maintenance"
  }'
```

**Response** (200 OK):
```json
{
  "id": "507f1f77bcf86cd799439011",
  "model": "Toyota Corolla",
  "year": 2021,
  "status": "maintenance"
}
```

**Errors**:
- `404 Not Found` - Car doesn't exist
- `409 Conflict` - Business rule violated (active rental, can't mark rented, etc.)

---

#### Delete Car

**Endpoint**: `DELETE /api/cars/{car_id}`

**Description**: Remove a car from the fleet.

**Path Parameters**:
- `car_id`: Car ID (string, required)

**Business Rules**:
- Cannot delete a car with an active rental

**Example Request**:
```bash
curl -X DELETE http://127.0.0.1:8000/api/cars/507f1f77bcf86cd799439011
```

**Response** (204 No Content):
```
(empty body)
```

**Errors**:
- `404 Not Found` - Car doesn't exist
- `409 Conflict` - Car has an active rental

---

### Rentals

#### List Rentals

**Endpoint**: `GET /api/rentals`

**Description**: Get all rentals, optionally filtered by status.

**Query Parameters**:
- `open_only` (optional): Filter by status
  - `true` - Only active rentals (end_date is null)
  - `false` - Only completed rentals (end_date is set)
  - Omit - All rentals

**Example Requests**:
```bash
# All rentals
curl http://127.0.0.1:8000/api/rentals

# Only active (open) rentals
curl "http://127.0.0.1:8000/api/rentals?open_only=true"

# Only completed rentals
curl "http://127.0.0.1:8000/api/rentals?open_only=false"
```

**Response** (200 OK):
```json
[
  {
    "id": "507f1f77bcf86cd799439020",
    "car_id": "507f1f77bcf86cd799439011",
    "customer_name": "Dana Levi",
    "start_date": "2024-05-20",
    "end_date": null
  },
  {
    "id": "507f1f77bcf86cd799439021",
    "car_id": "507f1f77bcf86cd799439012",
    "customer_name": "Jane Smith",
    "start_date": "2024-05-15",
    "end_date": "2024-05-18"
  }
]
```

---

#### Start Rental

**Endpoint**: `POST /api/rentals`

**Description**: Start a new rental for a customer. Automatically marks the car as `"rented"`.

**Request Body**:
```json
{
  "car_id": "507f1f77bcf86cd799439011",
  "customer_name": "Dana Levi",
  "start_date": "2024-05-20"
}
```

**Field Validation**:
- `car_id`: Valid MongoDB ObjectId (required)
- `customer_name`: 1-120 characters (required)
- `start_date`: ISO 8601 date (required, defaults to today)

**Business Rules**:
- Car must exist and be in `"available"` status
- Car cannot have an active rental already

**Example Request**:
```bash
curl -X POST http://127.0.0.1:8000/api/rentals \
  -H "Content-Type: application/json" \
  -d '{
    "car_id": "507f1f77bcf86cd799439011",
    "customer_name": "John Doe",
    "start_date": "2024-05-25"
  }'
```

**Response** (201 Created):
```json
{
  "id": "507f1f77bcf86cd799439022",
  "car_id": "507f1f77bcf86cd799439011",
  "customer_name": "John Doe",
  "start_date": "2024-05-25",
  "end_date": null
}
```

**Errors**:
- `404 Not Found` - Car doesn't exist
- `409 Conflict` - Car not available or already has active rental

---

#### End Rental

**Endpoint**: `POST /api/rentals/{rental_id}/end`

**Description**: Mark a rental as ended. Automatically returns the car to `"available"` status.

**Path Parameters**:
- `rental_id`: Rental ID (string, required)

**Query Parameters**:
- `end_date` (optional): ISO 8601 date for rental end. Defaults to today if omitted.

**Example Requests**:
```bash
# End rental with today's date
curl -X POST http://127.0.0.1:8000/api/rentals/507f1f77bcf86cd799439020/end

# End rental with specific date
curl -X POST "http://127.0.0.1:8000/api/rentals/507f1f77bcf86cd799439020/end?end_date=2024-05-25"
```

**Response** (200 OK):
```json
{
  "id": "507f1f77bcf86cd799439020",
  "car_id": "507f1f77bcf86cd799439011",
  "customer_name": "Dana Levi",
  "start_date": "2024-05-20",
  "end_date": "2024-05-25"
}
```

**Errors**:
- `404 Not Found` - Rental doesn't exist

---

### System

#### Health Check

**Endpoint**: `GET /health`

**Description**: Check if the API is running. Used for monitoring and load balancers.

**Response** (200 OK):
```json
{
  "status": "ok"
}
```

---

#### Metrics

**Endpoint**: `GET /metrics`

**Description**: Prometheus-compatible metrics endpoint for monitoring.

**Format**: Plaintext (Prometheus format)

**Metrics Exported**:
- `rental_fleet_operations_total` - Total operations by type
- `rental_fleet_operation_duration_seconds` - Operation latency histogram
- `rental_fleet_available_cars` - Current available car count
- `rental_fleet_rented_cars` - Current rented car count
- `rental_fleet_open_rentals` - Active rental count

**Example Response**:
```
# HELP rental_fleet_operations_total Total number of backend operations.
# TYPE rental_fleet_operations_total counter
rental_fleet_operations_total{operation="add_car"} 5.0
rental_fleet_operations_total{operation="list_cars"} 12.0
rental_fleet_operations_total{operation="start_rental"} 3.0
# ...
```

---

## Error Handling

### Common Errors

**400 Bad Request** - Invalid input:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "model"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    }
  ]
}
```

**404 Not Found**:
```json
{
  "detail": "Car 507f1f77bcf86cd799439099 was not found."
}
```

**409 Conflict** - Business rule violation:
```json
{
  "detail": "Cannot delete a car with an active rental."
}
```

---

## Code Examples

### JavaScript/Fetch

```javascript
// List all available cars
const response = await fetch('/api/cars?status=available');
const cars = await response.json();

// Create a car
const carResponse = await fetch('/api/cars', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'Toyota Corolla',
    year: 2021,
    status: 'available'
  })
});
const newCar = await carResponse.json();

// Start a rental
const rentalResponse = await fetch('/api/rentals', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    car_id: newCar.id,
    customer_name: 'Jane Smith',
    start_date: '2024-05-25'
  })
});
const rental = await rentalResponse.json();
```

### Python/Requests

```python
import requests

BASE_URL = 'http://127.0.0.1:8000'

# List cars
response = requests.get(f'{BASE_URL}/api/cars?status=available')
cars = response.json()

# Create car
new_car = requests.post(
    f'{BASE_URL}/api/cars',
    json={
        'model': 'Tesla Model 3',
        'year': 2024,
        'status': 'available'
    }
).json()

# Start rental
rental = requests.post(
    f'{BASE_URL}/api/rentals',
    json={
        'car_id': new_car['id'],
        'customer_name': 'John Doe',
        'start_date': '2024-05-25'
    }
).json()

# End rental
ended_rental = requests.post(
    f'{BASE_URL}/api/rentals/{rental["id"]}/end?end_date=2024-05-30'
).json()
```

### cURL

```bash
# List available cars
curl 'http://127.0.0.1:8000/api/cars?status=available'

# Create car
curl -X POST http://127.0.0.1:8000/api/cars \
  -H 'Content-Type: application/json' \
  -d '{"model":"Honda Civic","year":2022,"status":"available"}'

# Start rental
curl -X POST http://127.0.0.1:8000/api/rentals \
  -H 'Content-Type: application/json' \
  -d '{"car_id":"507f1f77bcf86cd799439011","customer_name":"Alice","start_date":"2024-05-25"}'

# Health check
curl http://127.0.0.1:8000/health

# Metrics
curl http://127.0.0.1:8000/metrics
```

---

## Rate Limiting

Currently no rate limiting is implemented. For production, consider:
- Implementing per-IP rate limits
- Using API keys for throttling
- Setting up WAF rules

---

## CORS

CORS is not explicitly configured. To enable cross-origin requests from a specific domain:

1. Update `backend/app/main.py` to add CORS middleware
2. Specify allowed origins, methods, headers
3. Example:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

---

## Version

- **API Version**: 0.1.0
- **Python**: 3.11+
- **FastAPI**: 0.111+
