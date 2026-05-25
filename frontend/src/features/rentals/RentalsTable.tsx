import { CheckCircle2 } from "lucide-react";

import type { Car, Rental } from "../../types/fleet";
import { carDisplayName } from "../../utils/labels";

type RentalsTableProps = {
  cars: Car[];
  rentals: Rental[];
  onEndRental: (rentalId: string) => Promise<void>;
};

export function RentalsTable({ cars, rentals, onEndRental }: RentalsTableProps) {
  function carName(carId: string): string {
    const car = cars.find((item) => item.id === carId);
    return car ? carDisplayName(car) : `Car ${carId}`;
  }

  return (
    <section className="panel table-panel">
      <div className="panel-heading">
        <div>
          <h2>Rentals</h2>
          <p>{rentals.length} records</p>
        </div>
      </div>

      {rentals.length === 0 ? (
        <p className="empty-state">No rentals yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Car</th>
                <th>Customer</th>
                <th>Start</th>
                <th>End</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rentals.map((rental) => (
                <tr key={rental.id}>
                  <td data-label="Car">{carName(rental.car_id)}</td>
                  <td data-label="Customer">{rental.customer_name}</td>
                  <td data-label="Start">{rental.start_date}</td>
                  <td data-label="End">{rental.end_date ?? "Open"}</td>
                  <td data-label="Actions">
                    {rental.end_date === null ? (
                      <button type="button" onClick={() => onEndRental(rental.id)}>
                        <CheckCircle2 size={17} aria-hidden="true" />
                        End rental
                      </button>
                    ) : (
                      <span className="muted">Closed</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
