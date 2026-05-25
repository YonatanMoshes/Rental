import { ClipboardPlus } from "lucide-react";
import { useEffect, useState } from "react";

import type { Car, RentalCreatePayload } from "../../types/fleet";
import { todayIsoDate } from "../../utils/dates";
import { carDisplayName } from "../../utils/labels";

type RentalFormProps = {
  availableCars: Car[];
  selectedCarId: string;
  onSelectedCarChange: (carId: string) => void;
  onSubmit: (payload: RentalCreatePayload) => Promise<void>;
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

  useEffect(() => {
    if (!selectedCarId && availableCars[0]) {
      onSelectedCarChange(availableCars[0].id);
    }
  }, [availableCars, onSelectedCarChange, selectedCarId]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({
      car_id: selectedCarId,
      customer_name: customerName.trim(),
      start_date: startDate
    });
    setCustomerName("");
    setStartDate(todayIsoDate());
  }

  return (
    <form className="panel form-panel" onSubmit={handleSubmit}>
      <div className="panel-heading">
        <h2>Start Rental</h2>
      </div>

      <label>
        Available car
        <select
          value={selectedCarId}
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

      <button className="primary-button" type="submit" disabled={isSaving || availableCars.length === 0}>
        <ClipboardPlus size={18} aria-hidden="true" />
        Start rental
      </button>
    </form>
  );
}
