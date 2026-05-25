def test_car_and_rental_flow_over_api(client):
    car_response = client.post("/api/cars", json={"model": "Toyota Corolla", "year": 2024})
    car_id = car_response.json()["id"]

    rental_response = client.post(
        "/api/rentals",
        json={
            "car_id": car_id,
            "customer_name": "Dana Levi",
            "start_date": "2026-05-25",
        },
    )
    rental_id = rental_response.json()["id"]

    assert car_response.status_code == 201
    assert rental_response.status_code == 201
    assert client.get("/api/cars").json()[0]["status"] == "rented"

    end_response = client.post(
        f"/api/rentals/{rental_id}/end",
        params={"end_date": "2026-05-26"},
    )

    assert end_response.status_code == 200
    assert end_response.json()["end_date"] == "2026-05-26"
    assert client.get("/api/cars").json()[0]["status"] == "available"


def test_rejects_second_active_rental_for_same_car(client):
    car_id = client.post("/api/cars", json={"model": "Mazda 3", "year": 2023}).json()["id"]
    first = client.post("/api/rentals", json={"car_id": car_id, "customer_name": "Avi Cohen"})
    second = client.post("/api/rentals", json={"car_id": car_id, "customer_name": "Noa Amir"})

    assert first.status_code == 201
    assert second.status_code == 409


def test_metrics_endpoint_is_available(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "rental_fleet_available_cars" in response.text
