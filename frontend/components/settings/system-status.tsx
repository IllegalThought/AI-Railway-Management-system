"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, Globe2, LockKeyhole, RefreshCw, Server, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { describeApiFailure, getApiBaseUrl, getHealth, type ApiFailurePresentation, type HealthResponse } from "@/lib/api";

type StatusState =
  | { status: "loading" }
  | { status: "ready"; health: HealthResponse; checkedAt: Date }
  | { status: "error"; error: ApiFailurePresentation; checkedAt: Date };

export function SystemStatus() {
  const [state, setState] = useState<StatusState>({ status: "loading" });
  const load = useCallback(async (signal?: AbortSignal) => {
    setState({ status: "loading" });
    try {
      setState({ status: "ready", health: await getHealth(signal), checkedAt: new Date() });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setState({ status: "error", error: describeApiFailure(error), checkedAt: new Date() });
    }
  }, []);

  // Initial API synchronization is intentionally effect-driven.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load]);

  const apiOrigin = getApiBaseUrl();
  return <div className="space-y-6">
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div><p className="text-[11px] font-medium uppercase tracking-[0.18em] text-cyan-400/70">Release environment</p><h1 className="mt-2 text-xl font-semibold tracking-tight text-white sm:text-2xl">System Status</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Runtime connectivity, environment boundaries, and safety controls for this synthetic operations workspace.</p></div>
      <Button variant="outline" onClick={() => void load()} disabled={state.status === "loading"}><RefreshCw className={`size-4 ${state.status === "loading" ? "animate-spin" : ""}`} />Check status</Button>
    </div>

    {state.status === "error" ? <div role="alert" className="rounded-lg border border-rose-900/60 bg-rose-950/30 px-4 py-3 text-sm text-rose-200"><p className="font-medium">{state.error.title}</p><p className="mt-1 text-xs text-rose-300/75">{state.error.message}</p></div> : null}

    <div className="grid gap-3 md:grid-cols-3">
      <StatusCard icon={Server} label="API service" value={state.status === "ready" ? "Operational" : state.status === "error" ? "Unavailable" : "Checking"} detail={state.status === "ready" ? `${state.health.service} · v${state.health.version}` : "Waiting for the health endpoint"} loading={state.status === "loading"} healthy={state.status === "ready"} />
      <StatusCard icon={Database} label="Persistence" value={state.status === "ready" ? "Available" : state.status === "error" ? "Unknown" : "Checking"} detail={state.status === "ready" ? "Database connectivity verified" : "No database status received"} loading={state.status === "loading"} healthy={state.status === "ready"} />
      <StatusCard icon={Globe2} label="Environment" value={state.status === "ready" ? state.health.environment : "—"} detail={apiOrigin || "NEXT_PUBLIC_API_BASE_URL is not configured"} loading={state.status === "loading"} healthy={Boolean(apiOrigin)} />
    </div>

    <div className="grid gap-6 xl:grid-cols-2">
      <Card><CardHeader><div><CardTitle>Workspace isolation</CardTitle><CardDescription>Browser workspaces are separated by a UUID request header.</CardDescription></div><LockKeyhole className="size-4 text-teal-300" /></CardHeader><CardContent className="space-y-3 text-sm leading-6 text-slate-400"><p>Train, platform, plan, incident, simulation, and analytics records are scoped to the current demo workspace.</p><p className="text-xs text-slate-500">The identifier isolates demonstration data; it is not user authentication or authorization.</p></CardContent></Card>
      <Card><CardHeader><div><CardTitle>Operational boundary</CardTitle><CardDescription>Intended use of the release candidate</CardDescription></div><ShieldCheck className="size-4 text-cyan-300" /></CardHeader><CardContent className="space-y-3 text-sm leading-6 text-slate-400"><p>RailOps AI models scheduling and disruption response for demonstration and decision-support evaluation.</p><p className="text-xs text-slate-500">It is not certified railway signaling, dispatch, or safety software and must not control real infrastructure.</p></CardContent></Card>
    </div>

    <p className="text-right text-[11px] text-slate-600">{state.status === "ready" || state.status === "error" ? `Last checked ${state.checkedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Status check in progress"}</p>
  </div>;
}

function StatusCard({ icon: Icon, label, value, detail, loading, healthy }: { icon: typeof Server; label: string; value: string; detail: string; loading: boolean; healthy: boolean }) {
  return <Card className="p-5"><div className="flex items-start justify-between gap-4"><div className="min-w-0"><p className="text-xs text-slate-500">{label}</p>{loading ? <Skeleton className="mt-3 h-7 w-28" /> : <p className="mt-2 text-lg font-semibold capitalize text-slate-100">{value}</p>}<p className="mt-2 truncate text-xs text-slate-500" title={detail}>{detail}</p></div><Badge tone={healthy ? "positive" : "neutral"}><Icon className="mr-1 size-3" />{healthy ? "Ready" : "Pending"}</Badge></div></Card>;
}
