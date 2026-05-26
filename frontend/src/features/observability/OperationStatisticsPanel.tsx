/**
 * Operation statistics panel.
 *
 * Shows the average execution time of every tracked backend operation, plus the
 * average across all measured operations together.
 */

import { TimerReset } from "lucide-react";

import type { OperationStatistics } from "../../types/fleet";

type OperationStatisticsPanelProps = {
  statistics: OperationStatistics | null;
  isLoading: boolean;
};

function formatMilliseconds(value: number): string {
  return `${value.toFixed(2)} ms`;
}

export function OperationStatisticsPanel({
  statistics,
  isLoading
}: OperationStatisticsPanelProps) {
  return (
    <section className="panel table-panel" id="operation-statistics">
      <div className="panel-heading table-heading">
        <div>
          <h2>Operation Statistics</h2>
          <p>{statistics?.total_count ?? 0} measured operations</p>
        </div>
        <div className="stat-chip">
          <TimerReset size={18} aria-hidden="true" />
          <span>All operations avg</span>
          <strong>{formatMilliseconds(statistics?.average_ms ?? 0)}</strong>
        </div>
      </div>

      {isLoading ? (
        <p className="empty-state">Loading statistics...</p>
      ) : statistics === null || statistics.operations.length === 0 ? (
        <p className="empty-state">No operation timing data yet.</p>
      ) : (
        <div className="table-wrap">
          <table className="stats-table">
            <thead>
              <tr>
                <th>Operation</th>
                <th>Calls</th>
                <th>Average</th>
                <th>Last</th>
                <th>Fastest</th>
                <th>Slowest</th>
              </tr>
            </thead>
            <tbody>
              {statistics.operations.map((operation) => (
                <tr key={operation.operation}>
                  <td data-label="Operation">
                    <strong>{operation.operation}</strong>
                  </td>
                  <td data-label="Calls">{operation.count}</td>
                  <td data-label="Average">{formatMilliseconds(operation.average_ms)}</td>
                  <td data-label="Last">{formatMilliseconds(operation.last_ms)}</td>
                  <td data-label="Fastest">{formatMilliseconds(operation.min_ms)}</td>
                  <td data-label="Slowest">{formatMilliseconds(operation.max_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
