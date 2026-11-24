"use client";

import { Activity, ArrowUpRight, CircleAlert, ClipboardCheck, Files, FileText, FlaskConical, Play, RadioTower, ShieldAlert, Square, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { api, date, severities, title, write, type Event, type Incident } from "../lib/api";
import { DetectionPanel, eventTypes, pageSize, sourceSystems } from "./monitor";
import { useApi, useWrite } from "./query";
import { Badge, Button, DataTable, DetailList, Empty, ErrorState, Loading, Pager, Panel, SearchInput, Select } from "./ui";

const scenarios: { key: string; label: string; description: string; icon: LucideIcon }[] = [
  { key: "normal", label: "Normal activity", description: "Routine access using a known device.", icon: ShieldAlert },
  { key: "failed_login", label: "Repeated failed login attempts", description: "A synthetic account reports successive authentication failures.", icon: CircleAlert },
  { key: "unknown_device", label: "Unknown device", description: "Routine activity arrives from an unrecognized device.", icon: RadioTower },
  { key: "outside_hours", label: "Outside-hours activity", description: "A record is accessed outside regular working hours.", icon: Activity },
  { key: "large_transfer", label: "Large data transfer", description: "Unusually high synthetic transfer volume.", icon: Files },
  { key: "privileged_action", label: "Suspicious privileged action", description: "An administrator activity includes a privilege signal.", icon: ShieldAlert },
  { key: "sensitive_access", label: "Unusual sensitive-record access", description: "A session accesses an unusual volume of protected records.", icon: FileText },
  { key: "combined", label: "Combined suspicious activity", description: "Multiple risk signals appear in the same activity.", icon: FlaskConical },
];

type SimulationStatus = { running: boolean; scenario: string; source_system: string; interval_seconds: number; generated: number; error?: string };

export function Simulator() {
  const [source, setSource] = useState("");
  const [result, setResult] = useState<Event>();
  const generate = useWrite((scenario: string) => api<{ events: Event[] }>("/simulator/generate", write("POST", { scenario, count: 1, source_system: source || undefined })));
  const submit = useWrite((body: object) => api<Event>("/events", write("POST", body)));

  function generateEvent(scenario: string) {
    submit.reset();
    generate.mutate(scenario, { onSuccess: ({ events }) => setResult(events[0]) });
  }

  function manual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    generate.reset();
    const data = new FormData(event.currentTarget);
    const body: Record<string, string | number | boolean> = {};
    for (const name of ["source_system", "event_type", "username", "device_id", "source_ip"]) body[name] = String(data.get(name)).trim();
    for (const name of ["failed_login_count", "requests_per_minute", "data_transfer_mb", "sensitive_records_accessed"]) body[name] = Number(data.get(name));
    for (const name of ["outside_working_hours", "unknown_device", "unusual_location", "privileged_action", "sensitive_record_access"]) body[name] = data.has(name);
    submit.mutate(body, { onSuccess: setResult });
  }

  return <div className="stack">
    <div className="notice"><FlaskConical size={19} /><div><strong>Synthetic activity only</strong><p>Scenarios send fictional telemetry through the same detector, event storage and alert policy used elsewhere in this console.</p></div></div>
    <div className="split simulator-layout">
      <div className="stack">
        <Panel title="Generate an event" icon={RadioTower}>
          <div className="form-stack">
            <Select label="Source system" options={sourceSystems} value={source} onChange={setSource} />
            <div className="scenario-grid">{scenarios.map(({ key, label, description, icon: Icon }) => <button className="scenario" type="button" key={key} disabled={generate.isPending || submit.isPending} onClick={() => generateEvent(key)}>
              <Icon size={19} aria-hidden="true" /><span><strong>{label}</strong><small>{description}</small></span><ArrowUpRight size={14} aria-hidden="true" />
            </button>)}</div>
            {generate.error && <ErrorState error={generate.error} />}
          </div>
        </Panel>
        <Panel title="Manual event" icon={FileText}>
          <form className="form-stack" onSubmit={manual}>
            <div className="form-row">
              <label className="control">Source system<select name="source_system">{sourceSystems.map((item) => <option key={item} value={item}>{title(item)}</option>)}</select></label>
              <label className="control">Event type<select name="event_type">{eventTypes.map((item) => <option key={item} value={item}>{title(item)}</option>)}</select></label>
              <label className="control">Username<input name="username" defaultValue="demo-operator" required maxLength={80} /></label>
              <label className="control">Device identifier<input name="device_id" defaultValue="DEMO-DEVICE-01" required maxLength={80} /></label>
              <label className="control">Example IP address<input name="source_ip" defaultValue="192.0.2.25" required maxLength={45} /></label>
              <label className="control">Failed logins<input name="failed_login_count" type="number" min={0} defaultValue={0} required /></label>
              <label className="control">Requests per minute<input name="requests_per_minute" type="number" min={0} defaultValue={12} required /></label>
              <label className="control">Data transfer (MB)<input name="data_transfer_mb" type="number" min={0} step="any" defaultValue={3} required /></label>
              <label className="control">Sensitive records accessed<input name="sensitive_records_accessed" type="number" min={0} defaultValue={0} required /></label>
            </div>
            <div className="check-grid">{["outside_working_hours", "unknown_device", "unusual_location", "privileged_action", "sensitive_record_access"].map((name) => <label key={name}><input name={name} type="checkbox" />{title(name)}</label>)}</div>
            {submit.error && <ErrorState error={submit.error} />}
            <Button variant="primary" type="submit" disabled={generate.isPending || submit.isPending}>{submit.isPending ? "Submitting…" : "Submit synthetic event"}</Button>
          </form>
        </Panel>
      </div>
      <div className="stack" aria-live="polite">
        {result ? <>
          <DetectionPanel event={result} />
          <div className="actions"><Button asChild><Link href={`/events/${result.id}`}>Open event #{result.id}<ArrowUpRight size={16} /></Link></Button>{result.detection_result.should_alert && <Button asChild><Link href="/alerts">Review alerts<ArrowUpRight size={16} /></Link></Button>}</div>
        </> : <Panel title="Detection results" icon={Activity}><Empty>Generate an event to see the detector’s decision and risk score.</Empty></Panel>}
        <AutomaticSimulator />
      </div>
    </div>
  </div>;
}

function AutomaticSimulator() {
  const status = useApi<SimulationStatus>("/simulator/status", { interval: 4000 });
  const control = useWrite(({ action, body }: { action: "start" | "stop"; body?: object }) => api<SimulationStatus>(`/simulator/${action}`, write("POST", body)));

  function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    control.mutate({ action: "start", body: { scenario: String(form.get("scenario")), interval_seconds: Number(form.get("interval")) } });
  }

  return <Panel title="Automatic monitoring" icon={Activity} meta={status.data && <Badge value={status.data.running ? "Running" : "Stopped"} tone={status.data.running ? "low" : "neutral"} />}>
    {status.isPending ? <Loading /> : status.error ? <ErrorState error={status.error} retry={() => { void status.refetch(); }} /> : <>
      {status.data.error && <ErrorState error={new Error(status.data.error)} />}
      {status.data.running ? <div className="form-stack">
        <DetailList items={[["Scenario", title(status.data.scenario)], ["Generated events", status.data.generated], ["Interval", `${status.data.interval_seconds} seconds`]]} />
        <Button type="button" disabled={control.isPending} onClick={() => control.mutate({ action: "stop" })}><Square size={15} />Stop monitoring</Button>
      </div> : <form className="form-stack" onSubmit={start}>
        <label className="control">Scenario<select name="scenario">{scenarios.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label className="control">Interval (seconds)<input type="number" name="interval" defaultValue={5} min={2} max={60} required /></label>
        <Button type="submit" disabled={control.isPending}><Play size={15} />Start monitoring</Button>
      </form>}
      {control.error && <ErrorState error={control.error} />}
    </>}
  </Panel>;
}

const statuses = ["OPEN", "INVESTIGATING", "RESOLVED", "CLOSED"];
export function Incidents() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const params = new URLSearchParams({ limit: String(pageSize), offset: String(page * pageSize) });
  if (search.trim()) params.set("q", search.trim());
  if (status) params.set("status", status);
  const query = useApi<Incident[]>(`/incidents?${params}`, { interval: 10000 });
  return <Panel title="Incident register" icon={Files} meta={<Button asChild><Link href="/alerts">Review alerts<ArrowUpRight size={15} /></Link></Button>}>
    <div className="filters">
      <SearchInput label="Search incidents" value={search} onChange={(value) => { setSearch(value); setPage(0); }} />
      <Select label="Status" value={status} options={statuses} onChange={(value) => { setStatus(value); setPage(0); }} />
    </div>
    {query.isPending ? <Loading /> : query.error ? <ErrorState error={query.error} retry={() => { void query.refetch(); }} /> : <>
      {query.data.length ? <DataTable headers={["Incident", "Priority", "Status", "Assigned to", "Last updated"]}>{query.data.map((incident) => <tr key={incident.id}>
        <td><Link className="table-link" href={`/incidents/${incident.id}`}>{incident.title}<ArrowUpRight size={13} /></Link><small>#{incident.id}</small></td>
        <td><Badge value={incident.priority} /></td><td><Badge value={incident.status} /></td>
        <td>{incident.assigned_to || "Unassigned"}</td><td className="mono">{date(incident.updated_at)}</td>
      </tr>)}</DataTable> : <Empty>No incidents match this view. Create an incident from an alert.</Empty>}
      <Pager page={page} size={pageSize} currentCount={query.data.length} setPage={setPage} />
    </>}
  </Panel>;
}

export function IncidentDetails({ id }: { id: string }) {
  const query = useApi<Incident>(`/incidents/${id}`);
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorState error={query.error} retry={() => { void query.refetch(); }} />;
  return <IncidentContent incident={query.data} />;
}

function IncidentContent({ incident }: { incident: Incident }) {
  const endpoint = `/incidents/${incident.id}`;
  const update = useWrite((body: object) => api<Incident>(endpoint, write("PATCH", body)));
  const addNote = useWrite((note: string) => api<Incident>(`${endpoint}/notes`, write("POST", { note })));

  function assignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    update.mutate({ priority: form.get("priority"), assigned_to: String(form.get("assignedTo")).trim() || null });
  }

  function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const note = String(new FormData(form).get("note")).trim();
    if (note) addNote.mutate(note, { onSuccess: () => form.reset() });
  }

  function resolve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const resolution = String(new FormData(event.currentTarget).get("resolution")).trim();
    if (resolution) update.mutate({ status: "RESOLVED", resolution });
  }

  return <div className="stack">
    <div className="split">
      <div className="stack">
        <Panel title={incident.title} icon={Files} meta={<Badge value={incident.status} />}>
          <DetailList items={[
            ["Incident", `#${incident.id}`], ["Priority", <Badge key="priority" value={incident.priority} />],
            ["Assigned to", incident.assigned_to || "Unassigned"],
            ["Alert evidence", <Link key="alert" className="table-link" href={`/alerts/${incident.alert_id}`}>Alert #{incident.alert_id}<ArrowUpRight size={13} /></Link>],
            ["Created (CAT)", date(incident.created_at)], ["Updated (CAT)", date(incident.updated_at)],
            ["Resolution", incident.resolution],
          ]} />
        </Panel>
        <Panel title="Incident workflow" icon={ClipboardCheck}>
          <ol className="lifecycle">{statuses.map((status) => <li key={status} aria-current={status === incident.status ? "step" : undefined}>{title(status)}</li>)}</ol>
          {incident.status === "OPEN" && <Button type="button" variant="primary" disabled={update.isPending} onClick={() => update.mutate({ status: "INVESTIGATING" })}>Start investigation</Button>}
          {incident.status === "INVESTIGATING" && <form className="form-stack" onSubmit={resolve}><label className="control">Resolution<textarea name="resolution" required maxLength={4000} rows={3} /></label><Button type="submit" variant="primary" disabled={update.isPending}>Resolve incident</Button></form>}
          {incident.status === "RESOLVED" && <Button type="button" variant="primary" disabled={update.isPending} onClick={() => update.mutate({ status: "CLOSED" })}>Close incident</Button>}
          {incident.status === "CLOSED" && <p className="muted">Incident closed.</p>}
          {update.error && <ErrorState error={update.error} />}
        </Panel>
        {incident.status !== "CLOSED" && <Panel title="Assignment and priority" icon={Files}>
          <form className="form-stack" key={`${incident.priority}/${incident.assigned_to}`} onSubmit={assignment}>
            <div className="form-row"><label className="control">Priority<select name="priority" defaultValue={incident.priority}>{severities.map((priority) => <option key={priority} value={priority}>{title(priority)}</option>)}</select></label><label className="control">Assigned to<input name="assignedTo" defaultValue={incident.assigned_to ?? ""} maxLength={100} /></label></div>
            <Button type="submit" disabled={update.isPending}>Save assignment</Button>
          </form>
        </Panel>}
      </div>
      <div className="stack">
        <Panel title="Investigation timeline" icon={Activity}>
          {incident.history?.length ? <ol className="timeline">{incident.history.map((item) => <li key={item.id}><div><strong>{title(item.action)}</strong><small>{date(item.created_at)}</small></div><p>{item.detail}</p><span>{item.username}</span></li>)}</ol> : <Empty>No recorded actions yet.</Empty>}
        </Panel>
        {incident.status !== "CLOSED" && <Panel title="Investigation notes" icon={FileText}>
          <form className="form-stack" onSubmit={add}><label className="control">Investigation note<textarea name="note" required maxLength={4000} rows={4} /></label>{addNote.error && <ErrorState error={addNote.error} />}<Button type="submit" disabled={addNote.isPending}>Add note</Button></form>
        </Panel>}
      </div>
    </div>
  </div>;
}
