/**
 * Main dashboard page component.
 * 
 * Orchestrates the entire rental fleet management UI including:
 * - Summary metrics (total cars, available, in maintenance, open rentals)
 * - Car management form and table
 * - Rental management form and table
 * - State management and API communication
 * - Error and success message handling
 * - Data refresh and loading states
 * 
 * The dashboard fetches all data on mount and after each action.
 */

import { CarFront, ClipboardList, Gauge, Wrench } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  createCar,
  createRental,
  deleteCar,
  endRental,
  listCars,
  listRentals,
  updateCar,
  updateRental
} from "../api/fleetApi";
import { AppHeader } from "../components/AppHeader";
import { SummaryTile } from "../components/SummaryTile";
import { CarForm } from "../features/cars/CarForm";
import { CarsTable } from "../features/cars/CarsTable";
import { RentalForm } from "../features/rentals/RentalForm";
import { RentalsTable } from "../features/rentals/RentalsTable";
import type {
  Car,
  CarCreatePayload,
  Rental,
  RentalCreatePayload,
  VehicleStatus
} from "../types/fleet";
import { todayIsoDate } from "../utils/dates";

export function DashboardPage() {
  const [cars, setCars] = useState<Car[]>([]);
  const [rentals, setRentals] = useState<Rental[]>([]);
  const [statusFilter, setStatusFilter] = useState<VehicleStatus | "">("");
  const [selectedRentalCarId, setSelectedRentalCarId] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const availableCars = useMemo(() => cars.filter((car) => car.status === "available"), [cars]);
  const openRentals = useMemo(() => rentals.filter((rental) => rental.end_date === null), [rentals]);

  async function loadDashboard() {
    setIsLoading(true);
    setError(null);
    try {
      const [carsResult, rentalsResult] = await Promise.all([listCars(), listRentals()]);
      setCars(carsResult);
      setRentals(rentalsResult);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  async function runAction(action: () => Promise<void>, successMessage: string) {
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      await loadDashboard();
      setMessage(successMessage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Action failed.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCreateCar(payload: CarCreatePayload) {
    await runAction(async () => {
      await createCar(payload);
    }, "Car added.");
  }

  async function handleCreateRental(payload: RentalCreatePayload) {
    await runAction(async () => {
      await createRental(payload);
      setSelectedRentalCarId("");
    }, "Rental started.");
  }

  async function handleUpdateStatus(carId: string, status: VehicleStatus) {
    await runAction(async () => {
      await updateCar(carId, { status });
    }, "Car status updated.");
  }

  async function handleDeleteCar(carId: string) {
    const confirmed = window.confirm("Delete this car?");
    if (!confirmed) {
      return;
    }
    await runAction(async () => {
      await deleteCar(carId);
    }, "Car deleted.");
  }

  async function handleEndRental(rental: Rental) {
    await runAction(async () => {
      const today = todayIsoDate();
      const safeEndDate = rental.start_date > today ? rental.start_date : today;
      await endRental(rental.id, safeEndDate);
    }, "Rental ended.");
  }

  async function handleUpdateRentalPlan(rentalId: string, plannedEndDate: string | null) {
    await runAction(async () => {
      await updateRental(rentalId, { planned_end_date: plannedEndDate });
    }, "Rental plan updated.");
  }

  return (
    <main className="app-shell">
      <AppHeader onRefresh={loadDashboard} isLoading={isLoading} />

      {(message || error) && (
        <section className={`notice ${error ? "notice-error" : "notice-success"}`} role="status">
          {error ?? message}
        </section>
      )}

      <section className="summary-grid" aria-label="Fleet summary">
        <SummaryTile label="Total cars" value={cars.length} icon={CarFront} />
        <SummaryTile label="Available" value={availableCars.length} icon={Gauge} />
        <SummaryTile
          label="Maintenance"
          value={cars.filter((car) => car.status === "maintenance").length}
          icon={Wrench}
        />
        <SummaryTile label="Open rentals" value={openRentals.length} icon={ClipboardList} />
      </section>

      <section className="dashboard-grid">
        <div className="forms-column">
          <CarForm onSubmit={handleCreateCar} isSaving={isSaving} />
          <RentalForm
            availableCars={availableCars}
            selectedCarId={selectedRentalCarId}
            onSelectedCarChange={setSelectedRentalCarId}
            onSubmit={handleCreateRental}
            isSaving={isSaving}
          />
        </div>

        <div className="tables-column">
          <CarsTable
            cars={cars}
            rentals={rentals}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            onUpdateStatus={handleUpdateStatus}
            onDeleteCar={handleDeleteCar}
            onSelectForRental={setSelectedRentalCarId}
          />
          <RentalsTable
            cars={cars}
            rentals={rentals}
            onUpdatePlannedEnd={handleUpdateRentalPlan}
            onEndRental={handleEndRental}
            isSaving={isSaving}
          />
        </div>
      </section>
    </main>
  );
}
