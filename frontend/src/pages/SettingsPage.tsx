/**
 * Settings page.
 *
 * Maps to "Settings" in the architecture doc's MVP screen list: org
 * management, API keys, ecosystem data agreement status, billing.
 *
 * MVP scope here covers lane watchlist management (the lane_limit
 * enforcement defined on the backend's Subscription model is surfaced
 * directly — adding a lane beyond the plan limit shows the 403 message
 * from the API). API keys, ecosystem agreements, and billing are
 * stubbed as "coming soon" sections pending Stripe integration.
 */
import { useState } from "react";
import { useAddWatchedLane, useRemoveWatchedLane, useWatchedLanes } from "@/hooks/useApi";
import { EmptyState, Panel } from "@/components/Dashboard";

export function SettingsPage() {
  const { data: lanes, isLoading } = useWatchedLanes();
  const addLane = useAddWatchedLane();
  const removeLane = useRemoveWatchedLane();

  const [newLane, setNewLane] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newLane.trim()) return;
    setError(null);

    addLane.mutate(
      { laneId: newLane.trim().toUpperCase() },
      {
        onSuccess: () => setNewLane(""),
        onError: (err: any) => {
          setError(err?.response?.data?.detail ?? "Failed to add lane");
        },
      }
    );
  }

  return (
    <>
      <div className="page-header">
        <h1>Settings</h1>
        <p>Manage your lane watchlist, organization, and integrations.</p>
      </div>

      <Panel title="Lane Watchlist">
        <form onSubmit={handleAdd} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <input
            type="text"
            placeholder="e.g. SHSE-LAX"
            value={newLane}
            onChange={(e) => setNewLane(e.target.value)}
            style={{
              flex: 1,
              background: "var(--shell-3)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "8px 12px",
              color: "var(--text-1)",
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={addLane.isPending}
            style={{
              background: "var(--teal)",
              color: "#0A0A0A",
              fontWeight: 700,
              fontSize: 13,
              padding: "8px 18px",
              border: "none",
              borderRadius: 6,
            }}
          >
            {addLane.isPending ? "Adding…" : "Add Lane"}
          </button>
        </form>

        {error && (
          <div style={{ color: "var(--down)", fontSize: 12, marginBottom: 16 }}>{error}</div>
        )}

        {isLoading ? (
          <EmptyState title="Loading…" />
        ) : !lanes || lanes.length === 0 ? (
          <EmptyState title="No lanes watched yet" description="Add a lane above to start tracking it." />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Lane ID</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lanes.map((lane) => (
                <tr key={lane.lane_id}>
                  <td className="td-lane">{lane.lane_id}</td>
                  <td>
                    <button
                      onClick={() => removeLane.mutate(lane.lane_id)}
                      style={{
                        background: "none",
                        border: "1px solid var(--border)",
                        color: "var(--text-3)",
                        fontSize: 11,
                        padding: "4px 10px",
                        borderRadius: 4,
                      }}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>

      <Panel title="API & Integrations">
        <EmptyState
          title="Coming soon"
          description="API key management, ecosystem data agreement status, and billing will appear here once Stripe integration is complete."
        />
      </Panel>
    </>
  );
}
