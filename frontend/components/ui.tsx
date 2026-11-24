"use client";

import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertCircle, ArrowDown, ArrowUp, ChevronLeft, ChevronRight, FolderOpen, Search, ShieldCheck, type LucideIcon } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { severities, title } from "../lib/api";

const buttonVariants = cva("button", {
  variants: { variant: { primary: "button-primary", secondary: "button-secondary", quiet: "button-quiet" } },
  defaultVariants: { variant: "secondary" },
});

export function Button({ asChild, variant, className, ...props }: ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Component = asChild ? Slot : "button";
  return <Component className={buttonVariants({ variant, className })} {...props} />;
}

export function Brand() {
  return <div className="brand"><span className="brand-mark"><ShieldCheck aria-hidden="true" /></span><div><strong>RoadSecure<span> AI</span></strong><small>Transport cyber defence</small></div></div>;
}

export function Panel({ title: heading, icon: Icon, meta, children, className = "" }: { title: string; icon?: LucideIcon; meta?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><header className="panel-header"><h2>{Icon && <Icon aria-hidden="true" />}{heading}</h2>{meta && <div className="panel-meta">{meta}</div>}</header><div className="panel-body">{children}</div></section>;
}

export function Badge({ value, tone }: { value?: string; tone?: string }) {
  return <span className={`badge badge-${(tone || value || "neutral").toLowerCase()}`}>{title(value)}</span>;
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return <div className="error-state" role="alert"><AlertCircle aria-hidden="true" /><span>{error instanceof Error ? error.message : "Request could not be completed."}</span>{retry && <Button type="button" onClick={retry}>Retry</Button>}</div>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty"><FolderOpen aria-hidden="true" />{children}</div>;
}

export function Loading() {
  return <div className="loading" role="status"><span className="spinner" aria-hidden="true" />Loading workspace…</div>;
}

export function DetailList({ items }: { items: [string, ReactNode][] }) {
  return <dl className="detail-list">{items.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value ?? "—"}</dd></div>)}</dl>;
}

export function DataTable({ headers, children }: { headers: string[]; children: ReactNode }) {
  return <div className="table-scroll"><table><thead><tr>{headers.map((header) => <th scope="col" key={header}>{header}</th>)}</tr></thead><tbody>{children}</tbody></table></div>;
}

export function Select({ label, value, options, onChange }: { label: string; value: string; options: readonly string[]; onChange: (value: string) => void }) {
  return <label className="control"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}><option value="">All</option>{options.map((option) => <option key={option} value={option}>{title(option)}</option>)}</select></label>;
}

export const SeveritySelect = (props: { value: string; onChange: (value: string) => void }) => <Select label="Severity" options={severities} {...props} />;

export function SearchInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="control search"><span>{label}</span><span className="search-box"><Search size={16} aria-hidden="true" /><input type="search" value={value} onChange={(event) => onChange(event.target.value)} placeholder="Search records" /></span></label>;
}

export function Pager({ page, size, currentCount, setPage }: { page: number; size: number; currentCount: number; setPage: (page: number) => void }) {
  return <div className="pagination"><span>{currentCount ? `Showing ${page * size + 1}–${page * size + currentCount}` : "No records on this page"}</span><div><Button type="button" disabled={page === 0} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /> Previous</Button><Button type="button" disabled={currentCount < size} onClick={() => setPage(page + 1)}>Next <ChevronRight size={16} /></Button></div></div>;
}

export function Distribution({ data, colors = false }: { data: [string, number][]; colors?: boolean }) {
  const max = Math.max(1, ...data.map(([, count]) => count));
  if (data.length === 0) return <Empty>No data in this view.</Empty>;
  return <div className="distribution">{data.map(([name, count]) => <div key={name}><div className="distribution-label"><span>{title(name)}</span><strong>{count.toLocaleString()}</strong></div><div className="bar-track" aria-hidden="true"><span className={colors ? name.toLowerCase() : ""} style={{ width: `${count * 100 / max}%` }} /></div></div>)}</div>;
}

export function BackLinkIcon({ up = false }: { up?: boolean }) {
  return up ? <ArrowUp size={16} /> : <ArrowDown size={16} />;
}
