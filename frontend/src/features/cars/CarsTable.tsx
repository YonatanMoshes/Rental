/**
 * Cars table component.
 * 
 * Displays all fleet vehicles in a table with:
 * - Car details (model, year)
 * - Current status badge
 * - Active rental information
 * - Action buttons (rent, maintenance, delete)
 * - Status filter for quick viewing
 */

import { CheckCircle2, Trash2, Wrench } from "lucide-react";

import { StatusBadge } from "../../components/StatusBadge";
import type { Car, Rental, VehicleStatus } from "../../types/fleet";
import { todayIsoDate } from "../../utils/dates";
import { carDisplayName } from "../../utils/labels";

type CarsTableProps = {
  /** Array of cars to display. */
  cars: Car[];
  /** All rentals (used to show active rental info). */
  rentals: Rental[];
  /** Current status filter (empty string means no filter). */
  statusFilter: VehicleStatus | "";
  /** Callback when status filter changes. */
  onStatusFilterChange: (status: VehicleStatus | "") => void;
  /** Callback to update a car's status. */
  onUpdateStatus: (carId: string, status: VehicleStatus) => Promise<void>;
  /** Callback to delete a car. */
  onDeleteCar: (carId: string) => Promise<void>;
  /** Callback when user clicks rent button for a car. */
  onSelectForRental: (carId: string) => void;
};

export function CarsTable({
  cars,
  rentals,
  statusFilter,
  onStatusFilterChange,
  onUpdateStatus,
  onDeleteCar,
  onSelectForRental
}: CarsTableProps) {
  const today = todayIsoDate();

  function activeRental(carId: string): Rental | undefined {
    return rentals.find((rental) => {
      const plannedEndDate = rental.planned_end_date ?? rental.start_date;
      return (
        rental.car_id === carId
        && rental.end_date === null
        && rental.start_date <= today
        && plannedEndDate >= today
      );
    });
  }

  function currentStatus(car: Car): VehicleStatus {
    if (car.status === "maintenance") {
      return "maintenance";
    }
    return activeRental(car.id) ? "rented" : "available";
  }

  const visibleCars = statusFilter ? cars.filter((car) => currentStatus(car) === statusFilter) : cars;

  return (
    <section className="panel table-panel">
      <div className="panel-heading table-heading">
        <div>
          <h2>Cars</h2>
          <p>{visibleCars.length} records</p>
        </div>

        <label className="compact-field">
          Status
          <select
            value={statusFilter}
            onChange={(event) => onStatusFilterChange(event.target.value as VehicleStatus | "")}
          >
            <option value="">All</option>
            <option value="available">Available</option>
            <option value="rented">Rented</option>
            <option value="maintenance">Maintenance</option>
          </select>
        </label>
      </div>

      {visibleCars.length === 0 ? (
        <p className="empty-state">No cars match the selected view.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Car</th>
                <th>Status</th>
                <th>Current rental</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {visibleCars.map((car) => {
                const rental = activeRental(car.id);
                const status = currentStatus(car);
                return (
                  <tr key={car.id}>
                    <td data-label="Car">
                      <strong>{carDisplayName(car)}</strong>
                      <span className="muted">ID: {car.id}</span>
                    </td>
                    <td data-label="Status">
                      <StatusBadge status={status} />
                    </td>
                    <td data-label="Current rental">
                      {rental ? `${rental.customer_name} (${rental.start_date})` : "-"}
                    </td>
                    <td data-label="Actions">
                      <div className="row-actions">
                        {status === "available" && (
                          <button type="button" onClick={() => onSelectForRental(car.id)}>
                            <CheckCircle2 size={17} aria-hidden="true" />
                            Rent
                          </button>
                        )}
                        {status !== "rented" && (
                          <button
                            type="button"
                            onClick={() =>
                              onUpdateStatus(
                                car.id,
                                status === "maintenance" ? "available" : "maintenance"
                              )
                            }
                          >
                            <Wrench size={17} aria-hidden="true" />
                            {status === "maintenance" ? "Available" : "Maintenance"}
                          </button>
                        )}
                        <button className="danger-button" type="button" onClick={() => onDeleteCar(car.id)}>
                          <Trash2 size={17} aria-hidden="true" />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
