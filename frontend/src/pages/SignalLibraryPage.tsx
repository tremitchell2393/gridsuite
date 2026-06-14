/**
 * Signal Library page.
 *
 * Maps to "Signal Library" in the architecture doc's MVP screen list:
 * browsable list of active signals, filterable by category.
 *
 * At MVP this is intentionally simple — a flat list from
 * GET /signals/library. As the signal count grows (per the "constantly
 * fishing for new signals" differentiator), this page is where
 * category filtering, search, and per-signal documentation
 * (what it measures, which lanes it covers, update frequency) would
 * be added — each addition driven by adapters registered in
 * app/ingestion/adapters/__init__.py on the backend.
 */
import { useState } from "react";
import { useSignalLibrary } from "@/hooks/useApi";
import { EmptyState, Panel } from "@/components/Dashboard";

// Human-readable descriptions for known signals. New signals (from new
// adapters) appear automatically even without an entry here — they
// just show without a description until one is added.
const SIGNAL_DESCRIPTIONS: Record<string, string> = {
  customs_velocity_index: "Customs filing volume relative to 30-day average — a leading demand indicator by lane.",
  port_dwell_time: "Average vessel dwell time at port, in days — a congestion signal.",
};

export function SignalLibraryPage() {
  const { data: signals, isLoading } = useSignalLibrary();
  const [search, setSearch] = useState("");

  const filtered = (signals ?? []).filter((s) => s.toLowerCase().includes(search.toLowerCase()));

  return (
    <>
      <div className="page-header">
        <h1>Signal Library</h1>
        <p>All signals currently active in GridSuite's data layer.</p>
      </div>

      <Panel
        title="Active Signals"
        action={
          <input
            type="text"
            placeholder="Search signals..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: "var(--shell-3)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "5px 10px",
              fontSize: 12,
              color: "var(--text-1)",
              outline: "none",
            }}
          />
        }
      >
        {isLoading ? (
          <EmptyState title="Loading…" />
        ) : filtered.length === 0 ? (
          <EmptyState
            title="No signals found"
            description="Signals appear here once ingestion adapters have run at least once."
          />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Signal ID</th>
                <th style={{ textAlign: "left" }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((signalId) => (
                <tr key={signalId}>
                  <td className="td-lane">{signalId}</td>
                  <td className="text-2" style={{ textAlign: "left" }}>
                    {SIGNAL_DESCRIPTIONS[signalId] ?? "—"}
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
