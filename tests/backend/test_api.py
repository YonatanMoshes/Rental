"""API-level tests for the FastAPI routes.

These tests call the application through HTTP using TestClient. They prove that
routes, schemas, dependency injection, service logic, and error handling work
together as one backend API.
"""

from datetime import date, timedelta


def test_car_and_rental_flow_over_api(client):
    """Create a car, schedule a rental, edit it, close it, and verify status."""
    today = date.today()
    planned_end = today + timedelta(days=2)
    car_response = client.post("/api/cars", json={"model": "Toyota Corolla", "year": 2024})
    car_id = car_response.json()["id"]

    rental_response = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Dana Levi",
            "start_date": today.isoformat(),
            "planned_end_date": planned_end.isoformat(),
        },
    )
    rental_id = rental_response.json()["id"]

    assert car_response.status_code == 201
    assert rental_response.status_code == 201
    assert rental_response.json()["planned_end_date"] == planned_end.isoformat()
    assert client.get("/api/cars").json()[0]["status"] == "rented"

    extended_end = planned_end + timedelta(days=1)
    update_response = client.patch(
        f"/api/rentals/{rental_id}",
        json={"planned_end_date": extended_end.isoformat()},
    )

    assert update_response.status_code == 200
    assert update_response.json()["planned_end_date"] == extended_end.isoformat()

    end_response = client.post(
        f"/api/rentals/{rental_id}/end",
        params={"end_date": today.isoformat()},
    )

    assert end_response.status_code == 200
    assert end_response.json()["planned_end_date"] == extended_end.isoformat()
    assert end_response.json()["end_date"] == today.isoformat()
    assert client.get("/api/cars").json()[0]["status"] == "available"


def test_rejects_second_active_rental_for_same_car(client):
    """Overlapping rentals for the same car must return 409 Conflict."""
    today = date.today()
    car_id = client.post("/api/cars", json={"model": "Mazda 3", "year": 2023}).json()["id"]
    first = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Avi Cohen",
            "start_date": today.isoformat(),
            "planned_end_date": (today + timedelta(days=2)).isoformat(),
        },
    )
    second = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Noa Amir",
            "start_date": (today + timedelta(days=1)).isoformat(),
            "planned_end_date": (today + timedelta(days=3)).isoformat(),
        },
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_future_rentals_do_not_make_car_rented_now(client):
    """Future rentals should reserve dates without making the car rented today."""
    today = date.today()
    future_start = today + timedelta(days=30)
    future_end = future_start + timedelta(days=2)
    next_week_start = today + timedelta(days=7)
    next_week_end = next_week_start + timedelta(days=2)
    car_id = client.post("/api/cars", json={"model": "Hyundai i20", "year": 2024}).json()["id"]

    future = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Dana Levi",
            "start_date": future_start.isoformat(),
            "planned_end_date": future_end.isoformat(),
        },
    )
    next_week = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Noa Amir",
            "start_date": next_week_start.isoformat(),
            "planned_end_date": next_week_end.isoformat(),
        },
    )
    overlap = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Avi Cohen",
            "start_date": (future_start + timedelta(days=1)).isoformat(),
            "planned_end_date": (future_end + timedelta(days=1)).isoformat(),
        },
    )

    assert future.status_code == 201
    assert next_week.status_code == 201
    assert overlap.status_code == 409
    assert client.get("/api/cars").json()[0]["status"] == "available"


def test_rejects_past_rental_dates_over_api(client):
    """The API must reject rental schedules that use dates before today."""
    today = date.today()
    car_id = client.post("/api/cars", json={"model": "Kia Picanto", "year": 2024}).json()["id"]

    past_start = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Past Start",
            "start_date": (today - timedelta(days=1)).isoformat(),
            "planned_end_date": (today + timedelta(days=1)).isoformat(),
        },
    )
    past_return = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Past Return",
            "start_date": today.isoformat(),
            "planned_end_date": (today - timedelta(days=1)).isoformat(),
        },
    )

    assert past_start.status_code == 409
    assert past_return.status_code == 409


def test_metrics_endpoint_is_available(client):
    """The Prometheus metrics endpoint should be reachable by monitoring tools."""
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "rental_fleet_available_cars" in response.text


def test_operation_statistics_endpoint_is_available(client):
    """The UI statistics endpoint should expose measured operation timings."""
    client.get("/api/cars")

    response = client.get("/api/operation-statistics")
    body = response.json()

    assert response.status_code == 200
    assert "operations" in body
    assert "average_ms" in body
    assert body["total_count"] >= 1
    assert any(operation["operation"] == "list_cars" for operation in body["operations"])


def test_logs_endpoint_is_available(client):
    """The UI Logs button needs a plain-text log endpoint to open."""
    response = client.get("/api/logs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
