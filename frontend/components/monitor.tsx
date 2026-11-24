"use client";

import { Activity, ArrowUpRight, CircleAlert, FilePlus2, RefreshCw, ScanLine } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api, date, severities, title, write, type Alert, type Event, type Incident } from "../lib/api";
import { useApi, useWrite } from "./query";
import { Badge, Button, DataTable, DetailList, Empty, ErrorState, Loading, Pager, Panel, SearchInput, Select, SeveritySelect } from "./ui";

export const sourceSystems = ["vehicle_registration", "driver_licensing", "vehicle_inspection", "transport_payments", "administration", "network_infrastructure"];
export const eventTypes = ["authentication", "record_access", "data_transfer", "privileged_action", "device_activity"];
export const pageSize = 15;

export function EventTable({ events }: { events: Event[] }) {
  if (!events.length) return <Empty>No events match this view.</Empty>;
  return <DataTable headers={["Event / time", "Identity", "Source / activity", "Detection", "Severity", "Risk"]}>
    {events.map((event) => <tr key={event.id}>
      <td><Link className="table-link" href={`/events/${event.id}`}>#{event.id}<ArrowUpRight size={13} /></Link><small>{date(event.event_timestamp)}</small></td>
      <td><strong>{event.username}</strong><small>{event.device_id}</small></td>
      <td>{title(event.source_system)}<small>{title(event.event_type)}</small></td>
      <td><Badge value={event.detection_result?.detection_result} tone={event.detection_result?.detection_result === "normal" ? "low" : "neutral"} /></td>
      <td><Badge value={event.severity} /></td><td className="mono">{event.risk_score} / 100</td>
    </tr>)}
  </DataTable>;
}

export function Events() {
  const summary = useApi<{ events_by_source: Record<string, number> }>("/dashboard");
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [source, setSource] = useState("");
  const [eventType, setEventType] = useState("");
  const [detection, setDetection] = useState("");
  const [page, setPage] = useState(0);
  const params = new URLSearchParams({ limit: String(pageSize), offset: String(page * pageSize) });
  if (search.trim()) params.set("q", search.trim());
  if (severity) params.set("severity", severity);
  if (source) params.set("source_system", source);
  if (eventType) params.set("event_type", eventType);
  if (detection) params.set("detection_result", detection);
  const events = useApi<Event[]>(`/events?${params}`, { interval: 10000 });
  const sources = summary.data ? Object.keys(summary.data.events_by_source).sort() : [];
  const filter = (setValue: (value: string) => void) => (value: string) => { setValue(value); setPage(0); };

  return <Panel title="Monitored activity" icon={Activity} meta={<Button type="button" disabled={events.isFetching} onClick={() => { void events.refetch(); }}><RefreshCw size={15} />Refresh</Button>}>
    <div className="filters">
      <SearchInput label="Search events" value={search} onChange={filter(setSearch)} />
      <SeveritySelect value={severity} onChange={filter(setSeverity)} />
      <Select label="Source system" value={source} options={sources} onChange={filter(setSource)} />
      <Select label="Event type" value={eventType} options={eventTypes} onChange={filter(setEventType)} />
      <Select label="Detection" value={detection} options={["normal", "suspicious"]} onChange={filter(setDetection)} />
    </div>
    {events.isPending ? <Loading /> : events.error ? <ErrorState error={events.error} retry={() => { void events.refetch(); }} /> : <>
      <EventTable events={events.data} /><Pager page={page} size={pageSize} currentCount={events.data.length} setPage={setPage} />
    </>}
  </Panel>;
}

export function AlertTable({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) return <Empty>No alerts match this view.</Empty>;
  return <DataTable headers={["Alert / time", "Source / activity", "Severity", "Risk", "Status"]}>
    {alerts.map((alert) => <tr key={alert.id}>
      <td><Link className="table-link" href={`/alerts/${alert.id}`}>Alert #{alert.id}<ArrowUpRight size={13} /></Link><small>{date(alert.created_at)}</small></td>
      <td>{title(alert.event.source_system)}<small>{title(alert.event.event_type)}</small></td>
      <td><Badge value={alert.severity} /></td><td className="mono">{alert.event.risk_score} / 100</td>
      <td><Badge value={alert.status} /></td>
    </tr>)}
  </DataTable>;
}

export function Alerts() {
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const params = new URLSearchParams({ limit: String(pageSize), offset: String(page * pageSize) });
  if (search.trim()) params.set("q", search.trim());
  if (severity) params.set("severity", severity);
  if (status) params.set("status", status);
  const alerts = useApi<Alert[]>(`/alerts?${params}`, { interval: 10000 });

  return <Panel title="Alert queue" icon={CircleAlert}>
    <div className="filters">
      <SearchInput label="Search alerts" value={search} onChange={(value) => { setSearch(value); setPage(0); }} />
      <SeveritySelect value={severity} onChange={(value) => { setSeverity(value); setPage(0); }} />
      <Select label="Status" options={["NEW", "ACKNOWLEDGED", "DISMISSED"]} value={status} onChange={(value) => { setStatus(value); setPage(0); }} />
    </div>
    {alerts.isPending ? <Loading /> : alerts.error ? <ErrorState error={alerts.error} retry={() => { void alerts.refetch(); }} /> : <>
      <AlertTable alerts={alerts.data} /><Pager page={page} size={pageSize} currentCount={alerts.data.length} setPage={setPage} />
    </>}
  </Panel>;
}

type RuleMatch = string | { id?: string; rule_id?: string; rule?: string; name?: string; title?: string; message?: string; explanation?: string; description?: string; risk_contribution?: number };

function RuleList({ result }: { result: unknown }) {
  const value = result as RuleMatch[] | { matches?: RuleMatch[]; triggered?: RuleMatch[]; triggered_rules?: RuleMatch[] } | undefined;
  const rules = Array.isArray(value) ? value : (value?.matches ?? value?.triggered ?? value?.triggered_rules ?? []);
  if (!rules.length) return <p className="muted">No rule conditions fired.</p>;
  return <ul className="rule-list">{rules.map((rule, index) => {
    if (typeof rule === "string") return <li key={rule}>{title(rule)}</li>;
    const name = rule.title || rule.name || title(rule.rule || rule.rule_id || rule.id);
    const explanation = rule.explanation || rule.description || rule.message;
    return <li key={rule.rule_id || rule.id || rule.rule || String(index)}><strong>{name}</strong>{explanation && <span>{explanation}</span>}{rule.risk_contribution !== undefined && <small>Risk contribution {rule.risk_contribution}</small>}</li>;
  })}</ul>;
}

export function DetectionPanel({ event }: { event: Event }) {
  const result = event.detection_result;
  const score = event.risk_score ?? result.risk_score;
  const severity = event.severity ?? result.severity;
  return <Panel title="Detection analysis" icon={ScanLine} meta={<Badge value={severity} />}>
    <div className="detection-overview"><div className={`risk-gauge ${severity.toLowerCase()}`} style={{ "--score": `${score}%` } as React.CSSProperties}><div><strong>{score}</strong><span>/ 100</span></div></div>
      <DetailList items={[
        ["Hybrid decision", title(result.detection_result)],
        ["Isolation Forest", title(result.ml_prediction)],
        ["Anomaly score", Number(result.anomaly_score).toFixed(4)],
        ["Alert policy", result.should_alert ? "Alert generated" : "Monitor only"],
      ]} />
    </div>
    <h3 className="subheading">Triggered rules</h3>
    <RuleList result={result.rule_results} />
  </Panel>;
}

type EventWithAlert = Event & { alert_id?: number };

export function EventDetails({ id }: { id: string }) {
  const query = useApi<EventWithAlert>(`/events/${id}`);
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorState error={query.error} retry={() => { void query.refetch(); }} />;
  const event = query.data;
  return <div className="stack">
    <div className="split">
      <Panel title={`Event #${event.id}`} icon={Activity}><DetailList items={[
        ["Event reference", event.event_id], ["Timestamp (CAT)", date(event.event_timestamp)],
        ["Source system", title(event.source_system)], ["Activity", title(event.event_type)],
        ["Username", event.username], ["Device", event.device_id], ["Source IP", event.source_ip],
      ]} />{event.alert_id && <Button asChild><Link href={`/alerts/${event.alert_id}`}>Review related alert <ArrowUpRight size={16} /></Link></Button>}</Panel>
      <DetectionPanel event={event} />
    </div>
    <Panel title="Activity signals" icon={ScanLine}><DetailList items={[
      ["Failed logins", event.failed_login_count], ["Requests per minute", event.requests_per_minute],
      ["Data transfer", `${event.data_transfer_mb} MB`], ["Sensitive records accessed", event.sensitive_records_accessed],
      ["Outside working hours", event.outside_working_hours ? "Yes" : "No"],
      ["Unknown device", event.unknown_device ? "Yes" : "No"],
      ["Unusual location", event.unusual_location ? "Yes" : "No"],
      ["Privileged action", event.privileged_action ? "Yes" : "No"],
      ["Sensitive record access", event.sensitive_record_access ? "Yes" : "No"],
    ]} /></Panel>
  </div>;
}

type AlertWithIncident = Alert & { incident_id?: number };

export function AlertDetails({ id }: { id: string }) {
  const query = useApi<AlertWithIncident>(`/alerts/${id}`);
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorState error={query.error} retry={() => { void query.refetch(); }} />;
  return <AlertContent alert={query.data} />;
}

function AlertContent({ alert }: { alert: AlertWithIncident }) {
  const router = useRouter();
  const review = useWrite((status: string) => api(`/alerts/${alert.id}`, write("PATCH", { status })));
  const create = useWrite((form: { title: string; priority: string; assigned_to?: string }) => api<Incident>("/incidents", write("POST", { ...form, alert_id: alert.id })));
  const related = useApi<Incident[]>(`/incidents?alert_id=${alert.id}&limit=1`, { enabled: !alert.incident_id });
  const existingIncident = alert.incident_id ?? related.data?.find((incident) => incident.alert_id === alert.id)?.id;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      title: String(form.get("title")).trim(),
      priority: String(form.get("priority")),
      assigned_to: String(form.get("assignedTo")).trim() || undefined,
    }, { onSuccess: (incident) => router.push(`/incidents/${incident.id}`) });
  }

  return <div className="stack">
    <div className="split">
      <Panel title={`Alert #${alert.id}`} icon={CircleAlert} meta={<Badge value={alert.status} />}>
        <DetailList items={[
          ["Source system", title(alert.event.source_system)], ["Activity", title(alert.event.event_type)],
          ["Identity", alert.event.username], ["Observed device", alert.event.device_id], ["Created (CAT)", date(alert.created_at)],
          ["Evidence", <Link key="evidence" className="table-link" href={`/events/${alert.event_id}`}>Event #{alert.event_id}<ArrowUpRight size={13} /></Link>],
        ]} />
        <div className="actions">
          {alert.status === "NEW" && <Button type="button" disabled={review.isPending} onClick={() => review.mutate("ACKNOWLEDGED")}>Acknowledge</Button>}
          {alert.status !== "DISMISSED" && <Button type="button" disabled={review.isPending} onClick={() => review.mutate("DISMISSED")}>Dismiss alert</Button>}
        </div>
        {review.error && <ErrorState error={review.error} />}
      </Panel>
      <DetectionPanel event={alert.event} />
    </div>
    <div className="split">
      <Panel title="Incident response" icon={FilePlus2}>{existingIncident
        ? <Button asChild variant="primary"><Link href={`/incidents/${existingIncident}`}>Open incident #{existingIncident}<ArrowUpRight size={16} /></Link></Button>
        : <form className="form-stack" onSubmit={submit}>
          <label className="control">Title<input name="title" required maxLength={150} defaultValue={`Investigate ${title(alert.event.source_system).toLowerCase()} alert #${alert.id}`} /></label>
          <div className="form-row"><label className="control">Priority<select name="priority" defaultValue={alert.severity}>{severities.map((severity) => <option key={severity} value={severity}>{title(severity)}</option>)}</select></label>
            <label className="control">Assigned to<input name="assignedTo" maxLength={100} placeholder="Analyst username" /></label></div>
          {create.error && <ErrorState error={create.error} />}
          <Button variant="primary" type="submit" disabled={create.isPending}><FilePlus2 size={16} />{create.isPending ? "Creating…" : "Create incident"}</Button>
        </form>}</Panel>
      <Panel title="Investigation guidance" icon={ScanLine}>
        <ul className="rule-list"><li>Confirm the synthetic identity, activity time and device details.</li><li>Review the conditions that increased risk and compare with adjacent events from the same system.</li><li>Record findings and a resolution in the incident timeline.</li></ul>
      </Panel>
    </div>
  </div>;
}
