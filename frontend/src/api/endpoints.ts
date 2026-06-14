/**
 * Typed API endpoint functions — one function per backend route.
 *
 * These are the functions React Query hooks (src/hooks/) call.
 * Keeping them separate from the hooks means the request/response
 * shapes are defined in one place regardless of how many components
 * end up using a given endpoint.
 */
import { apiClient } from "./client";
import type {
  AlertRule,
  Forecast,
  LaneForecastSummary,
  LoginResponse,
  SignalListResponse,
  User,
  WatchedLane,
} from "@/types/api";

// ── Auth ──
export async function login(email: string, password: string): Promise<LoginResponse> {
  const params = new URLSearchParams();
  params.append("username", email);
  params.append("password", password);

  const { data } = await apiClient.post<LoginResponse>("/auth/login", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function register(payload: {
  email: string;
  password: string;
  full_name?: string;
  organization_name: string;
}): Promise<User> {
  const { data } = await apiClient.post<User>("/auth/register", payload);
  return data;
}

// ── Signals ──
export async function getSignals(params: {
  entity_type: string;
  entity_id: string;
  signal_id?: string;
  days?: number;
}): Promise<SignalListResponse> {
  const { data } = await apiClient.get<SignalListResponse>("/signals", { params });
  return data;
}

export async function getSignalLibrary(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>("/signals/library");
  return data;
}

// ── Forecasts ──
export async function getLaneForecasts(
  laneId: string,
  horizonDays?: number
): Promise<Forecast[]> {
  const { data } = await apiClient.get<Forecast[]>(`/forecasts/lane/${laneId}`, {
    params: horizonDays ? { horizon_days: horizonDays } : {},
  });
  return data;
}

export async function getDashboardSummary(): Promise<LaneForecastSummary[]> {
  const { data } = await apiClient.get<LaneForecastSummary[]>("/forecasts/dashboard");
  return data;
}

// ── Lanes ──
export async function getWatchedLanes(): Promise<WatchedLane[]> {
  const { data } = await apiClient.get<WatchedLane[]>("/lanes");
  return data;
}

export async function addWatchedLane(laneId: string, label?: string): Promise<WatchedLane> {
  const { data } = await apiClient.post<WatchedLane>("/lanes", { lane_id: laneId, label });
  return data;
}

export async function removeWatchedLane(laneId: string): Promise<void> {
  await apiClient.delete(`/lanes/${laneId}`);
}

// ── Alerts ──
export async function getAlertRules(): Promise<AlertRule[]> {
  const { data } = await apiClient.get<AlertRule[]>("/alerts");
  return data;
}

export async function createAlertRule(
  payload: Omit<AlertRule, "id" | "is_active">
): Promise<AlertRule> {
  const { data } = await apiClient.post<AlertRule>("/alerts", payload);
  return data;
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  await apiClient.delete(`/alerts/${ruleId}`);
}
