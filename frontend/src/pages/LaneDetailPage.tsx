/**
 * Lane Detail page.
 *
 * Maps to "Lane Detail" in the architecture doc's MVP screen list:
 * forecast chart with confidence bands, signal attribution breakdown,
 * historical accuracy for this lane.
 *
 * The chart shows actual signal history (line) plus the 30/60/90-day
 * forecast points with their confidence bands — directly visualizing
 * the Forecast.lower_bound/upper_bound fields from the backend.
 */
import { useParams } from "react-router-dom";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
} from "chart.js";
import { useLaneForecasts, useSignals } from "@/hooks/useApi";
import { EmptyState, Panel } from "@/components/Dashboard";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler);

const CHART_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: "index" as const, intersect: false },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: "#1E2230",
      borderColor: "#252A38",
      borderWidth: 1,
      titleColor: "#9BA5C0",
      bodyColor: "#F0F2F8",
      titleFont: { family: "JetBrains Mono", size: 10 },
      bodyFont: { family: "JetBrains Mono", size: 11 },
    },
  },
  scales: {
    x: {
      grid: { color: "#2A3254" },
      ticks: { color: "#5A6480", font: { family: "JetBrains Mono", size: 10 } },
    },
    y: {
      grid: { color: "#2A3254" },
      ticks: { color: "#5A6480", font: { family: "JetBrains Mono", size: 10 } },
    },
  },
};

export function LaneDetailPage() {
  const { laneId = "" } = useParams<{ laneId: string }>();
  const { data: forecasts, isLoading: forecastsLoading } = useLaneForecasts(laneId);
  const { data: customsSignals } = useSignals("lane", laneId, "customs_velocity_index", 90);

  const forecast30d = forecasts?.find((f) => f.horizon_days === 30);

  const chartData = buildChartData(customsSignals?.signals ?? [], forecast30d);

  return (
    <>
      <div className="page-header">
        <h1 className="mono">{laneId}</h1>
        <p>Rate forecast and signal attribution for this lane.</p>
      </div>

      <Panel title="30-Day Forecast — Customs Velocity Index">
        {forecastsLoading ? (
          <EmptyState title="Loading…" />
        ) : !forecast30d ? (
          <EmptyState
            title="No forecast available yet"
            description="Forecasts are generated daily once enough signal history accumulates for this lane."
          />
        ) : (
          <>
            <div style={{ height: 240, marginBottom: 16 }}>
              <Line data={chartData} options={CHART_OPTIONS} />
            </div>
            <div className="forecast-summary">
              <div>
                <div className="text-3 mono" style={{ fontSize: 10, letterSpacing: "0.1em" }}>
                  PREDICTED CHANGE
                </div>
                <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>
                  {(forecast30d.predicted_value * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-3 mono" style={{ fontSize: 10, letterSpacing: "0.1em" }}>
                  CONFIDENCE
                </div>
                <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>
                  {(forecast30d.confidence * 100).toFixed(0)}%
                </div>
              </div>
              <div>
                <div className="text-3 mono" style={{ fontSize: 10, letterSpacing: "0.1em" }}>
                  MODEL VERSION
                </div>
                <div className="mono" style={{ fontSize: 14, color: "var(--text-2)" }}>
                  {forecast30d.model_version}
                </div>
              </div>
            </div>
          </>
        )}
      </Panel>

      {forecast30d && forecast30d.signal_attribution.length > 0 && (
        <Panel title="Signal Attribution — Why the model is calling this">
          <table className="table">
            <thead>
              <tr>
                <th>Signal</th>
                <th>Current Value</th>
                <th>30-day Baseline</th>
              </tr>
            </thead>
            <tbody>
              {forecast30d.signal_attribution.map((attr) => (
                <tr key={attr.signal_id}>
                  <td className="td-lane">{attr.signal_id}</td>
                  <td className="td-price">{attr.value?.toFixed(3) ?? "—"}</td>
                  <td className="td-price">{attr.baseline_30d?.toFixed(3) ?? attr.note ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </>
  );
}

function buildChartData(
  signals: { timestamp: string; value: number }[],
  forecast?: { target_date: string; predicted_value: number; lower_bound: number | null; upper_bound: number | null }
) {
  const labels = signals.map((s) => new Date(s.timestamp).toLocaleDateString(undefined, { month: "short", day: "numeric" }));
  const actual = signals.map((s) => s.value);

  if (forecast) {
    labels.push(new Date(forecast.target_date).toLocaleDateString(undefined, { month: "short", day: "numeric" }));
  }

  const forecastLine = new Array(actual.length).fill(null);
  const upperLine = new Array(actual.length).fill(null);
  const lowerLine = new Array(actual.length).fill(null);

  if (forecast) {
    const lastActual = actual[actual.length - 1] ?? 0;

    // forecast.predicted_value is a pct_change (e.g. 0.11 = +11%), while
    // `actual` is the raw signal value (e.g. ~1.0-1.18 for
    // customs_velocity_index). Plotting 0.11 directly on the same axis
    // as ~1.0-1.18 makes the forecast point collapse near zero —
    // instead, convert the forecast to an "implied future value" on the
    // same scale as the actual series: lastActual * (1 + pct_change).
    const toImplied = (pct: number) => lastActual * (1 + pct);

    forecastLine[actual.length - 1] = lastActual;
    forecastLine.push(toImplied(forecast.predicted_value));

    upperLine[actual.length - 1] = lastActual;
    upperLine.push(toImplied(forecast.upper_bound ?? forecast.predicted_value));

    lowerLine[actual.length - 1] = lastActual;
    lowerLine.push(toImplied(forecast.lower_bound ?? forecast.predicted_value));

    actual.push(NaN); // gap for the actual line at the forecast point
  }

  return {
    labels,
    datasets: [
      {
        label: "Actual",
        data: actual,
        borderColor: "#9BA5C0",
        borderWidth: 1.5,
        pointRadius: 2,
        spanGaps: false,
      },
      {
        label: "Forecast",
        data: forecastLine,
        borderColor: "#00D4AA",
        borderWidth: 2,
        borderDash: [4, 3],
        pointRadius: 2,
        spanGaps: false,
      },
      {
        label: "Upper",
        data: upperLine,
        borderColor: "rgba(0,212,170,0.15)",
        borderWidth: 0,
        fill: "+1",
        backgroundColor: "rgba(0,212,170,0.06)",
        pointRadius: 0,
        spanGaps: false,
      },
      {
        label: "Lower",
        data: lowerLine,
        borderColor: "rgba(0,212,170,0.15)",
        borderWidth: 0,
        pointRadius: 0,
        spanGaps: false,
      },
    ],
  };
}
