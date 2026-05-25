/**
 * Car creation form component.
 * 
 * Allows users to add a new vehicle to the fleet by entering:
 * - Model name
 * - Year of manufacture
 * - Initial status (available or maintenance)
 */

import { Plus } from "lucide-react";
import { useState } from "react";

import type { CarCreatePayload, VehicleStatus } from "../../types/fleet";

type CarFormProps = {
  /** Callback when form is submitted with car data. */
  onSubmit: (payload: CarCreatePayload) => Promise<void>;
  /** If true, disables the submit button and shows saving state. */
  isSaving: boolean;
};

export function CarForm({ onSubmit, isSaving }: CarFormProps) {
  const [model, setModel] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [status, setStatus] = useState<VehicleStatus>("available");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ model: model.trim(), year, status });
    setModel("");
    setYear(new Date().getFullYear());
    setStatus("available");
  }

  return (
    <form className="panel form-panel" onSubmit={handleSubmit}>
      <div className="panel-heading">
        <h2>Add Car</h2>
      </div>

      <label>
        Model
        <input
          value={model}
          onChange={(event) => setModel(event.target.value)}
          placeholder="Toyota Corolla"
          required
        />
      </label>

      <div className="form-grid">
        <label>
          Year
          <input
            type="number"
            min={1886}
            max={2100}
            value={year}
            onChange={(event) => setYear(Number(event.target.value))}
            required
          />
        </label>

        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value as VehicleStatus)}>
            <option value="available">Available</option>
            <option value="maintenance">Maintenance</option>
          </select>
        </label>
      </div>

      <button className="primary-button" type="submit" disabled={isSaving}>
        <Plus size={18} aria-hidden="true" />
        Add car
      </button>
    </form>
  );
}
