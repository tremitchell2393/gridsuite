/**
 * Dashboard / Overview page.
 *
 * Maps to "Dashboard/Overview" in the architecture doc's MVP screen
 * list: KPI row + lane table summarizing all watched lanes. Clicking a
 * lane row navigates to its detail page (Lane Detail screen).
 */
import { useNavigate } from "react-router-dom";
import { useDashboardSummary, useWatchedLanes } from "@/hooks/useApi";
import { ConfidenceBar, EmptyState, ForecastBadge, KpiCard, Panel } from "@/components/Dashboard";

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: summary, isLoading } = useDashboardSummary();
  const { data: watchedLanes } = useWatchedLanes();

  const lanesWithForecast = summary?.filter((s) => s.forecast_30d).length ?? 0;
  const avgConfidence =
    summary && summary.length > 0
      ? summary.reduce((sum, s) => sum + (s.forecast_30d?.confidence ?? 0), 0) /
        Math.max(1, summary.filter((s) => s.forecast_30d).length)
      : 0;

  return (
    <>
      <div className="page-header">
        <h1>Overview</h1>
        <p>Forecast summary across your watched lanes.</p>
      </div>

      <div className="kpi-row">
        <KpiCard label="Watched Lanes" value={watchedLanes?.length ?? 0} unit="/∞" />
        <KpiCard
          label="Lanes with Forecast"
          value={lanesWithForecast}
          unit={`/${summary?.length ?? 0}`}
        />
        <KpiCard
          label="Avg. Confidence"
          value={avgConfidence ? `${Math.round(avgConfidence * 100)}` : "—"}
          unit="%"
          change={avgConfidence < 0.5 ? "Models warming up" : undefined}
          changeDirection="neutral"
        />
        <KpiCard label="Active Alerts" value="—" />
      </div>

      <Panel title="Rate Forecasts — Watched Lanes">
        {isLoading ? (
          <EmptyState title="Loading…" />
        ) : !summary || summary.length === 0 ? (
          <EmptyState
            title="No watched lanes yet"
            description="Add a lane from Settings to start seeing forecasts here."
          />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Lane</th>
                <th>Current</th>
                <th>30d Forecast</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((row) => (
                <tr key={row.lane_id} onClick={() => navigate(`/lanes/${row.lane_id}`)}>
                  <td className="td-lane">{row.lane_id}</td>
                  <td className="td-price">
                    {row.current_value != null ? `${row.current_value} ${row.current_unit}` : "—"}
                  </td>
                  <td>
                    {row.forecast_30d ? (
                      <ForecastBadge
                        value={row.forecast_30d.predicted_value}
                        unit={row.forecast_30d.unit}
                      />
                    ) : (
                      <span className="text-3">—</span>
                    )}
                  </td>
                  <td>
                    {row.forecast_30d ? (
                      <ConfidenceBar confidence={row.forecast_30d.confidence} />
                    ) : (
                      <span className="text-3">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
    </>
  );
}
