"use client";

import { QueryClient, QueryClientProvider, useQueryClient, useMutation } from "@tanstack/react-query";
import { Activity, BarChart3, BrainCircuit, ChevronRight, CircleAlert, Eye, EyeOff, Files, LayoutDashboard, LogOut, Moon, RadioTower, Settings, ShieldCheck, Sun } from "lucide-react";
import { MotionConfig, motion } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useSyncExternalStore, useState, type FormEvent } from "react";
import { api, ApiError, title, write, type Account } from "../lib/api";
import { Brand, Button, ErrorState, Loading } from "./ui";
import { useApi } from "./query";
import { Dashboard, Evaluation, Reports, SettingsPage } from "./overview";
import { EventDetails, Events, AlertDetails, Alerts } from "./monitor";
import { IncidentDetails, Incidents, Simulator } from "./response";

const nav = [
  { page: "dashboard", href: "/", label: "Dashboard", icon: LayoutDashboard },
  { page: "events", href: "/events", label: "Security Events", icon: Activity },
  { page: "alerts", href: "/alerts", label: "Security Alerts", icon: CircleAlert },
  { page: "simulator", href: "/simulator", label: "Simulate Activity", icon: RadioTower },
  { page: "incidents", href: "/incidents", label: "Incident Management", icon: Files },
  { page: "reports", href: "/reports", label: "Reports", icon: BarChart3 },
  { page: "evaluation", href: "/evaluation", label: "Model Evaluation", icon: BrainCircuit },
  { page: "settings", href: "/settings", label: "Settings", icon: Settings },
];

const headings: Record<string, [string, string, string?]> = {
  dashboard: ["Overview", "Security overview"],
  events: ["Monitoring", "Security events", "Event details"],
  alerts: ["Monitoring", "Security alerts", "Alert details"],
  simulator: ["Simulation", "Simulate activity"],
  incidents: ["Response", "Incident management", "Incident details"],
  reports: ["Analytics", "Reports and analytics"],
  evaluation: ["Analytics", "Model evaluation"],
  settings: ["Administration", "Settings"],
};

export function RoadSecure({ page, id }: { page: string; id?: string }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 2500, retry: false, refetchOnWindowFocus: true } },
  }));
  return <QueryClientProvider client={client}><MotionConfig reducedMotion="user"><Session page={page} id={id} /></MotionConfig></QueryClientProvider>;
}

function Session({ page, id }: { page: string; id?: string }) {
  const router = useRouter();
  const account = useApi<Account>("/auth/me", { interval: 30000 });
  const signedOut = account.error instanceof ApiError && account.error.status === 401;

  useEffect(() => {
    if (page === "login" && account.data && !account.error) router.replace("/");
    if (page !== "login" && signedOut) router.replace("/login");
  }, [account.data, account.error, page, router, signedOut]);

  if (page === "login") return account.data && !account.error ? <Loading /> : <Login />;
  if (account.isPending || signedOut) return <Loading />;
  if (account.error) return <main className="login-wrap"><ErrorState error={account.error} retry={() => { void account.refetch(); }} /></main>;
  return <Workspace page={page} id={id} account={account.data} />;
}

function subscribeTheme(callback: () => void) {
  window.addEventListener("roadsecure-theme-change", callback);
  return () => window.removeEventListener("roadsecure-theme-change", callback);
}

function themeSnapshot() {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeTheme, themeSnapshot, () => "dark");

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("roadsecure-theme", next);
    } catch {
      // The theme still applies for this session when storage is unavailable.
    }
    window.dispatchEvent(new Event("roadsecure-theme-change"));
  }

  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  return <Button type="button" variant="quiet" aria-label={label} title={label} aria-pressed={theme === "light"} onClick={toggle}>{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}</Button>;
}

function Login() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [visible, setVisible] = useState(false);
  const login = useMutation({
    mutationFn: (credentials: { username: string; password: string }) => api<Account>("/auth/login", write("POST", credentials)),
    onSuccess: (account) => {
      queryClient.setQueryData(["/auth/me"], account);
      router.replace("/");
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    login.mutate({ username: String(data.get("username")).trim(), password: String(data.get("password")) });
  }

  return <main className="login-wrap">
    <motion.div className="login-panel panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
      <Brand />
      <div className="login-intro"><h1>Administrator sign in</h1><p>Access the road transport security operations console.</p></div>
      <form className="form-stack" onSubmit={submit}>
        <label className="control">Username<input name="username" autoComplete="username" required maxLength={100} autoFocus /></label>
        <label className="control">Password<div className="password-box"><input name="password" type={visible ? "text" : "password"} autoComplete="current-password" required maxLength={256} /><Button type="button" variant="quiet" onClick={() => setVisible(!visible)} aria-label={visible ? "Hide password" : "Show password"}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</Button></div></label>
        {login.error && <ErrorState error={login.error} />}
        <Button variant="primary" type="submit" disabled={login.isPending}>{login.isPending ? "Signing in…" : "Sign in"}<ChevronRight size={17} /></Button>
      </form>
      <div className="login-footer"><ShieldCheck size={16} /> Isolated academic environment · Synthetic data only</div>
    </motion.div>
  </main>;
}

function Workspace({ page, id, account }: { page: string; id?: string; account: Account }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const connection = useApi<{ status: string }>("/model/status", { interval: 15000 });
  const logout = useMutation({
    mutationFn: () => api("/auth/logout", write("POST")),
    onSuccess: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });
  const [section, name, detail] = headings[page];
  return <div className="workspace">
    <aside className="sidebar">
      <Link href="/" className="brand-link"><Brand /></Link>
      <span className="nav-label">Operations</span>
      <nav aria-label="Main navigation">
        {nav.map(({ page: key, href, label, icon: Icon }) => <Link key={key} href={href} aria-current={key === page ? "page" : undefined}><Icon size={18} aria-hidden="true" /><span>{label}</span></Link>)}
      </nav>
      <div className="sidebar-footer"><span className="system-status"><span className={connection.isSuccess && !connection.isError ? "status-dot online" : "status-dot"} />{connection.isSuccess && !connection.isError ? "Detector connected" : "Detector status unavailable"}</span><span className="sidebar-caption">Synthetic environment</span></div>
    </aside>
    <main className="workspace-main" id="main">
      <header className="topbar">
        <div><div className="eyebrow">{section}{id && <><ChevronRight size={11} /> <Link href={`/${page}`}>{name}</Link></>}</div><h1>{id ? detail : name}</h1></div>
        <div className="account-bar"><span><strong>{account.username}</strong><small>{title(account.role)}</small></span><ThemeToggle /><Button type="button" variant="quiet" aria-label="Sign out" disabled={logout.isPending} onClick={() => logout.mutate()}><LogOut size={18} /></Button></div>
      </header>
      {logout.error && <ErrorState error={logout.error} />}
      <div className="content" key={`${page}/${id ?? ""}`}>
        {page === "dashboard" && <Dashboard />}
        {page === "events" && (id ? <EventDetails id={id} /> : <Events />)}
        {page === "alerts" && (id ? <AlertDetails id={id} /> : <Alerts />)}
        {page === "simulator" && <Simulator />}
        {page === "incidents" && (id ? <IncidentDetails id={id} /> : <Incidents />)}
        {page === "reports" && <Reports />}
        {page === "evaluation" && <Evaluation />}
        {page === "settings" && <SettingsPage account={account} />}
      </div>
      <footer className="workspace-footer">RoadSecure AI <span>Mulungushi University · Academic prototype</span></footer>
    </main>
  </div>;
}
