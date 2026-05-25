import { request } from "./http";
import type {
  Car,
  CarCreatePayload,
  CarUpdatePayload,
  Rental,
  RentalCreatePayload,
  VehicleStatus
} from "../types/fleet";

export function listCars(status?: VehicleStatus): Promise<Car[]> {
  const query = status ? `?status=${status}` : "";
  return request<Car[]>(`/api/cars${query}`);
}

export function createCar(payload: CarCreatePayload): Promise<Car> {
  return request<Car>("/api/cars", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateCar(carId: string, payload: CarUpdatePayload): Promise<Car> {
  return request<Car>(`/api/cars/${carId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deleteCar(carId: string): Promise<void> {
  return request<void>(`/api/cars/${carId}`, {
    method: "DELETE"
  });
}

export function listRentals(openOnly?: boolean): Promise<Rental[]> {
  const query = openOnly === undefined ? "" : `?open_only=${openOnly}`;
  return request<Rental[]>(`/api/rentals${query}`);
}

export function createRental(payload: RentalCreatePayload): Promise<Rental> {
  return request<Rental>("/api/rentals", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function endRental(rentalId: string, endDate: string): Promise<Rental> {
  return request<Rental>(`/api/rentals/${rentalId}/end?end_date=${endDate}`, {
    method: "POST"
  });
}
