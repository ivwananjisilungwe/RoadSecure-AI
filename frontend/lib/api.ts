export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Account = { id: number; username: string; role: string };
export type Detection = {
  rule_results: unknown;
  ml_prediction: string;
  anomaly_score: number;
  risk_score: number;
  severity: Severity;
  detection_result: string;
  should_alert: boolean;
};
export type Event = {
  id: number;
  event_id: string;
  event_type: string;
  source_system: string;
  username: string;
  device_id: string;
  source_ip: string;
  event_timestamp: string;
  created_at: string;
  detection_result: Detection;
  status?: string;
  severity: Severity;
  risk_score: number;
  anomaly_score: number;
  failed_login_count: number;
  requests_per_minute: number;
  data_transfer_mb: number;
  outside_working_hours: boolean;
  unknown_device: boolean;
  unusual_location: boolean;
  privileged_action: boolean;
  sensitive_record_access: boolean;
  sensitive_records_accessed: number;
};
export type Alert = {
  id: number;
  event_id: number;
  severity: Severity;
  status: string;
  created_at: string;
  event: Event;
};
export type Incident = {
  id: number;
  alert_id: number;
  title: string;
  priority: Severity;
  assigned_to: number | null;
  status: "OPEN" | "INVESTIGATING" | "RESOLVED" | "CLOSED";
  resolution: string | null;
  created_at: string;
  updated_at: string;
  history?: { id: number; action: string; detail: string; username: string; created_at: string }[];
};
export type Summary = {
  total_events: number;
  total_alerts: number;
  critical_alerts: number;
  open_incidents: number;
  resolved_incidents: number;
  anomalous_events: number;
  events_over_time: { date: string; count: number }[];
  severity_distribution: Record<string, number>;
  events_by_source: Record<string, number>;
  rule_frequencies: Record<string, number>;
  detection_methods: Record<string, number>;
  recent_events: Event[];
  recent_alerts: Alert[];
  incidents_by_status?: Record<string, number>;
  alerts_by_source?: Record<string, number>;
  alert_severity_distribution?: Record<string, number>;
};
export type Metrics = {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  false_positive_rate: number;
  true_positives: number;
  true_negatives: number;
  false_positives: number;
  false_negatives: number;
  mean_processing_ms: number;
  median_processing_ms: number;
  p95_processing_ms: number;
};
export type Evaluation = {
  model: { version: string; feature_schema: string[]; decision_threshold: number; training_timestamp: string };
  datasets: Record<"train" | "validation" | "test", { count: number; anomalies: number; seed: number; fingerprint: string }>;
  experiments: Record<"rules" | "isolation_forest" | "hybrid", Metrics>;
};

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    credentials: "same-origin",
    ...init,
    headers: { ...(init?.body && { "Content-Type": "application/json" }), ...init?.headers },
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item: { loc?: string[]; msg: string }) => `${item.loc?.at(-1) ?? "Input"}: ${item.msg}`).join("; ")
      : typeof detail === "string" ? detail : `Request failed (${response.status})`;
    throw new ApiError(response.status, message);
  }
  return data as T;
}

export const write = (method: "POST" | "PATCH", body?: object): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const title = (value: string | null | undefined) => value
  ? value.replace(/([a-z])([A-Z])/g, "$1 $2").replaceAll(/[_-]/g, " ").toLowerCase().replace(/^\w/, (letter) => letter.toUpperCase())
  : "—";

export const date = (value?: string | null) => value
  ? new Intl.DateTimeFormat("en-ZM", { timeZone: "Africa/Lusaka", dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
  : "—";

export const severities: Severity[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
