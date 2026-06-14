/**
 * Types mirroring backend Pydantic schemas (app/schemas/).
 *
 * Kept hand-written and minimal for MVP. Once the API stabilizes,
 * these can be generated automatically from the OpenAPI spec
 * (FastAPI exposes this at /v1/openapi.json) using a tool like
 * openapi-typescript — at that point this file becomes generated
 * output rather than hand-maintained.
 */

export interface SignalRecord {
  signal_id: string;
  entity_type: string;
  entity_id: string;
  timestamp: string; // ISO datetime
  value: number;
  unit: string;
  source: string;
  confidence: number;
  metadata: Record<string, unknown>;
}

export interface SignalListResponse {
  entity_type: string;
  entity_id: string;
  signals: SignalRecord[];
}

export interface SignalAttribution {
  signal_id: string;
  value?: number | null;
  baseline_30d?: number | null;
  contribution?: number | null;
  note?: string | null;
}

export interface Forecast {
  forecast_type: string;
  entity_type: string;
  entity_id: string;
  generated_at: string;
  target_date: string;
  horizon_days: number;
  predicted_value: number;
  unit: string;
  lower_bound: number | null;
  upper_bound: number | null;
  confidence: number;
  model_version: string;
  signal_attribution: SignalAttribution[];
}

export interface LaneForecastSummary {
  lane_id: string;
  current_value: number | null;
  current_unit: string | null;
  forecast_30d: Forecast | null;
}

export interface WatchedLane {
  lane_id: string;
  label: string | null;
}

export type AlertChannel = "email" | "slack" | "webhook";
export type AlertCondition =
  | "forecast_change_above"
  | "signal_threshold"
  | "confidence_above";

export interface AlertRule {
  id: string;
  lane_id: string;
  signal_or_forecast_type: string;
  condition: AlertCondition;
  threshold: number;
  channel: AlertChannel;
  destination: string;
  is_active: boolean;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_org_admin: boolean;
  organization_id: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
