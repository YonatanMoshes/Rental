/**
 * Rentals table component.
 * 
 * Displays all rentals (past and active) with:
 * - Car details
 * - Customer name
 * - Start, planned return, and actual end dates
 * - Planned return editing for open rentals
 * - Action button to end active rentals
 */

import { CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";

import type { Car, Rental } from "../../types/fleet";
import { todayIsoDate } from "../../utils/dates";
import { carDisplayName } from "../../utils/labels";

type RentalsTableProps = {
  /** All cars (used for looking up car names). */
  cars: Car[];
  /** All rentals to display. */
  rentals: Rental[];
  /** Callback when user changes the planned return date. */
  onUpdatePlannedEnd: (rentalId: string, plannedEndDate: string) => Promise<void>;
  /** Callback when user clicks 'End rental' button. */
  onEndRental: (rental: Rental) => Promise<void>;
  /** If true, disables rental action buttons during save. */
  isSaving: boolean;
};

export function RentalsTable({
  cars,
  rentals,
  onUpdatePlannedEnd,
  onEndRental,
  isSaving
}: RentalsTableProps) {
  const [draftPlannedEnds, setDraftPlannedEnds] = useState<Record<string, string>>({});

  useEffect(() => {
    const nextDrafts: Record<string, string> = {};
    for (const rental of rentals) {
      if (rental.end_date === null) {
        nextDrafts[rental.id] = rental.planned_end_date ?? rental.start_date;
      }
    }
    setDraftPlannedEnds(nextDrafts);
  }, [rentals]);

  function carName(carId: string): string {
    const car = cars.find((item) => item.id === carId);
    return car ? carDisplayName(car) : `Car ${carId}`;
  }

  function plannedEndValue(rental: Rental): string {
    return draftPlannedEnds[rental.id] ?? rental.planned_end_date ?? rental.start_date;
  }

  function setPlannedEndValue(rentalId: string, value: string) {
    setDraftPlannedEnds((current) => ({ ...current, [rentalId]: value }));
  }

  function handlePlannedEndChange(rental: Rental, value: string) {
    if (!value) {
      return;
    }
    setPlannedEndValue(rental.id, value);
    void onUpdatePlannedEnd(rental.id, value);
  }

  function rentalCanEndNow(rental: Rental): boolean {
    return rental.end_date === null && rental.start_date <= todayIsoDate();
  }

  function openRentalLabel(rental: Rental): string {
    if (rental.end_date !== null) {
      return rental.end_date;
    }
    if (rental.start_date > todayIsoDate()) {
      return "Scheduled";
    }
    return "Open";
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
                <th>Planned start</th>
                <th>Planned return</th>
                <th>Actual end</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rentals.map((rental) => (
                <tr key={rental.id}>
                  <td data-label="Car">{carName(rental.car_id)}</td>
                  <td data-label="Customer">{rental.customer_name}</td>
                  <td data-label="Planned start">{rental.start_date}</td>
                  <td data-label="Planned return">
                    {rental.end_date === null ? (
                      <div className="date-action-row">
                        <input
                          aria-label={`Planned return date for ${rental.customer_name}`}
                          type="date"
                          value={plannedEndValue(rental)}
                          min={rental.start_date}
                          onChange={(event) => handlePlannedEndChange(rental, event.target.value)}
                          disabled={isSaving}
                        />
                      </div>
                    ) : (
                      rental.planned_end_date ?? "-"
                    )}
                  </td>
                  <td data-label="Actual end">{openRentalLabel(rental)}</td>
                  <td data-label="Actions">
                    {rentalCanEndNow(rental) ? (
                      <button type="button" onClick={() => onEndRental(rental)} disabled={isSaving}>
                        <CheckCircle2 size={17} aria-hidden="true" />
                        End now
                      </button>
                    ) : rental.end_date === null ? (
                      <span className="muted">Scheduled</span>
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
