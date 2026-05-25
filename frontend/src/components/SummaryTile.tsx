/**
 * Summary tile component.
 * 
 * Displays a metric with a label, numeric value, and icon.
 * Used in the dashboard to show stats like available cars, rented cars, etc.
 */

import type { LucideIcon } from "lucide-react";

type SummaryTileProps = {
  /** Display label for the metric. */
  label: string;
  /** Numeric value to display. */
  value: number;
  /** Lucide icon component to display. */
  icon: LucideIcon;
};

export function SummaryTile({ label, value, icon: Icon }: SummaryTileProps) {
  return (
    <article className="summary-tile">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <Icon size={22} aria-hidden="true" />
    </article>
  );
}
