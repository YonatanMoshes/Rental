import { CheckCircle2, Trash2, Wrench } from "lucide-react";

import { StatusBadge } from "../../components/StatusBadge";
import type { Car, Rental, VehicleStatus } from "../../types/fleet";
import { carDisplayName } from "../../utils/labels";

type CarsTableProps = {
  cars: Car[];
  rentals: Rental[];
  statusFilter: VehicleStatus | "";
  onStatusFilterChange: (status: VehicleStatus | "") => void;
  onUpdateStatus: (carId: string, status: VehicleStatus) => Promise<void>;
  onDeleteCar: (carId: string) => Promise<void>;
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
  const visibleCars = statusFilter ? cars.filter((car) => car.status === statusFilter) : cars;

  function activeRental(carId: string): Rental | undefined {
    return rentals.find((rental) => rental.car_id === carId && rental.end_date === null);
  }

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
                return (
                  <tr key={car.id}>
                    <td data-label="Car">
                      <strong>{carDisplayName(car)}</strong>
                      <span className="muted">ID: {car.id}</span>
                    </td>
                    <td data-label="Status">
                      <StatusBadge status={car.status} />
                    </td>
                    <td data-label="Current rental">
                      {rental ? `${rental.customer_name} (${rental.start_date})` : "-"}
                    </td>
                    <td data-label="Actions">
                      <div className="row-actions">
                        {car.status === "available" && (
                          <button type="button" onClick={() => onSelectForRental(car.id)}>
                            <CheckCircle2 size={17} aria-hidden="true" />
                            Rent
                          </button>
                        )}
                        {car.status !== "rented" && (
                          <button
                            type="button"
                            onClick={() =>
                              onUpdateStatus(
                                car.id,
                                car.status === "maintenance" ? "available" : "maintenance"
                              )
                            }
                          >
                            <Wrench size={17} aria-hidden="true" />
                            {car.status === "maintenance" ? "Available" : "Maintenance"}
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
