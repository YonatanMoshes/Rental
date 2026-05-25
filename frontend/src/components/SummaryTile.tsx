import type { LucideIcon } from "lucide-react";

type SummaryTileProps = {
  label: string;
  value: number;
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
