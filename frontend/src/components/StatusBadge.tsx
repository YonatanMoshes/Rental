/**
 * Status badge component.
 * 
 * Displays a vehicle status (available, rented, maintenance) as a styled badge.
 * Styling is applied via CSS classes based on the status value.
 */

import type { VehicleStatus } from "../types/fleet";
import { statusLabels } from "../utils/labels";

type StatusBadgeProps = {
  /** The vehicle status to display. */
  status: VehicleStatus;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`status-badge status-${status}`}>{statusLabels[status]}</span>;
}
