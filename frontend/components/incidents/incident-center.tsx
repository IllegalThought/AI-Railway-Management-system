"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, GitCompareArrows, Plus, RefreshCw, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { Modal } from "@/components/ui/modal";
import { ApiError, applySchedule, createIncident, getIncidents, getNetworkMonitor, getPlatforms, getSimulationState, getTrains, replanIncident, updateIncidentStatus, type Incident, type IncidentType, type NetworkMonitor, type Platform, type ReplanResult, type SimulationState, type Train } from "@/lib/api";

const formatMinute = (minute: number) => `${String(Math.floor(minute / 60) % 24).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
const labels: Record<IncidentType, string> = { train_arrival_delay: "Train arrival delay", train_departure_delay: "Train departure delay", platform_closure: "Platform closure", track_blockage: "Track blockage", junction_closure: "Junction closure", new_train_request: "New train request" };

export function IncidentCenter() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [trains, setTrains] = useState<Train[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [network, setNetwork] = useState<NetworkMonitor | null>(null);
  const [simulation, setSimulation] = useState<SimulationState | null>(null);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [comparison, setComparison] = useState<ReplanResult | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [incidentData, trainData, platformData, networkData, simulationData] = await Promise.all([getIncidents(), getTrains(), getPlatforms(), getNetworkMonitor(), getSimulationState()]);
      setIncidents(incidentData); setTrains(trainData); setPlatforms(platformData); setNetwork(networkData); setSimulation(simulationData); setError("");
      setSelected((current) => current ? incidentData.find((item) => item.id === current.id) ?? incidentData[0] ?? null : incidentData[0] ?? null);
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Incident data could not be loaded."); }
    finally { setBusy(false); }
  }, []);
  // Initial API synchronization is intentionally effect-driven.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [load]);

  async function replan() {
    if (!selected || !simulation?.active_plan_id || !simulation.active_plan_version) { setError("Apply a validated plan before triggering incident replanning."); return; }
    setBusy(true);
    try { setComparison(await replanIncident({ incident_id: selected.id, base_plan_id: simulation.active_plan_id, base_plan_version: simulation.active_plan_version, expected_simulation_revision: simulation.revision })); setError(""); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Replanning failed."); await load(); }
    finally { setBusy(false); }
  }

  async function applyRevised() {
    if (!comparison?.valid) return;
    setBusy(true);
    try { await applySchedule(comparison.revised_plan); setComparison(null); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "The revised plan could not be applied."); }
    finally { setBusy(false); }
  }

  async function setStatus(status: Incident["status"]) {
    if (!selected) return;
    setBusy(true);
    try { await updateIncidentStatus(selected.id, status); await load(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Incident status could not be updated."); }
    finally { setBusy(false); }
  }

  return <div className="space-y-6">
    <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><p className="text-[11px] font-medium uppercase tracking-[0.18em] text-cyan-400/70">Operational disruption workflow</p><h1 className="mt-2 text-xl font-semibold text-white sm:text-2xl">Incident Center</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Record disruptions, inspect affected services, and produce validated schedule and route revisions.</p></div><div className="flex gap-2"><Button variant="outline" onClick={() => void load()} disabled={busy}><RefreshCw className={`size-4 ${busy ? "animate-spin" : ""}`} />Refresh</Button><Button onClick={() => setFormOpen(true)}><Plus className="size-4" />Report incident</Button></div></div>
    {error ? <div className="rounded-lg border border-red-900/60 bg-red-950/30 px-4 py-3 text-sm text-red-200">{error}</div> : null}
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]"><Card><CardHeader><div><CardTitle>Incident register</CardTitle><CardDescription>{incidents.length} persisted incident{incidents.length === 1 ? "" : "s"} in this isolated workspace.</CardDescription></div></CardHeader><CardContent><DataTable columns={[{ key: "incident", label: "Incident" }, { key: "resource", label: "Resource" }, { key: "window", label: "Window" }, { key: "severity", label: "Severity" }, { key: "status", label: "Status" }]} rows={incidents.map((item) => ({ incident: <button className="text-left font-medium text-slate-200 hover:text-cyan-300" onClick={() => { setSelected(item); setComparison(null); }}>{item.title}</button>, resource: <span className="font-mono text-xs">{item.affected_resource}</span>, window: <span className="text-xs">{formatMinute(item.start_minute)} · {item.duration_minutes} min</span>, severity: <Badge tone={item.severity === "critical" || item.severity === "high" ? "danger" : item.severity === "medium" ? "warning" : "neutral"}>{item.severity}</Badge>, status: <span className="capitalize">{item.status}</span> }))} emptyTitle="No incidents reported" emptyDescription="Use Report incident to introduce an operational disruption into this simulation workspace." /></CardContent></Card>
      <Card><CardHeader><div><CardTitle>Impact and response</CardTitle><CardDescription>Selected incident and replanning controls.</CardDescription></div></CardHeader><CardContent>{selected ? <div className="space-y-5"><div><div className="flex items-center justify-between gap-3"><Badge tone="warning">{labels[selected.incident_type]}</Badge><span className="text-xs capitalize text-slate-500">{selected.status}</span></div><h3 className="mt-3 text-sm font-semibold text-slate-100">{selected.title}</h3><p className="mt-2 text-xs leading-5 text-slate-500">{selected.description}</p></div><div className="grid grid-cols-2 gap-3"><Detail label="Resource" value={selected.affected_resource} /><Detail label="Affected trains" value={String(selected.affected_train_ids.length)} /><Detail label="Starts" value={formatMinute(selected.start_minute)} /><Detail label="Duration" value={`${selected.duration_minutes} min`} /></div><div className="flex flex-wrap gap-2"><Button onClick={() => void replan()} disabled={busy || selected.status === "resolved"}><Sparkles className="size-4" />Run AI replan</Button>{selected.status === "open" ? <Button variant="outline" onClick={() => void setStatus("monitoring")}>Monitor</Button> : null}{selected.status !== "resolved" ? <Button variant="ghost" onClick={() => void setStatus("resolved")}>Resolve</Button> : null}</div><p className="border-t border-slate-800 pt-4 text-xs leading-5 text-slate-600">Completed and already-started route movements are non-revocable. Every revised plan is independently checked for platform, route, and resource conflicts before it can be applied.</p></div> : <p className="py-16 text-center text-sm text-slate-500">Select an incident to inspect its impact.</p>}</CardContent></Card></div>
    {comparison ? <Comparison result={comparison} busy={busy} onApply={applyRevised} /> : null}
    <IncidentForm open={formOpen} onClose={() => setFormOpen(false)} trains={trains} platforms={platforms} network={network} currentMinute={simulation?.current_minute ?? 0} onCreated={async (incident) => { setFormOpen(false); await load(); setSelected(incident); }} onError={setError} />
  </div>;
}

function Comparison({ result, busy, onApply }: { result: ReplanResult; busy: boolean; onApply: () => void }) {
  const changed = result.changes.filter((item) => item.change !== "Unchanged");
  return <Card><CardHeader><div><CardTitle className="flex items-center gap-2"><GitCompareArrows className="size-4 text-cyan-300" />Before and after</CardTitle><CardDescription>Active plan v{result.base_plan.version} compared with incident replan v{result.revised_plan.version}.</CardDescription></div>{result.valid ? <Button onClick={onApply} disabled={busy}><CheckCircle2 className="size-4" />Apply revised plan</Button> : null}</CardHeader><CardContent className="space-y-4">{!result.valid ? <div className="flex gap-3 rounded-lg border border-red-900/60 bg-red-950/20 p-4 text-sm text-red-200"><AlertTriangle className="mt-0.5 size-4 shrink-0" /><div><p className="font-medium">No valid solution</p><p className="mt-1 text-xs leading-5 text-red-300/70">{result.infeasible_reason}</p></div></div> : <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-3 text-xs text-emerald-200">Validated revised plan ready. {result.preserved_train_ids.length} committed movement(s) were preserved.</div>}<DataTable columns={[{ key: "train", label: "Train and rationale" }, { key: "change", label: "Decision" }, { key: "before", label: "Before" }, { key: "after", label: "After" }]} rows={changed.map((item) => ({ train: <div><span className="font-mono text-xs">{item.train_identifier}</span><p className="mt-1 max-w-md text-[11px] leading-4 text-slate-500">{item.reason}</p></div>, change: <Badge tone={item.change === "Preserved" ? "positive" : item.change === "Unassigned" ? "danger" : "warning"}>{item.change}</Badge>, before: item.before ? `${item.before.platform_code} · ${formatMinute(item.before.occupancy_start_minute)}` : "—", after: item.after ? `${item.after.platform_code} · ${formatMinute(item.after.occupancy_start_minute)}` : "—" }))} emptyTitle="No schedule changes" emptyDescription="The revised plan matches the active allocation." /></CardContent></Card>;
}

function IncidentForm({ open, onClose, trains, platforms, network, currentMinute, onCreated, onError }: { open: boolean; onClose: () => void; trains: Train[]; platforms: Platform[]; network: NetworkMonitor | null; currentMinute: number; onCreated: (incident: Incident) => Promise<void>; onError: (message: string) => void }) {
  const [type, setType] = useState<IncidentType>("train_arrival_delay");
  const [resource, setResource] = useState("RA-101");
  const [duration, setDuration] = useState(10);
  const [severity, setSeverity] = useState<Incident["severity"]>("medium");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const options = useMemo(() => type.includes("train_") && type !== "new_train_request" ? trains.map((item) => item.identifier) : type === "platform_closure" ? platforms.map((item) => item.code) : type === "track_blockage" ? Array.from(new Set(network?.edges.flatMap((item) => [item.code, ...(item.resource_group ? [item.resource_group] : [])]) ?? [])) : type === "junction_closure" ? network?.nodes.filter((item) => item.node_type === "junction" || item.node_type === "switch").map((item) => item.code) ?? [] : [], [network, platforms, trains, type]);
  const selectedResource = type === "new_train_request"
    ? (resource && !trains.some((item) => item.identifier === resource) ? resource : "EXTRA-01")
    : (options.includes(resource) ? resource : options[0] ?? "");
  async function submit(event: FormEvent) {
    event.preventDefault(); setSubmitting(true);
    try {
      const newTrain = type === "new_train_request" ? { identifier: selectedResource, priority: 3, arrival_minute: currentMinute + 30, departure_minute: currentMinute + 46, minimum_dwell_minutes: 10, length_meters: 200, required_platform_type: "passenger", compatible_platform_codes: platforms.filter((item) => item.length_meters >= 200).map((item) => item.code), service_status: "scheduled" as const, delay_minutes: 0, origin_node_code: "ENTRY-W", destination_node_code: "EXIT-E" } : undefined;
      const created = await createIncident({ incident_type: type, affected_resource: selectedResource, start_minute: currentMinute, duration_minutes: duration, severity, description, ...(newTrain ? { new_train: newTrain } : {}) });
      setDescription(""); await onCreated(created);
    } catch (caught) { onError(caught instanceof ApiError ? caught.message : "Incident creation failed."); }
    finally { setSubmitting(false); }
  }
  return <Modal open={open} onClose={onClose} title="Report operational incident" description="The incident will mutate only this isolated synthetic workspace.">
    <form className="space-y-4 p-5" onSubmit={submit}>
      <Field label="Incident type"><select value={type} onChange={(event) => { setType(event.target.value as IncidentType); setResource(""); }} className="input">{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
      <Field label={type === "new_train_request" ? "New train identifier" : "Affected resource"}>{type === "new_train_request" ? <input className="input" value={selectedResource} onChange={(event) => setResource(event.target.value)} required /> : <select className="input" value={selectedResource} onChange={(event) => setResource(event.target.value)} required>{options.map((item) => <option key={item}>{item}</option>)}</select>}</Field>
      <div className="grid grid-cols-2 gap-4"><Field label="Duration (minutes)"><input className="input" type="number" min={1} max={1440} value={duration} onChange={(event) => setDuration(Number(event.target.value))} /></Field><Field label="Severity"><select className="input" value={severity} onChange={(event) => setSeverity(event.target.value as Incident["severity"])}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></Field></div>
      <Field label="Description"><textarea className="input min-h-24 py-2" value={description} onChange={(event) => setDescription(event.target.value)} minLength={1} maxLength={1000} required /></Field>
      {type === "new_train_request" ? <p className="text-xs leading-5 text-slate-500">The request creates a passenger train 30 minutes from the current simulation time with compatible modeled platforms and standard west-to-east routing.</p> : null}
      <div className="flex justify-end gap-2 border-t border-slate-800 pt-4"><Button type="button" variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" disabled={submitting || !selectedResource || !description}>{submitting ? "Recording…" : "Record incident"}</Button></div>
    </form>
  </Modal>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block text-xs font-medium text-slate-400">{label}<div className="mt-2">{children}</div></label>; }
function Detail({ label, value }: { label: string; value: string }) { return <div className="rounded-md border border-slate-800 bg-slate-950/30 p-3"><p className="text-[10px] uppercase tracking-wider text-slate-600">{label}</p><p className="mt-1 font-mono text-xs text-slate-300">{value}</p></div>; }
