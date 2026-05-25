/**
 * Display label utilities.
 * 
 * Provides human-readable labels and formatting for domain objects.
 */

import type { Car, VehicleStatus } from "../types/fleet";

/** Maps vehicle status values to display labels. */
export const statusLabels: Record<VehicleStatus, string> = {
  available: "Available",
  rented: "Rented",
  maintenance: "Maintenance"
};

/**
 * Format a car as a display string.
 * 
 * @param car Car record
 * @returns Formatted string like "Toyota Corolla (2021)"
 */
export function carDisplayName(car: Car): string {
  return `${car.model} (${car.year})`;
}
