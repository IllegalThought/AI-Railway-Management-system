"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, Clock3, Database, RefreshCw, Server, TrainFront } from "lucide-react";

import { useToast } from "@/components/toast-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { KpiCard } from "@/components/overview/kpi-card";
import { ApiError, getApiBaseUrl, getHealth, type HealthResponse } from "@/lib/api";

type HealthState =
  | { status: "loading" }
  | { status: "available"; data: HealthResponse; checkedAt: Date }
  | { status: "unavailable"; message: string; checkedAt: Date };

export function OverviewDashboard() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const { toast } = useToast();

  const refreshHealth = useCallback(async (notify = false) => {
    setHealth({ status: "loading" });
    try {
      const data = await getHealth();
      setHealth({ status: "available", data, checkedAt: new Date() });
      if (notify) toast({ title: "System status refreshed", description: "The backend health check completed successfully.", tone: "success" });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      const message = error instanceof ApiError ? error.message : "System status could not be loaded.";
      setHealth({ status: "unavailable", message, checkedAt: new Date() });
      if (notify) toast({ title: "System status unavailable", description: message, tone: "info" });
    }
  }, [toast]);

  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal)
      .then((data) => setHealth({ status: "available", data, checkedAt: new Date() }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setHealth({ status: "unavailable", message: error instanceof ApiError ? error.message : "System status could not be loaded.", checkedAt: new Date() });
      });
    return () => controller.abort();
  }, []);

  const online = health.status === "available";
  const checkedTime = health.status !== "loading" ? health.checkedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null;

  return (
    <div className="animate-[toast-in_220ms_ease-out] space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="flex items-center gap-2"><p className="text-[11px] font-medium uppercase tracking-[0.18em] text-cyan-400/70">System overview</p><Badge tone="neutral">Synthetic simulation</Badge></div>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-white sm:text-2xl">Operations control summary</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Service readiness and operational data availability across the RailOps AI workspace.</p>
        </div>
        <Button variant="outline" onClick={() => refreshHealth(true)} disabled={health.status === "loading"}><RefreshCw className={`size-3.5 ${health.status === "loading" ? "animate-spin" : ""}`} />Refresh status</Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Backend service" value={online ? "Online" : health.status === "loading" ? "" : "Unavailable"} detail={online ? `${health.data.service} · v${health.data.version}` : health.status === "unavailable" ? health.message : "Checking service health"} icon={Server} loading={health.status === "loading"} tone={online ? "positive" : health.status === "unavailable" ? "warning" : "neutral"} />
        <KpiCard label="Trains in service" value="—" detail="Operational API not available" icon={TrainFront} />
        <KpiCard label="Platform occupancy" value="—" detail="Assignment API not available" icon={Activity} />
        <KpiCard label="Active incidents" value="—" detail="Incident API not available" icon={AlertTriangle} />
      </div>

      <Card>
        <CardHeader>
          <div><CardTitle>System readiness</CardTitle><CardDescription>Live connectivity to the configured FastAPI service</CardDescription></div>
          {health.status === "loading" ? <Badge><span className="mr-1.5 size-1.5 animate-pulse rounded-full bg-slate-400" />Checking</Badge> : online ? <Badge tone="positive"><span className="mr-1.5 size-1.5 rounded-full bg-teal-300" />Operational</Badge> : <Badge tone="warning"><span className="mr-1.5 size-1.5 rounded-full bg-amber-300" />Unavailable</Badge>}
        </CardHeader>
        <CardContent className="grid gap-px overflow-hidden rounded-b-xl bg-slate-800/70 p-0 sm:grid-cols-3">
          <ReadinessItem icon={Server} label="API service" value={online ? health.data.status.toUpperCase() : health.status === "loading" ? "CHECKING" : "UNAVAILABLE"} available={online} />
          <ReadinessItem icon={Database} label="Database" value={online ? health.data.database.toUpperCase() : "UNKNOWN"} available={online} />
          <ReadinessItem icon={Clock3} label="Last check" value={checkedTime ?? "IN PROGRESS"} available={online} />
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <Card>
          <CardHeader><div><CardTitle>Platform occupancy</CardTitle><CardDescription>Current and scheduled platform use</CardDescription></div><Badge>Unavailable</Badge></CardHeader>
          <CardContent><DataTable columns={[{ key: "platform", label: "Platform" }, { key: "train", label: "Train" }, { key: "window", label: "Occupancy window" }, { key: "status", label: "Status", align: "right" }]} rows={[]} emptyTitle="No occupancy feed available" emptyDescription="Platform assignments cannot be displayed until an operational scheduling API is implemented." /></CardContent>
        </Card>
        <Card>
          <CardHeader><div><CardTitle>Active incidents</CardTitle><CardDescription>Open and monitored disruptions</CardDescription></div><Badge>Unavailable</Badge></CardHeader>
          <CardContent className="flex min-h-[246px] flex-col items-center justify-center text-center"><span className="grid size-10 place-items-center rounded-lg border border-slate-800 bg-slate-950/60 text-slate-500"><AlertTriangle className="size-4" /></span><p className="mt-3 text-sm font-medium text-slate-300">Incident feed not connected</p><p className="mt-1 max-w-xs text-xs leading-5 text-slate-500">No incident read endpoint exists in the current backend.</p></CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><div><CardTitle>Upcoming trains</CardTitle><CardDescription>Scheduled arrivals and departures</CardDescription></div><Badge>Unavailable</Badge></CardHeader>
          <CardContent><DataTable columns={[{ key: "train", label: "Train" }, { key: "movement", label: "Movement" }, { key: "time", label: "Time" }, { key: "platform", label: "Platform", align: "right" }]} rows={[]} emptyTitle="No timetable feed available" emptyDescription="Train records are stored by the backend, but a read endpoint is not implemented in this phase." /></CardContent>
        </Card>
        <Card>
          <CardHeader><div><CardTitle>Recent activity</CardTitle><CardDescription>Latest operational events in this workspace</CardDescription></div><Badge>Unavailable</Badge></CardHeader>
          <CardContent className="flex min-h-[246px] flex-col items-center justify-center text-center"><span className="grid size-10 place-items-center rounded-lg border border-slate-800 bg-slate-950/60 text-slate-500"><Activity className="size-4" /></span><p className="mt-3 text-sm font-medium text-slate-300">Activity feed not connected</p><p className="mt-1 max-w-xs text-xs leading-5 text-slate-500">Operational events will appear when an event API is available.</p></CardContent>
        </Card>
      </div>

      <p className="flex items-center gap-2 border-t border-slate-800/80 pt-5 text-[11px] leading-5 text-slate-600"><span className="size-1.5 shrink-0 rounded-full bg-cyan-400/60" />RailOps AI is a synthetic decision-support simulation and is not certified railway signaling software.{!getApiBaseUrl() ? " Configure NEXT_PUBLIC_API_BASE_URL to enable backend status checks." : ""}</p>
    </div>
  );
}

function ReadinessItem({ icon: Icon, label, value, available }: { icon: typeof Server; label: string; value: string; available: boolean }) {
  return <div className="flex items-center gap-3 bg-slate-900/80 px-5 py-4"><span className="grid size-8 place-items-center rounded-md bg-slate-950/70 text-slate-500"><Icon className="size-3.5" /></span><div><p className="text-[11px] text-slate-500">{label}</p><p className={`mt-0.5 font-mono text-xs font-medium ${available ? "text-teal-300" : "text-slate-400"}`}>{value}</p></div></div>;
}
