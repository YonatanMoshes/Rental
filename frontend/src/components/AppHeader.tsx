/**
 * Application header component.
 * 
 * Displays the app title and navigation links to:
 * - Application logs
 * - Operation statistics
 * - Data refresh button
 */

import { Activity, BarChart3, FileText } from "lucide-react";

type AppHeaderProps = {
  /** Callback when refresh button is clicked. */
  onRefresh: () => void;
  /** If true, disables the refresh button during data loading. */
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
        <a href="/api/logs" target="_blank" rel="noreferrer">
          <FileText size={18} aria-hidden="true" />
          Logs
        </a>
        <a href="#operation-statistics">
          <BarChart3 size={18} aria-hidden="true" />
          Statistics
        </a>
        <button type="button" onClick={onRefresh} disabled={isLoading}>
          <Activity size={18} aria-hidden="true" />
          Refresh
        </button>
      </nav>
    </header>
  );
}
