/**
 * Fleet API client - Typed API calls to the backend.
 * 
 * All functions use the generic request utility to communicate with the FastAPI backend.
 * Return types are strictly typed using the types defined in fleet.ts.
 */

import { request } from "./http";
import type {
  Car,
  CarCreatePayload,
  CarUpdatePayload,
  OperationStatistics,
  Rental,
  RentalCreatePayload,
  RentalUpdatePayload,
  VehicleStatus
} from "../types/fleet";

/**
 * Get all cars, optionally filtered by status.
 */
export function listCars(status?: VehicleStatus): Promise<Car[]> {
  const query = status ? `?status=${status}` : "";
  return request<Car[]>(`/api/cars${query}`);
}

/**
 * Create a new car and add it to the fleet.
 */
export function createCar(payload: CarCreatePayload): Promise<Car> {
  return request<Car>("/api/cars", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

/**
 * Update car details (model, year, status).
 */
export function updateCar(carId: string, payload: CarUpdatePayload): Promise<Car> {
  return request<Car>(`/api/cars/${carId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

/**
 * Delete a car from the fleet.
 */
export function deleteCar(carId: string): Promise<void> {
  return request<void>(`/api/cars/${carId}`, {
    method: "DELETE"
  });
}

/**
 * Get all rentals, optionally filtered to open rentals only.
 */
export function listRentals(openOnly?: boolean): Promise<Rental[]> {
  const query = openOnly === undefined ? "" : `?open_only=${openOnly}`;
  return request<Rental[]>(`/api/rentals${query}`);
}

/**
 * Start a new rental for a customer.
 */
export function createRental(payload: RentalCreatePayload): Promise<Rental> {
  return request<Rental>("/api/rentals", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

/**
 * Edit an open rental's planned return date.
 */
export function updateRental(rentalId: string, payload: RentalUpdatePayload): Promise<Rental> {
  return request<Rental>(`/api/rentals/${rentalId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

/**
 * Mark a rental as ended and free up the car.
 */
export function endRental(rentalId: string, endDate: string): Promise<Rental> {
  return request<Rental>(`/api/rentals/${rentalId}/end?end_date=${endDate}`, {
    method: "POST"
  });
}

/**
 * Get average timing statistics for backend operations.
 */
export function getOperationStatistics(): Promise<OperationStatistics> {
  return request<OperationStatistics>("/api/operation-statistics");
}
