import type { Car, VehicleStatus } from "../types/fleet";

export const statusLabels: Record<VehicleStatus, string> = {
  available: "Available",
  rented: "Rented",
  maintenance: "Maintenance"
};

export function carDisplayName(car: Car): string {
  return `${car.model} (${car.year})`;
}
