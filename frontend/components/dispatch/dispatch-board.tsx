"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock3, Play, RefreshCw, Route, Sparkles } from "lucide-react";

import { useToast } from "@/components/toast-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, applySchedule, generateSchedule, getCurrentSchedule, validateSchedule, type ScheduleAssignment, type SchedulePlan, type SchedulingEngine } from "@/lib/api";

const inputClass = "h-9 rounded-md border border-slate-700 bg-slate-950/70 px-3 text-sm text-slate-200 outline-none focus:border-cyan-400/60 focus:ring-2 focus:ring-cyan-400/15";
const engineNames: Record<SchedulingEngine, string> = { cp_sat: "CP-SAT optimizer", csp: "Custom CSP", fcfs: "FCFS baseline" };

export function DispatchBoard() {
  const [plan, setPlan] = useState<SchedulePlan | null>(null);
  const [engine, setEngine] = useState<SchedulingEngine>("cp_sat");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"generate" | "validate" | "apply" | null>(null);
  const [error, setError] = useState("");
  const [issues, setIssues] = useState<string[]>([]);
  const { toast } = useToast();

  useEffect(() => {
    const controller = new AbortController();
    getCurrentSchedule(controller.signal).then((value) => { setPlan(value); setSelectedId(value?.assignments[0]?.id ?? null); }).catch((caught: unknown) => {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof ApiError ? caught.message : "Scheduling data could not be loaded.");
    }).finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  async function generate() {
    setBusy("generate"); setError(""); setIssues([]);
    try {
      const next = await generateSchedule(engine); setPlan(next); setSelectedId(next.assignments[0]?.id ?? null);
      toast({ title: "Dispatch plan generated", description: `${engineNames[engine]} returned ${next.solver_status}.`, tone: next.assignments.length ? "success" : "info" });
    } catch (caught) { setError(message(caught)); }
    finally { setBusy(null); }
  }

  async function validate() {
    if (!plan) return; setBusy("validate"); setError("");
    try {
      const result = await validateSchedule(plan); setPlan(result.plan); setIssues(result.issues.map((item) => item.message));
      toast({ title: result.valid ? "Plan validated" : "Validation failed", description: result.message, tone: result.valid ? "success" : "info" });
    } catch (caught) { setError(message(caught)); }
    finally { setBusy(null); }
  }

  async function apply() {
    if (!plan) return; setBusy("apply"); setError("");
    try { const result = await applySchedule(plan); setPlan(result.plan); toast({ title: "Plan applied", description: result.message, tone: "success" }); }
    catch (caught) { setError(message(caught)); }
    finally { setBusy(null); }
  }

  const selected = plan?.assignments.find((item) => item.id === selectedId) ?? null;
  return <div className="animate-[toast-in_220ms_ease-out] space-y-6">
    <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
      <div><p className="text-[11px] font-medium uppercase tracking-[0.18em] text-cyan-400/70">AI platform allocation</p><h1 className="mt-2 text-xl font-semibold tracking-tight text-white sm:text-2xl">Dispatch Board</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Generate, inspect, validate, and provisionally apply platform plans for this synthetic workspace.</p></div>
      <div className="flex flex-wrap items-center gap-2"><select className={inputClass} aria-label="Scheduling engine" value={engine} onChange={(event) => setEngine(event.target.value as SchedulingEngine)}><option value="cp_sat">CP-SAT optimizer</option><option value="csp">Custom CSP</option><option value="fcfs">FCFS baseline</option></select><Button onClick={generate} disabled={busy !== null}><Sparkles className="size-4" />{busy === "generate" ? "Generating…" : "Generate Dispatch Plan"}</Button><Button variant="outline" onClick={validate} disabled={!plan || !plan.assignments.length || busy !== null || plan.is_stale}><CheckCircle2 className="size-4" />{busy === "validate" ? "Validating…" : "Validate Plan"}</Button><Button variant="outline" onClick={apply} disabled={!plan?.is_validated || plan.is_stale || busy !== null || plan.lifecycle_status === "applied"}><Play className="size-4" />{busy === "apply" ? "Applying…" : "Apply Plan"}</Button></div>
    </div>
    <div className="flex items-start gap-3 rounded-lg border border-amber-400/15 bg-amber-400/[0.05] px-4 py-3 text-xs leading-5 text-amber-200/80"><Route className="mt-0.5 size-4 shrink-0" /><p>Platform plans are provisional. Route reservations and route-level conflicts will be checked in Phase 5 and are not validated here.</p></div>
    {error ? <div className="flex items-center gap-2 rounded-lg border border-rose-400/20 bg-rose-400/[0.06] px-4 py-3 text-sm text-rose-200"><AlertTriangle className="size-4" />{error}</div> : null}
    {loading ? <div className="grid gap-6"><Skeleton className="h-28 rounded-xl" /><Skeleton className="h-[520px] rounded-xl" /></div> : plan ? <>
      <SolverSummary plan={plan} />
      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_320px]"><Timeline plan={plan} selectedId={selectedId} onSelect={setSelectedId} /><TrainDetails assignment={selected} /></div>
      {issues.length ? <Card><CardHeader><div><CardTitle>Validation findings</CardTitle><CardDescription>Resolve these hard-constraint violations before applying the plan.</CardDescription></div><Badge tone="critical">{issues.length} issues</Badge></CardHeader><CardContent><ul className="space-y-2">{issues.map((item, index) => <li key={`${item}-${index}`} className="flex gap-2 text-sm text-slate-300"><AlertTriangle className="mt-0.5 size-4 shrink-0 text-rose-300" />{item}</li>)}</ul></CardContent></Card> : null}
    </> : <Card className="grid min-h-[420px] place-items-center p-8 text-center"><div><div className="mx-auto grid size-12 place-items-center rounded-xl border border-cyan-400/20 bg-cyan-400/[0.07]"><Sparkles className="size-5 text-cyan-300" /></div><h2 className="mt-4 font-semibold text-slate-100">No dispatch plan yet</h2><p className="mt-2 max-w-md text-sm leading-6 text-slate-500">Choose a scheduling engine and generate a plan from the current trains, platform compatibility, availability, timing, and clearance constraints.</p><Button className="mt-5" onClick={generate}><Sparkles className="size-4" />Generate Dispatch Plan</Button></div></Card>}
  </div>;
}

function SolverSummary({ plan }: { plan: SchedulePlan }) {
  const delayed = plan.assignments.filter((item) => item.delay_minutes > 0).length;
  const reassigned = plan.assignments.filter((item) => item.reassigned).length;
  const tone = plan.solver_status === "OPTIMAL" || plan.solver_status === "FEASIBLE" ? "positive" : plan.solver_status === "INFEASIBLE" ? "critical" : "warning";
  return <Card><CardContent className="grid gap-5 lg:grid-cols-[1.4fr_repeat(4,minmax(100px,0.5fr))]"><div><div className="flex flex-wrap items-center gap-2"><Badge tone={tone}>{plan.solver_status.replace("_", " ")}</Badge><Badge>{engineNames[plan.engine]}</Badge><Badge tone={plan.lifecycle_status === "applied" ? "positive" : plan.is_validated ? "positive" : "neutral"}>{plan.lifecycle_status}</Badge><span className="font-mono text-[11px] text-slate-600">v{plan.version}</span></div><p className="mt-3 text-sm leading-6 text-slate-400">{plan.explanation}</p></div><Metric label="Assignments" value={String(plan.assignments.length)} /><Metric label="Delayed" value={String(delayed)} /><Metric label="Reassigned" value={String(reassigned)} /><Metric label="Objective" value={plan.objective_value?.toString() ?? "—"} /></CardContent></Card>;
}

function Timeline({ plan, selectedId, onSelect }: { plan: SchedulePlan; selectedId: number | null; onSelect: (id: number) => void }) {
  const start = Math.floor(plan.horizon_start_minute / 15) * 15;
  const end = Math.ceil(plan.horizon_end_minute / 15) * 15;
  const span = Math.max(1, end - start);
  const width = Math.max(900, span * 3);
  const ticks = useMemo(() => { const result = []; for (let value = start; value <= end; value += 30) result.push(value); return result; }, [start, end]);
  return <Card className="min-w-0 overflow-hidden"><CardHeader><div><CardTitle>Platform occupation timeline</CardTitle><CardDescription>Half-open train intervals; clearance buffers are shown with a dashed extension.</CardDescription></div><Badge>{formatMinute(start)}–{formatMinute(end)}</Badge></CardHeader><div className="overflow-x-auto"><div style={{ width: width + 112 }} className="min-w-full"><div className="flex h-11 border-b border-slate-800 bg-slate-950/40"><div className="sticky left-0 z-20 w-28 shrink-0 border-r border-slate-800 bg-slate-950/95 px-4 py-3 text-[10px] uppercase tracking-[0.14em] text-slate-600">Platform</div><div className="relative" style={{ width }}>{ticks.map((tick) => <div key={tick} className="absolute top-0 h-full border-l border-slate-800/80" style={{ left: `${((tick - start) / span) * 100}%` }}><span className="absolute left-2 top-3 font-mono text-[10px] text-slate-500">{formatMinute(tick)}</span></div>)}</div></div>{plan.platforms.map((platform) => { const assignments = plan.assignments.filter((item) => item.platform_id === platform.id); return <div key={platform.id} className="flex h-[76px] border-b border-slate-800/70 last:border-b-0"><div className="sticky left-0 z-20 flex w-28 shrink-0 items-center border-r border-slate-800 bg-slate-900/95 px-4"><div><p className="font-mono text-sm font-semibold text-slate-200">{platform.code}</p><p className={`mt-1 text-[10px] ${platform.is_available ? "text-teal-400/70" : "text-rose-300"}`}>{platform.is_available ? `${platform.clearance_minutes}m clear` : "Unavailable"}</p></div></div><div className="relative bg-[linear-gradient(to_right,rgba(30,41,59,.42)_1px,transparent_1px)] bg-[length:90px_100%]" style={{ width }}>{assignments.map((assignment) => { const left = ((assignment.occupancy_start_minute - start) / span) * 100; const blockWidth = ((assignment.occupancy_end_minute - assignment.occupancy_start_minute) / span) * 100; const clearanceWidth = (platform.clearance_minutes / span) * 100; const selected = selectedId === assignment.id; return <button key={assignment.id} onClick={() => onSelect(assignment.id)} style={{ left: `${left}%`, width: `${Math.max(blockWidth, 1.8)}%` }} className={`group absolute top-3 h-12 overflow-visible rounded-md border px-2 text-left transition ${selected ? "z-10 border-cyan-300 bg-cyan-300/25 ring-2 ring-cyan-300/20" : priorityClass(assignment.priority)}`} aria-label={`Select ${assignment.train_identifier}`}><span className="block truncate text-xs font-semibold text-white">{assignment.train_identifier} · P{assignment.priority}</span><span className="mt-0.5 block truncate font-mono text-[9px] text-slate-300">{formatMinute(assignment.occupancy_start_minute)}–{formatMinute(assignment.occupancy_end_minute)}</span>{clearanceWidth > 0 ? <span className="pointer-events-none absolute -right-[1px] top-1 h-10 translate-x-full border-r border-dashed border-slate-500/60 bg-slate-500/[0.06]" style={{ width: `${Math.max(clearanceWidth / Math.max(blockWidth, 0.01) * 100, 4)}%` }} /> : null}</button>; })}</div></div>; })}</div></div></Card>;
}

function TrainDetails({ assignment }: { assignment: ScheduleAssignment | null }) {
  if (!assignment) return <Card className="grid min-h-72 place-items-center p-6 text-center text-sm text-slate-500">Select a train block to inspect its allocation.</Card>;
  return <Card><CardHeader><div><CardTitle>{assignment.train_identifier}</CardTitle><CardDescription>Selected allocation</CardDescription></div><Badge tone={assignment.delay_minutes ? "warning" : "positive"}>Priority P{assignment.priority}</Badge></CardHeader><CardContent className="space-y-5"><div className="grid grid-cols-2 gap-4"><Metric label="Platform" value={assignment.platform_code} /><Metric label="Delay" value={`${assignment.delay_minutes} min`} /><Metric label="Planned arrival" value={formatMinute(assignment.planned_arrival_minute)} /><Metric label="Allocated arrival" value={formatMinute(assignment.occupancy_start_minute)} /><Metric label="Planned departure" value={formatMinute(assignment.planned_departure_minute)} /><Metric label="Allocated departure" value={formatMinute(assignment.occupancy_end_minute)} /></div><div className="flex items-start gap-2 border-t border-slate-800 pt-4 text-xs leading-5 text-slate-500"><Clock3 className="mt-0.5 size-3.5 shrink-0" />The occupancy block excludes the platform clearance buffer shown after it.</div>{assignment.reassigned ? <div className="flex items-center gap-2 text-xs text-amber-300"><RefreshCw className="size-3.5" />Platform changed from the applied plan.</div> : null}</CardContent></Card>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] uppercase tracking-[0.12em] text-slate-600">{label}</p><p className="mt-1 font-mono text-sm text-slate-200">{value}</p></div>; }
function formatMinute(value: number) { return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`; }
function priorityClass(priority: number) { return priority <= 2 ? "border-rose-300/30 bg-rose-400/20 hover:bg-rose-400/30" : priority === 3 ? "border-amber-300/30 bg-amber-400/20 hover:bg-amber-400/30" : "border-teal-300/30 bg-teal-400/20 hover:bg-teal-400/30"; }
function message(caught: unknown) { return caught instanceof ApiError ? caught.message : "The scheduling operation could not be completed."; }
