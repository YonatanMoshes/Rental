import type { VehicleStatus } from "../types/fleet";
import { statusLabels } from "../utils/labels";

type StatusBadgeProps = {
  status: VehicleStatus;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`status-badge status-${status}`}>{statusLabels[status]}</span>;
}
