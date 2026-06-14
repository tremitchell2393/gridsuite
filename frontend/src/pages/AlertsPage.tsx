/**
 * Alerts page.
 *
 * Maps to "Alerts" in the architecture doc's MVP screen list:
 * configuration UI + alert history.
 *
 * Channel availability mirrors the backend's tier gating
 * (app/api/v1/routes/alerts.py): email is available to everyone,
 * Slack/webhook require Pro+. The form disables those options for
 * Core-tier orgs — though the backend is the actual enforcement point
 * (this is just UX, not the security boundary).
 */
import { useState } from "react";
import { useAlertRules, useCreateAlertRule, useDeleteAlertRule, useWatchedLanes } from "@/hooks/useApi";
import { EmptyState, Panel } from "@/components/Dashboard";
import type { AlertChannel, AlertCondition } from "@/types/api";

const CONDITIONS: { value: AlertCondition; label: string }[] = [
  { value: "forecast_change_above", label: "Forecast change exceeds threshold" },
  { value: "signal_threshold", label: "Signal value exceeds threshold" },
  { value: "confidence_above", label: "Forecast confidence exceeds threshold" },
];

const CHANNELS: { value: AlertChannel; label: string }[] = [
  { value: "email", label: "Email" },
  { value: "slack", label: "Slack (Pro+)" },
  { value: "webhook", label: "Webhook (Pro+)" },
];

export function AlertsPage() {
  const { data: rules, isLoading } = useAlertRules();
  const { data: lanes } = useWatchedLanes();
  const createRule = useCreateAlertRule();
  const deleteRule = useDeleteAlertRule();

  const [form, setForm] = useState({
    lane_id: "",
    signal_or_forecast_type: "rate_change_pct",
    condition: "forecast_change_above" as AlertCondition,
    threshold: 10,
    channel: "email" as AlertChannel,
    destination: "",
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.lane_id || !form.destination) return;
    createRule.mutate(form, {
      onSuccess: () => setForm((f) => ({ ...f, destination: "" })),
    });
  }

  return (
    <>
      <div className="page-header">
        <h1>Alerts</h1>
        <p>Get notified when signals or forecasts cross thresholds you care about.</p>
      </div>

      <Panel title="Create Alert Rule">
        <form onSubmit={handleSubmit} className="alert-form">
          <div className="alert-form-row">
            <label>
              Lane
              <select
                value={form.lane_id}
                onChange={(e) => setForm((f) => ({ ...f, lane_id: e.target.value }))}
                required
              >
                <option value="">Select a watched lane…</option>
                {lanes?.map((l) => (
                  <option key={l.lane_id} value={l.lane_id}>
                    {l.lane_id}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Condition
              <select
                value={form.condition}
                onChange={(e) => setForm((f) => ({ ...f, condition: e.target.value as AlertCondition }))}
              >
                {CONDITIONS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Threshold
              <input
                type="number"
                value={form.threshold}
                onChange={(e) => setForm((f) => ({ ...f, threshold: parseFloat(e.target.value) }))}
              />
            </label>
          </div>

          <div className="alert-form-row">
            <label>
              Channel
              <select
                value={form.channel}
                onChange={(e) => setForm((f) => ({ ...f, channel: e.target.value as AlertChannel }))}
              >
                {CHANNELS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>

            <label style={{ flex: 2 }}>
              Destination
              <input
                type="text"
                placeholder={form.channel === "email" ? "you@company.com" : "https://hooks.slack.com/..."}
                value={form.destination}
                onChange={(e) => setForm((f) => ({ ...f, destination: e.target.value }))}
                required
              />
            </label>

            <button type="submit" className="btn-create" disabled={createRule.isPending}>
              {createRule.isPending ? "Creating…" : "Create Alert"}
            </button>
          </div>
        </form>
      </Panel>

      <Panel title="Active Alert Rules">
        {isLoading ? (
          <EmptyState title="Loading…" />
        ) : !rules || rules.length === 0 ? (
          <EmptyState title="No alert rules configured yet" />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Lane</th>
                <th>Metric</th>
                <th>Condition</th>
                <th>Channel</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td className="td-lane">{rule.lane_id}</td>
                  <td className="td-price">{rule.signal_or_forecast_type}</td>
                  <td className="td-price">
                    {rule.condition.replace(/_/g, " ")} {rule.threshold}
                  </td>
                  <td className="td-price">{rule.channel}</td>
                  <td>
                    <button className="btn-delete" onClick={() => deleteRule.mutate(rule.id)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <style>{`
        .alert-form { display: flex; flex-direction: column; gap: 12px; }
        .alert-form-row { display: flex; gap: 12px; align-items: flex-end; }
        .alert-form label {
          display: flex; flex-direction: column; gap: 6px;
          font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
          text-transform: uppercase; color: var(--text-3); flex: 1;
        }
        .alert-form input, .alert-form select {
          background: var(--shell-3); border: 1px solid var(--border);
          border-radius: 6px; padding: 8px 10px; color: var(--text-1);
          font-size: 13px; font-weight: 400; text-transform: none;
          letter-spacing: normal; outline: none;
        }
        .alert-form input:focus, .alert-form select:focus { border-color: var(--teal); }
        .btn-create {
          background: var(--teal); color: #0A0A0A; font-weight: 700;
          font-size: 13px; padding: 9px 18px; border: none; border-radius: 6px;
          white-space: nowrap; transition: background 0.15s;
        }
        .btn-create:hover { background: #00e0ad; }
        .btn-create:disabled { opacity: 0.6; cursor: not-allowed; }
        .btn-delete {
          background: none; border: 1px solid var(--border); color: var(--text-3);
          font-size: 11px; padding: 4px 10px; border-radius: 4px; transition: all 0.15s;
        }
        .btn-delete:hover { border-color: var(--down); color: var(--down); }
      `}</style>
    </>
  );
}
