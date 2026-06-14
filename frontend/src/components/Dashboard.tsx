/**
 * Shared dashboard components: KPI cards, panels, confidence bars.
 *
 * Small, presentational components — data fetching happens in pages
 * (via hooks/useApi.ts), these just render whatever they're given.
 */
import type { ReactNode } from "react";
import "./Dashboard.css";

export function Panel({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">{title}</span>
        {action}
      </div>
      {children}
    </div>
  );
}

export function KpiCard({
  label,
  value,
  unit,
  change,
  changeDirection,
}: {
  label: string;
  value: string | number;
  unit?: string;
  change?: string;
  changeDirection?: "up" | "down" | "neutral";
}) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-val">
        {value}
        {unit && <span>{unit}</span>}
      </div>
      {change && (
        <span className={`kpi-change ${changeDirection ?? "neutral"}`}>{change}</span>
      )}
    </div>
  );
}

export function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  return (
    <span className="td-conf mono">
      {confidence.toFixed(2)}
      <span className="conf-mini">
        <span className="conf-mini-fill" style={{ width: `${pct}%` }} />
      </span>
    </span>
  );
}

export function ForecastBadge({ value, unit }: { value: number; unit: string }) {
  const direction = value > 0 ? "up" : value < 0 ? "down" : "neutral";
  const arrow = value > 0 ? "↑" : value < 0 ? "↓" : "→";
  const display = unit === "pct_change" ? `${(value * 100).toFixed(1)}%` : `${value}${unit}`;

  return (
    <span className={`td-forecast ${direction} mono`}>
      {arrow} {display}
    </span>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="empty-state">
      <div className="empty-state-title">{title}</div>
      {description && <div className="empty-state-desc">{description}</div>}
    </div>
  );
}
