/**
 * Type definitions for the rental fleet system.
 * 
 * These types match the API responses and request payloads from the FastAPI backend.
 */

export type VehicleStatus = "available" | "rented" | "maintenance";

/** A car record from the API. */
export type Car = {
  id: string;
  model: string;
  year: number;
  status: VehicleStatus;
};

/** A rental record from the API. */
export type Rental = {
  id: string;
  car_id: string;
  customer_name: string;
  start_date: string;
  planned_end_date: string | null;
  end_date: string | null;
};

/** Request payload for creating a new car. */
export type CarCreatePayload = {
  model: string;
  year: number;
  status: VehicleStatus;
};

/** Request payload for updating car details (all fields optional). */
export type CarUpdatePayload = {
  model?: string;
  year?: number;
  status?: VehicleStatus;
};

/** Request payload for starting a new rental. */
export type RentalCreatePayload = {
  car_id: string;
  customer_name: string;
  start_date: string;
  planned_end_date: string;
};

/** Request payload for editing an open rental. */
export type RentalUpdatePayload = {
  planned_end_date: string;
};
