"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Clock3, RefreshCw, TrainFront, Warehouse } from "lucide-react";
import { KpiCard } from "@/components/overview/kpi-card";
import { useToast } from "@/components/toast-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { describeApiFailure, getOverview, type ApiFailurePresentation, type Overview } from "@/lib/api";

type DashboardState = { status: "loading" } | { status: "available"; overview: Overview } | { status: "unavailable"; error: ApiFailurePresentation };

export function OverviewDashboard() {
  const [state, setState] = useState<DashboardState>({ status: "loading" });
  const { toast } = useToast();
  const load = useCallback(async (notify = false, signal?: AbortSignal) => {
    try {
      const overview = await getOverview(signal);
      setState({ status: "available", overview });
      if (notify) toast({ title: "Overview refreshed", description: "Current operating data is displayed.", tone: "success" });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      const failure = describeApiFailure(error); setState({ status: "unavailable", error: failure });
      if (notify) toast({ title: failure.title, description: failure.message, tone: "info" });
    }
  }, [toast]);
  // Initial API synchronization is intentionally effect-driven.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { const controller = new AbortController(); void load(false, controller.signal); return () => controller.abort(); }, [load]);
  const overview = state.status === "available" ? state.overview : null;

  return <div className="animate-[toast-in_220ms_ease-out] space-y-5">
    <div className="flex items-center justify-between gap-4"><div><h2 className="text-xl font-semibold tracking-tight text-[#202B36]">Operations Overview</h2>{overview ? <p className="mt-1 text-sm text-[#687581]">{overview.scenario_name}</p> : null}</div><Button variant="outline" onClick={() => void load(true)} disabled={state.status === "loading"}><RefreshCw className={`size-3.5 ${state.status === "loading" ? "animate-spin" : ""}`} />Refresh</Button></div>
    {state.status === "unavailable" ? <div role="alert" className="flex items-start justify-between gap-4 rounded-md border border-[#E1B9B9] bg-[#FCEEEE] px-4 py-3 text-sm text-[#7F3434]"><div><p className="font-medium">{state.error.title}</p><p className="mt-1 text-xs">{state.error.message}</p></div><Button size="sm" variant="outline" onClick={() => void load(true)}>Retry</Button></div> : null}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard label="Trains" value={overview ? String(overview.train_count) : "—"} detail={overview ? `${overview.scheduled_train_count} scheduled` : "Loading"} icon={TrainFront} loading={state.status === "loading"} />
      <KpiCard label="Delayed" value={overview ? String(overview.delayed_train_count) : "—"} detail="Current services" icon={Clock3} loading={state.status === "loading"} tone={overview?.delayed_train_count ? "warning" : "positive"} />
      <KpiCard label="Platforms available" value={overview ? `${overview.available_platform_count}/${overview.platform_count}` : "—"} detail={overview?.unavailable_platform_count ? `${overview.unavailable_platform_count} unavailable` : "All configured platforms"} icon={Warehouse} loading={state.status === "loading"} tone={overview?.unavailable_platform_count ? "warning" : "positive"} />
      <KpiCard label="Active incidents" value={overview ? String(overview.active_incident_count) : "—"} detail={overview?.active_incident_count ? "Response required" : "No open incidents"} icon={AlertTriangle} loading={state.status === "loading"} tone={overview?.active_incident_count ? "warning" : "positive"} />
    </div>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(300px,.55fr)]">
      <Card><CardHeader><CardTitle>Upcoming trains</CardTitle></CardHeader><CardContent><DataTable columns={[{ key: "train", label: "Train" }, { key: "arrival", label: "Arrival" }, { key: "departure", label: "Departure" }, { key: "status", label: "Status", align: "right" }]} rows={(overview?.upcoming_trains ?? []).map((train) => ({ train: <span className="font-medium">{train.identifier}</span>, arrival: <span className="font-mono text-xs">{formatMinute(train.arrival_minute)}</span>, departure: <span className="font-mono text-xs">{formatMinute(train.departure_minute)}</span>, status: <Badge tone={train.service_status === "delayed" ? "warning" : "positive"}>{train.service_status === "delayed" ? `Delayed ${train.delay_minutes} min` : "Scheduled"}</Badge> }))} emptyTitle="No upcoming trains" emptyDescription="No scheduled train records are available." /></CardContent></Card>
      <Card><CardHeader><div className="flex w-full items-center justify-between gap-3"><CardTitle>Active incidents</CardTitle><Badge tone={overview?.active_incident_count ? "warning" : "positive"}>{overview?.active_incident_count ?? 0}</Badge></div></CardHeader><CardContent className="space-y-2">{overview?.active_incidents.length ? overview.active_incidents.map((incident) => <div key={incident.id} className="rounded-md border border-[#E1E6EA] bg-[#FAFBFB] p-3"><div className="flex items-start justify-between gap-3"><p className="text-sm font-medium text-[#202B36]">{incident.title}</p><Badge tone={incident.severity === "high" || incident.severity === "critical" ? "critical" : "warning"}>{incident.severity}</Badge></div><p className="mt-2 text-xs text-[#687581]">{incident.resource_code ?? "Network"} · {formatMinute(incident.reported_minute)}</p></div>) : <p className="py-10 text-center text-sm text-[#687581]">No active incidents</p>}</CardContent></Card>
    </div>
    <div className="grid gap-5 xl:grid-cols-2">
      <Card><CardHeader><CardTitle>Platform status</CardTitle></CardHeader><CardContent><div className="flex items-center justify-between rounded-md border border-[#DFE4E8] bg-[#F8F9FA] px-5 py-4"><div><p className="text-sm font-medium text-[#34424F]">Available resources</p><p className="mt-1 text-xs text-[#687581]">{overview?.unavailable_platform_count ?? 0} unavailable</p></div><p className="font-mono text-2xl font-semibold text-[#4F7A63]">{overview?.available_platform_count ?? "—"}<span className="text-sm font-normal text-[#687581]"> / {overview?.platform_count ?? "—"}</span></p></div></CardContent></Card>
      <Card><CardHeader><CardTitle>Recent activity</CardTitle></CardHeader><CardContent className="space-y-3">{overview?.recent_activity.length ? overview.recent_activity.slice(0, 5).map((event) => <div key={event.id} className="flex gap-3 border-b border-[#E5E9EC] pb-3 last:border-0 last:pb-0"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-[#36638A]" /><div><p className="text-sm text-[#34424F]">{event.message}</p><p className="mt-1 text-[11px] text-[#7C8994]">{new Date(event.created_at).toLocaleString()}</p></div></div>) : <p className="py-6 text-center text-sm text-[#687581]">No recent activity</p>}</CardContent></Card>
    </div>
  </div>;
}
function formatMinute(value: number) { return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`; }
