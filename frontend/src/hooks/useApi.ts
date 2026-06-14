/**
 * React Query hooks.
 *
 * Each hook wraps one or more endpoint functions (src/api/endpoints.ts)
 * with caching/polling behavior appropriate to that data:
 *   - Dashboard summary & signals: short staleTime + polling, since
 *     these should feel "live" per the brand's real-time positioning.
 *   - Lanes, alerts: longer staleTime, invalidated on mutation instead
 *     of polled (they change rarely, only via user action).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addWatchedLane,
  createAlertRule,
  deleteAlertRule,
  getAlertRules,
  getDashboardSummary,
  getLaneForecasts,
  getSignalLibrary,
  getSignals,
  getWatchedLanes,
  removeWatchedLane,
} from "@/api/endpoints";
import type { AlertRule } from "@/types/api";

const POLL_INTERVAL_MS = 60_000; // 1 minute — matches "live signals" framing

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useLaneForecasts(laneId: string, horizonDays?: number) {
  return useQuery({
    queryKey: ["lane-forecasts", laneId, horizonDays],
    queryFn: () => getLaneForecasts(laneId, horizonDays),
    enabled: !!laneId,
  });
}

export function useSignals(entityType: string, entityId: string, signalId?: string, days = 30) {
  return useQuery({
    queryKey: ["signals", entityType, entityId, signalId, days],
    queryFn: () => getSignals({ entity_type: entityType, entity_id: entityId, signal_id: signalId, days }),
    enabled: !!entityType && !!entityId,
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useSignalLibrary() {
  return useQuery({
    queryKey: ["signal-library"],
    queryFn: getSignalLibrary,
    staleTime: 5 * 60_000, // signal library changes rarely
  });
}

export function useWatchedLanes() {
  return useQuery({
    queryKey: ["watched-lanes"],
    queryFn: getWatchedLanes,
  });
}

export function useAddWatchedLane() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ laneId, label }: { laneId: string; label?: string }) =>
      addWatchedLane(laneId, label),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watched-lanes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });
}

export function useRemoveWatchedLane() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (laneId: string) => removeWatchedLane(laneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watched-lanes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });
}

export function useAlertRules() {
  return useQuery({
    queryKey: ["alert-rules"],
    queryFn: getAlertRules,
  });
}

export function useCreateAlertRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<AlertRule, "id" | "is_active">) => createAlertRule(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] }),
  });
}

export function useDeleteAlertRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => deleteAlertRule(ruleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] }),
  });
}
