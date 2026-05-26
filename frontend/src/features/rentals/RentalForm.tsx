/**
 * Rental creation form component.
 * 
 * Allows users to start a new rental by selecting:
 * - An available car from a dropdown
 * - Customer name
 * - Start date (defaults to today)
 * 
 * Automatically selects the first available car when the form loads.
 */

import { ClipboardPlus } from "lucide-react";
import { useEffect, useState } from "react";

import type { Car, RentalCreatePayload } from "../../types/fleet";
import { todayIsoDate } from "../../utils/dates";
import { carDisplayName } from "../../utils/labels";

type RentalFormProps = {
  /** Cars currently available for rent. */
  availableCars: Car[];
  /** ID of the currently selected car. */
  selectedCarId: string;
  /** Callback when user selects a different car. */
  onSelectedCarChange: (carId: string) => void;
  /** Callback when form is submitted with rental data. */
  onSubmit: (payload: RentalCreatePayload) => Promise<void>;
  /** If true, disables the submit button during save. */
  isSaving: boolean;
};

export function RentalForm({
  availableCars,
  selectedCarId,
  onSelectedCarChange,
  onSubmit,
  isSaving
}: RentalFormProps) {
  const [customerName, setCustomerName] = useState("");
  const [startDate, setStartDate] = useState(todayIsoDate());
  const [plannedEndDate, setPlannedEndDate] = useState(todayIsoDate());
  const selectedCarIsAvailable = availableCars.some((car) => car.id === selectedCarId);
  const effectiveSelectedCarId = selectedCarIsAvailable ? selectedCarId : availableCars[0]?.id ?? "";

  useEffect(() => {
    if (availableCars.length === 0) {
      if (selectedCarId) {
        onSelectedCarChange("");
      }
      return;
    }

    if (!availableCars.some((car) => car.id === selectedCarId)) {
      onSelectedCarChange(availableCars[0].id);
    }
  }, [availableCars, onSelectedCarChange, selectedCarId]);

  useEffect(() => {
    if (plannedEndDate && plannedEndDate < startDate) {
      setPlannedEndDate(startDate);
    }
  }, [plannedEndDate, startDate]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!effectiveSelectedCarId) {
      return;
    }

    await onSubmit({
      car_id: effectiveSelectedCarId,
      customer_name: customerName.trim(),
      start_date: startDate,
      planned_end_date: plannedEndDate || null
    });
    setCustomerName("");
    setStartDate(todayIsoDate());
    setPlannedEndDate(todayIsoDate());
  }

  return (
    <form className="panel form-panel" onSubmit={handleSubmit}>
      <div className="panel-heading">
        <h2>Start Rental</h2>
      </div>

      <label>
        Available car
        <select
          value={effectiveSelectedCarId}
          onChange={(event) => onSelectedCarChange(event.target.value)}
          disabled={availableCars.length === 0}
          required
        >
          {availableCars.length === 0 ? (
            <option value="">No available cars</option>
          ) : (
            availableCars.map((car) => (
              <option key={car.id} value={car.id}>
                {carDisplayName(car)}
              </option>
            ))
          )}
        </select>
      </label>

      <label>
        Customer name
        <input
          value={customerName}
          onChange={(event) => setCustomerName(event.target.value)}
          placeholder="Dana Levi"
          required
        />
      </label>

      <label>
        Start date
        <input
          type="date"
          value={startDate}
          onChange={(event) => setStartDate(event.target.value)}
          required
        />
      </label>

      <label>
        Planned return date
        <input
          type="date"
          value={plannedEndDate}
          min={startDate}
          onChange={(event) => setPlannedEndDate(event.target.value)}
        />
      </label>

      <button className="primary-button" type="submit" disabled={isSaving || !effectiveSelectedCarId}>
        <ClipboardPlus size={18} aria-hidden="true" />
        Start rental
      </button>
    </form>
  );
}
