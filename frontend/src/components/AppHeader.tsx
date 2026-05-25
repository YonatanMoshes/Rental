import { Activity, BarChart3, Server } from "lucide-react";

type AppHeaderProps = {
  onRefresh: () => void;
  isLoading: boolean;
};

export function AppHeader({ onRefresh, isLoading }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div>
        <p className="eyebrow">Rental Fleet Manager</p>
        <h1>Fleet Dashboard</h1>
      </div>

      <nav className="header-actions" aria-label="Application links">
        <a href="/docs" target="_blank" rel="noreferrer">
          <Server size={18} aria-hidden="true" />
          API Docs
        </a>
        <a href="/metrics" target="_blank" rel="noreferrer">
          <BarChart3 size={18} aria-hidden="true" />
          Metrics
        </a>
        <button type="button" onClick={onRefresh} disabled={isLoading}>
          <Activity size={18} aria-hidden="true" />
          Refresh
        </button>
      </nav>
    </header>
  );
}
