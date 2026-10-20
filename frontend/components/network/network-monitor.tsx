"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, GitBranch, RefreshCw, Route, TrainFront, Waypoints } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getNetworkMonitor, type NetworkEdge, type NetworkMonitor, type NetworkMovement, type NetworkNode } from "@/lib/api";

export function NetworkMonitorView() {
  const [data, setData] = useState<NetworkMonitor | null>(null);
  const [selectedTrain, setSelectedTrain] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true); setError("");
    const controller = new AbortController();
    getNetworkMonitor(controller.signal).then((value) => { setData(value); setSelectedTrain((current) => current ?? value.movements[0]?.train_id ?? null); }).catch((caught: unknown) => {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof ApiError ? caught.message : "Network data could not be loaded.");
    }).finally(() => setLoading(false));
    return controller;
  }

  useEffect(() => {
    const controller = new AbortController();
    getNetworkMonitor(controller.signal).then((value) => { setData(value); setSelectedTrain(value.movements[0]?.train_id ?? null); }).catch((caught: unknown) => {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) setError(caught instanceof ApiError ? caught.message : "Network data could not be loaded.");
    }).finally(() => setLoading(false));
    return () => controller.abort();
  }, []);
  const selected = data?.movements.find((item) => item.train_id === selectedTrain) ?? null;

  return <div className="animate-[toast-in_220ms_ease-out] space-y-6">
    <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><p className="text-[11px] font-medium uppercase tracking-[0.18em] text-cyan-400/70">Graph operations</p><h1 className="mt-2 text-xl font-semibold tracking-tight text-white sm:text-2xl">Network Monitor</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Inspect directed track topology, A* routes, exclusive reservations, closures, and explainable movement decisions.</p></div><Button variant="outline" onClick={load} disabled={loading}><RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />Refresh Network</Button></div>
    {error ? <div className="flex items-center gap-2 rounded-lg border border-rose-400/20 bg-rose-400/[0.06] px-4 py-3 text-sm text-rose-200"><AlertTriangle className="size-4" />{error}</div> : null}
    {loading && !data ? <div className="grid gap-6"><Skeleton className="h-24 rounded-xl" /><Skeleton className="h-[560px] rounded-xl" /></div> : data ? <>
      <StatusStrip data={data} />
      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]"><NetworkCanvas data={data} selected={selected} /><DecisionPanel movements={data.movements} selected={selected} onSelect={setSelectedTrain} /></div>
    </> : null}
  </div>;
}

function StatusStrip({ data }: { data: NetworkMonitor }) {
  const counts = data.movements.reduce((result, item) => ({ ...result, [item.indicator]: result[item.indicator] + 1 }), { RED: 0, YELLOW: 0, GREEN: 0 });
  return <Card><CardContent className="grid gap-4 lg:grid-cols-[1.5fr_repeat(4,minmax(100px,.5fr))]"><div><div className="flex flex-wrap gap-2"><Badge tone={data.route_validation_complete ? "positive" : "warning"}>{data.route_validation_complete ? "Routes validated" : "Validation pending"}</Badge>{data.plan_version ? <Badge>Plan v{data.plan_version}</Badge> : <Badge>No plan</Badge>}</div><p className="mt-3 text-sm text-slate-400">{data.message}</p></div><Metric label="Track sections" value={String(data.edges.length)} /><Metric label="Blocked" value={String(data.blocked_resources.length)} /><Metric label="Green" value={String(counts.GREEN)} /><Metric label="Red / Yellow" value={`${counts.RED} / ${counts.YELLOW}`} /></CardContent></Card>;
}

function NetworkCanvas({ data, selected }: { data: NetworkMonitor; selected: NetworkMovement | null }) {
  const nodeMap = useMemo(() => new Map(data.nodes.map((node) => [node.code, node])), [data.nodes]);
  const selectedPairs = new Set((selected?.path ?? []).slice(0, -1).map((node, index) => `${node}->${selected?.path[index + 1]}`));
  return <Card className="min-w-0 overflow-hidden"><CardHeader><div><CardTitle>Station topology</CardTitle><CardDescription>Arrows show permitted travel direction. Select a train to highlight its reserved path.</CardDescription></div><div className="flex gap-2"><Legend color="bg-cyan-300" text="Selected" /><Legend color="bg-rose-400" text="Blocked" /></div></CardHeader><CardContent className="overflow-x-auto p-2 sm:p-4"><svg role="img" aria-label="Interactive directed railway network" viewBox="0 0 960 410" className="min-h-[410px] min-w-[780px] w-full rounded-lg bg-slate-950/50"><defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" /></marker></defs>{data.edges.map((edge) => <EdgeLine key={edge.code} edge={edge} nodes={nodeMap} selected={selectedPairs.has(`${edge.from_node}->${edge.to_node}`)} />)}{data.nodes.map((node) => <NodeGlyph key={node.code} node={node} train={selected?.platform_code === node.code ? selected.train_identifier : null} />)}</svg></CardContent></Card>;
}

function EdgeLine({ edge, nodes, selected }: { edge: NetworkEdge; nodes: Map<string, NetworkNode>; selected: boolean }) {
  const start = nodes.get(edge.from_node); const end = nodes.get(edge.to_node); if (!start || !end) return null;
  const color = edge.blocked ? "#fb7185" : selected ? "#67e8f9" : "#334155";
  return <g className="text-slate-600"><line x1={start.x} y1={start.y} x2={end.x} y2={end.y} stroke={color} strokeWidth={selected ? 5 : 3} strokeDasharray={edge.blocked ? "8 6" : undefined} markerEnd="url(#arrow)" opacity={selected || edge.blocked ? 1 : .8}><title>{edge.code} · {edge.traversal_minutes} minutes · {edge.resource_group ?? "Independent resource"}</title></line></g>;
}

function NodeGlyph({ node, train }: { node: NetworkNode; train: string | null }) {
  const platform = node.node_type === "platform"; const switchNode = node.node_type === "switch";
  return <g><circle cx={node.x} cy={node.y} r={platform ? 14 : switchNode ? 11 : 9} fill={node.blocked ? "#881337" : platform ? "#0f766e" : switchNode ? "#a16207" : "#164e63"} stroke={node.blocked ? "#fb7185" : "#94a3b8"} strokeWidth="2"><title>{node.name} · {node.node_type}</title></circle><text x={node.x} y={node.y + (platform ? 29 : -16)} textAnchor="middle" fill="#cbd5e1" fontSize="11" fontFamily="ui-monospace, monospace">{node.code}</text>{train ? <g><rect x={node.x - 34} y={node.y - 34} width="68" height="17" rx="5" fill="#155e75" stroke="#67e8f9" /><text x={node.x} y={node.y - 22} textAnchor="middle" fill="#ecfeff" fontSize="10" fontWeight="600">{train}</text></g> : null}</g>;
}

function DecisionPanel({ movements, selected, onSelect }: { movements: NetworkMovement[]; selected: NetworkMovement | null; onSelect: (id: number) => void }) {
  return <Card className="overflow-hidden"><CardHeader><div><CardTitle>Decision details</CardTitle><CardDescription>Facts, route, reservations, and modeled constraints.</CardDescription></div>{selected ? <Indicator value={selected.indicator} /> : null}</CardHeader><CardContent className="space-y-5"><label className="block text-xs font-medium text-slate-400">Train<select className="mt-2 h-9 w-full rounded-md border border-slate-700 bg-slate-950/70 px-3 text-sm text-slate-200" value={selected?.train_id ?? ""} onChange={(event) => onSelect(Number(event.target.value))}><option value="" disabled>Select a train</option>{movements.map((item) => <option key={item.train_id} value={item.train_id}>{item.train_identifier} · {item.indicator}</option>)}</select></label>{selected ? <><div className="grid grid-cols-2 gap-4"><Metric label="Platform" value={selected.platform_code} /><Metric label="Decision" value={splitPredicate(selected.decision)} /><Metric label="Entry" value={selected.origin_node_code ?? "Missing"} /><Metric label="Exit" value={selected.destination_node_code ?? "Missing"} /></div><section><h3 className="flex items-center gap-2 text-xs font-semibold text-slate-300"><Waypoints className="size-3.5 text-cyan-300" />Selected route</h3><p className="mt-2 font-mono text-[11px] leading-5 text-slate-400">{selected.path.length ? selected.path.join(" → ") : "No route is reserved."}</p></section><section><h3 className="flex items-center gap-2 text-xs font-semibold text-slate-300"><GitBranch className="size-3.5 text-cyan-300" />Reservations</h3><div className="mt-2 max-h-48 space-y-2 overflow-y-auto">{selected.reservations.length ? selected.reservations.map((item, index) => <div key={`${item.resource_code}-${item.start_minute}-${index}`} className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-950/40 px-3 py-2"><div><p className="font-mono text-[11px] text-slate-300">{item.resource_code}</p><p className="text-[10px] capitalize text-slate-600">{item.resource_type}</p></div><span className="font-mono text-[10px] text-slate-400">{formatMinute(item.start_minute)}–{formatMinute(item.end_minute)}</span></div>) : <p className="text-xs text-amber-300">No reservation intervals are available.</p>}</div></section><div className="flex gap-2 border-t border-slate-800 pt-4 text-xs leading-5 text-slate-500"><Route className="mt-0.5 size-4 shrink-0" /><p>{selected.explanation}</p></div></> : <div className="grid min-h-60 place-items-center text-center text-sm text-slate-500"><div><TrainFront className="mx-auto mb-3 size-6" />Validate a dispatch plan, then select a train.</div></div>}</CardContent></Card>;
}

function Indicator({ value }: { value: NetworkMovement["indicator"] }) { const tone = value === "GREEN" ? "positive" : value === "RED" ? "critical" : "warning"; return <Badge tone={tone}><span className={`mr-1.5 size-1.5 rounded-full ${value === "GREEN" ? "bg-teal-300" : value === "RED" ? "bg-rose-300" : "bg-amber-300"}`} />{value}</Badge>; }
function Legend({ color, text }: { color: string; text: string }) { return <span className="flex items-center gap-1.5 text-[10px] text-slate-500"><span className={`size-2 rounded-full ${color}`} />{text}</span>; }
function Metric({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] uppercase tracking-[0.12em] text-slate-600">{label}</p><p className="mt-1 font-mono text-sm text-slate-200">{value}</p></div>; }
function formatMinute(value: number) { return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`; }
function splitPredicate(value: string) { return value.replace(/([a-z])([A-Z])/g, "$1 $2"); }
