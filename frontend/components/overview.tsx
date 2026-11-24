"use client";

import { BarChart3, BrainCircuit, Gauge, Settings, ShieldCheck } from "lucide-react";
import { api, date, title, type Evaluation as EvaluationData, type Summary } from "../lib/api";
import { useApi } from "./query";
import { Badge, DataTable, DetailList, Distribution, Empty, ErrorState, Loading, Panel } from "./ui";
import { AlertTable, EventTable } from "./monitor";

export function Dashboard() {
  const query = useApi<Summary>("/dashboard", { interval: 5000 });
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorState error={query.error} retry={() => { void query.refetch(); }} />;
  const s = query.data;
  const cards = [["Events processed", s.total_events], ["Security alerts", s.total_alerts], ["Critical alerts", s.critical_alerts], ["Open incidents", s.open_incidents]];
  return <div className="stack"><div className="metric-grid">{cards.map(([label, value]) => <div className="metric" key={String(label)}><span>{label}</span><strong>{value}</strong></div>)}</div>
    <div className="split"><Panel title="Severity distribution" icon={Gauge}><Distribution data={Object.entries(s.severity_distribution)} colors /></Panel><Panel title="Detection methods" icon={ShieldCheck}><Distribution data={Object.entries(s.detection_methods)} /></Panel></div>
    <div className="split"><Panel title="Recent events" icon={BarChart3}>{s.recent_events.length ? <EventTable events={s.recent_events} /> : <Empty>No events yet. Use Simulator to generate synthetic activity.</Empty>}</Panel><Panel title="Recent alerts" icon={ShieldCheck}>{s.recent_alerts.length ? <AlertTable alerts={s.recent_alerts} /> : <Empty>No alerts yet.</Empty>}</Panel></div>
  </div>;
}

export function Reports() {
  const query = useApi<Summary>("/reports/summary");
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorState error={query.error} retry={() => { void query.refetch(); }} />;
  const s = query.data;
  return <div className="stack"><div className="split"><Panel title="Events by source" icon={BarChart3}><Distribution data={Object.entries(s.events_by_source)} /></Panel><Panel title="Rules triggered" icon={ShieldCheck}><Distribution data={Object.entries(s.rule_frequencies)} /></Panel></div><Panel title="Incidents by status" icon={Gauge}><Distribution data={Object.entries(s.incidents_by_status || {})} colors /></Panel></div>;
}

export function Evaluation() {
  const query = useApi<EvaluationData>("/evaluation");
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorState error={query.error} retry={() => { void query.refetch(); }} />;
  const data = query.data;
  return <div className="stack"><div className="notice"><BrainCircuit size={19} /><div><strong>Measured on synthetic data</strong><p>These metrics describe the reproducible held-out experiment and do not establish real-world transport-system performance.</p></div></div><Panel title="Model configuration" icon={BrainCircuit}><DetailList items={[["Version", data.model.version], ["Decision threshold", data.model.decision_threshold.toFixed(4)], ["Training time", date(data.model.training_timestamp)], ["Features", data.model.feature_schema.map(title).join(", ")]]} /></Panel><Panel title="Strategy comparison" icon={BarChart3}><DataTable headers={["Strategy", "Accuracy", "Precision", "Recall", "F1", "False-positive rate"]}>{Object.entries(data.experiments).map(([name, metric]) => <tr key={name}><td><strong>{title(name)}</strong></td><td>{(metric.accuracy * 100).toFixed(2)}%</td><td>{(metric.precision * 100).toFixed(2)}%</td><td>{(metric.recall * 100).toFixed(2)}%</td><td>{(metric.f1_score * 100).toFixed(2)}%</td><td>{(metric.false_positive_rate * 100).toFixed(2)}%</td></tr>)}</DataTable></Panel></div>;
}

export function SettingsPage({ account }: { account?: { username: string; role: string } }) {
  const query = useApi<{ user: { username: string; role: string }; model: { version: string }; settings: Record<string, unknown> }>("/settings");
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorState error={query.error} retry={() => { void query.refetch(); }} />;
  const user = query.data.user || account || { username: "—", role: "—" };
  return <Panel title="Administration and settings" icon={Settings}><DetailList items={[["Account", user.username], ["Role", <Badge key="role" value={user.role} />], ["Detector", query.data.model.version], ...Object.entries(query.data.settings).map(([key, value]) => [title(key), String(value)] as [string, string])]} /></Panel>;
}
