"use client";

import { useCallback, useEffect, useState } from "react";
import { Clock3, Gauge, Pause, Play, RefreshCw, RotateCcw, StepForward, TrainFront } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, controlSimulation, getSimulationState, type SimulationState } from "@/lib/api";

const formatMinute = (minute: number) => `${String(Math.floor(minute / 60) % 24).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;

export function LiveOperations() {
  const [data, setData] = useState<SimulationState | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (quiet = false) => {
    if (!quiet) setBusy(true);
    try { setData(await getSimulationState()); setError(""); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Live state could not be loaded."); }
    finally { if (!quiet) setBusy(false); }
  }, []);

  // Initial API synchronization is intentionally effect-driven.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (data?.run_status !== "running") return;
    const timer = window.setInterval(() => void load(true), 1000);
    return () => window.clearInterval(timer);
  }, [data?.run_status, load]);

  async function command(action: "start" | "pause" | "step" | "reset", speed?: 1 | 2 | 5) {
    if (!data) return;
    setBusy(true);
    try { setData(await controlSimulation(action, data.revision, speed)); setError(""); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "The simulation command failed."); await load(true); }
    finally { setBusy(false); }
  }

  return <div className="space-y-6">
    <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><p className="text-[11px] font-medium uppercase tracking-[0.18em] text-cyan-400/70">Backend-controlled playback</p><h1 className="mt-2 text-xl font-semibold text-white sm:text-2xl">Live Operations</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Monitor deterministic train movement, platform occupation, reservations, and validated movement permissions.</p></div><Button variant="outline" onClick={() => void load()} disabled={busy}><RefreshCw className={`size-4 ${busy ? "animate-spin" : ""}`} />Refresh state</Button></div>
    {error ? <div className="rounded-lg border border-red-900/60 bg-red-950/30 px-4 py-3 text-sm text-red-200">{error}</div> : null}
    <Card><CardContent className="flex flex-col gap-5 py-5 xl:flex-row xl:items-center xl:justify-between"><div className="flex flex-wrap items-center gap-6"><Metric icon={Clock3} label="Simulated time" value={data ? formatMinute(data.current_minute) : "--:--"} /><Metric icon={Gauge} label="Playback" value={data ? `${data.run_status} · ${data.speed}x` : "Unavailable"} /><Metric icon={TrainFront} label="Active plan" value={data?.active_plan_version ? `Version ${data.active_plan_version}` : "Not applied"} /></div><div className="flex flex-wrap gap-2"><Button onClick={() => void command("start")} disabled={busy || !data || data.run_status === "running"}><Play className="size-4" />Start</Button><Button variant="outline" onClick={() => void command("pause")} disabled={busy || !data || data.run_status === "paused"}><Pause className="size-4" />Pause</Button><Button variant="outline" onClick={() => void command("step")} disabled={busy || !data || data.run_status === "running"}><StepForward className="size-4" />Step</Button><Button variant="ghost" onClick={() => void command("reset")} disabled={busy || !data}><RotateCcw className="size-4" />Reset</Button>{([1, 2, 5] as const).map((speed) => <Button key={speed} size="sm" variant={data?.speed === speed ? "outline" : "ghost"} onClick={() => void command(data?.run_status === "running" ? "start" : "pause", speed)} disabled={busy || !data}>{speed}x</Button>)}</div></CardContent></Card>
    <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.4fr)_minmax(360px,.6fr)]"><Card><CardHeader><div><CardTitle>Train movement</CardTitle><CardDescription>Progress is projected only from persisted route reservations and the backend clock.</CardDescription></div></CardHeader><CardContent className="space-y-3">{data?.trains.length ? data.trains.map((train) => <div key={train.train_id} className="rounded-lg border border-slate-800 bg-slate-950/35 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-mono text-sm font-semibold text-slate-100">{train.train_identifier}</p><p className="mt-1 text-xs text-slate-500">{train.position} · Platform {train.platform_code} · {train.status.replaceAll("_", " ")}</p></div><Signal value={train.signal} /></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-cyan-400 transition-[width] duration-700 ease-linear" style={{ width: `${train.progress_percent}%` }} /></div></div>) : <p className="py-12 text-center text-sm text-slate-500">{data?.message ?? "Loading live state…"}</p>}</CardContent></Card><div className="space-y-6"><Card><CardHeader><CardTitle>Platform occupation</CardTitle><CardDescription>Half-open occupancy intervals at {data ? formatMinute(data.current_minute) : "--:--"}.</CardDescription></CardHeader><CardContent className="grid grid-cols-2 gap-3">{data?.platforms.map((platform) => <div key={platform.platform_code} className={`rounded-lg border p-3 ${platform.occupied ? "border-cyan-800/70 bg-cyan-950/20" : "border-slate-800 bg-slate-950/30"}`}><div className="flex items-center justify-between"><span className="font-mono text-xs text-slate-300">{platform.platform_code}</span><span className={`size-2 rounded-full ${platform.occupied ? "bg-cyan-300" : "bg-slate-700"}`} /></div><p className="mt-2 text-xs text-slate-500">{platform.train_identifier ?? "Clear"}</p></div>)}</CardContent></Card><Card><CardHeader><CardTitle>Active reservations</CardTitle><CardDescription>Track and switch resources occupied now.</CardDescription></CardHeader><CardContent className="space-y-2">{data?.active_reservations.length ? data.active_reservations.map((item) => <div key={`${item.train_identifier}-${item.resource_code}`} className="flex items-center justify-between rounded-md border border-slate-800 px-3 py-2 text-xs"><span className="font-mono text-slate-300">{item.resource_code}</span><span className="text-slate-500">{item.train_identifier} · {formatMinute(item.start_minute)}–{formatMinute(item.end_minute)}</span></div>) : <p className="text-xs text-slate-500">No track or switch reservation is active at this minute.</p>}</CardContent></Card></div></div>
    <Card><CardHeader><CardTitle>Operational event stream</CardTitle><CardDescription>Persisted events at or before the current simulated time.</CardDescription></CardHeader><CardContent className="space-y-2">{data?.events.map((event) => <div key={event.id} className="grid gap-1 rounded-md border border-slate-800 px-3 py-2 text-xs sm:grid-cols-[60px_1fr_auto]"><span className="font-mono text-cyan-300">{formatMinute(event.event_minute)}</span><span className="text-slate-300">{event.message}</span><span className="text-slate-600">{event.resource_code}</span></div>)}</CardContent></Card>
  </div>;
}

function Metric({ icon: Icon, label, value }: { icon: typeof Clock3; label: string; value: string }) { return <div className="flex items-center gap-3"><span className="grid size-9 place-items-center rounded-lg border border-slate-800 bg-slate-950/50 text-cyan-300"><Icon className="size-4" /></span><div><p className="text-[10px] uppercase tracking-wider text-slate-600">{label}</p><p className="mt-0.5 text-sm font-medium capitalize text-slate-200">{value}</p></div></div>; }
function Signal({ value }: { value: "RED" | "YELLOW" | "GREEN" }) { const tone = value === "GREEN" ? "positive" : value === "RED" ? "critical" : "warning"; return <Badge tone={tone}><span className={`mr-1.5 inline-block size-1.5 rounded-full ${value === "GREEN" ? "bg-emerald-300" : value === "RED" ? "bg-red-300" : "bg-amber-300"}`} />{value}</Badge>; }
