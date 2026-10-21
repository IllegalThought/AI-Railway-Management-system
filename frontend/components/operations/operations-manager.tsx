"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowDownUp, ChevronRight, CirclePlus, Pencil, RefreshCw, Search, Trash2 } from "lucide-react";

import { TrainForm } from "@/components/operations/train-form";
import { useToast } from "@/components/toast-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Modal } from "@/components/ui/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, createTrain, deleteTrain, getPlatforms, getScenarios, getTrains, restoreScenario, updatePlatform, updateTrain, type Platform, type Scenario, type Train, type TrainInput } from "@/lib/api";

type SortKey = "identifier" | "arrival_minute" | "priority" | "service_status";
const inputClass = "h-9 rounded-md border border-[#C9D1D8] bg-[#F6F7F9] px-3 text-sm text-[#2D3A45] outline-none focus:border-[#36638A] focus:ring-2 focus:ring-[#36638A]/15";

export function OperationsManager() {
  const [trains, setTrains] = useState<Train[]>([]); const [platforms, setPlatforms] = useState<Platform[]>([]); const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [tab, setTab] = useState<"trains" | "platforms">("trains");
  const [search, setSearch] = useState(""); const [status, setStatus] = useState("all"); const [sortKey, setSortKey] = useState<SortKey>("arrival_minute"); const [descending, setDescending] = useState(false);
  const [selectedTrainId, setSelectedTrainId] = useState<number | null>(null); const [selectedPlatformId, setSelectedPlatformId] = useState<number | null>(null);
  const [formTrain, setFormTrain] = useState<Train | "new" | null>(null); const [deleteTarget, setDeleteTarget] = useState<Train | null>(null);
  const [scenarioKey, setScenarioKey] = useState("normal-traffic"); const [scenarioConfirm, setScenarioConfirm] = useState(false); const [busy, setBusy] = useState(false);
  const { toast } = useToast();

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true); setError("");
    try { const [nextTrains, nextPlatforms, nextScenarios] = await Promise.all([getTrains(), getPlatforms(), getScenarios()]); setTrains(nextTrains); setPlatforms(nextPlatforms); setScenarios(nextScenarios); setSelectedTrainId((current) => current && nextTrains.some((item) => item.id === current) ? current : nextTrains[0]?.id ?? null); setSelectedPlatformId((current) => current && nextPlatforms.some((item) => item.id === current) ? current : nextPlatforms[0]?.id ?? null); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Data management could not be loaded."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([getTrains(controller.signal), getPlatforms(controller.signal), getScenarios(controller.signal)])
      .then(([nextTrains, nextPlatforms, nextScenarios]) => {
        setTrains(nextTrains); setPlatforms(nextPlatforms); setScenarios(nextScenarios);
        setSelectedTrainId(nextTrains[0]?.id ?? null); setSelectedPlatformId(nextPlatforms[0]?.id ?? null);
      })
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError(caught instanceof ApiError ? caught.message : "Data management could not be loaded.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const filtered = useMemo(() => trains.filter((train) => train.identifier.toLowerCase().includes(search.toLowerCase()) && (status === "all" || train.service_status === status)).sort((a, b) => { const left = a[sortKey]; const right = b[sortKey]; const result = typeof left === "string" ? left.localeCompare(String(right)) : Number(left) - Number(right); return descending ? -result : result; }), [trains, search, status, sortKey, descending]);
  const selectedTrain = trains.find((item) => item.id === selectedTrainId) ?? null; const selectedPlatform = platforms.find((item) => item.id === selectedPlatformId) ?? null;

  async function saveTrain(data: TrainInput) {
    const result = formTrain === "new" ? await createTrain(data) : await updateTrain(formTrain!.id, data);
    setTrains((current) => formTrain === "new" ? [...current, result.train] : current.map((item) => item.id === result.train.id ? result.train : item)); setSelectedTrainId(result.train.id); setFormTrain(null);
    toast({ title: formTrain === "new" ? "Train added" : "Train updated", description: scheduleMessage(result.schedule_validation_required), tone: "success" });
  }

  async function confirmDelete() {
    if (!deleteTarget) return; setBusy(true);
    try { const result = await deleteTrain(deleteTarget.id); setTrains((current) => current.filter((item) => item.id !== deleteTarget.id)); setSelectedTrainId(null); setDeleteTarget(null); toast({ title: "Train deleted", description: scheduleMessage(result.schedule_validation_required), tone: "success" }); }
    catch (caught) { toast({ title: "Train could not be deleted", description: caught instanceof ApiError ? caught.message : "Please try again.", tone: "info" }); }
    finally { setBusy(false); }
  }

  async function changeAvailability(platform: Platform, available: boolean, reason: string | null) {
    setBusy(true);
    try { const result = await updatePlatform(platform.id, { is_available: available, unavailable_reason: available ? null : reason }); setPlatforms((current) => current.map((item) => item.id === platform.id ? result.platform : item)); toast({ title: available ? "Platform opened" : "Platform marked unavailable", description: scheduleMessage(result.schedule_validation_required), tone: "success" }); }
    catch (caught) { toast({ title: "Platform could not be updated", description: caught instanceof ApiError ? caught.details[0]?.message?.replace(/^Value error, /, "") ?? caught.message : "Please try again.", tone: "info" }); }
    finally { setBusy(false); }
  }

  async function confirmScenarioRestore() {
    setBusy(true);
    try { const result = await restoreScenario(scenarioKey); setScenarioConfirm(false); await load(true); toast({ title: "Scenario restored", description: result.message, tone: "success" }); }
    catch (caught) { toast({ title: "Scenario could not be restored", description: caught instanceof ApiError ? caught.message : "Please try again.", tone: "info" }); }
    finally { setBusy(false); }
  }

  return <div className="animate-[toast-in_220ms_ease-out] space-y-6">
    <div className="flex flex-wrap items-center justify-end gap-2"><select aria-label="Scenario" className={inputClass} value={scenarioKey} onChange={(e) => setScenarioKey(e.target.value)}>{scenarios.map((item) => <option key={item.key} value={item.key}>{item.name}</option>)}</select><Button variant="outline" onClick={() => setScenarioConfirm(true)} disabled={loading || busy}><RefreshCw className="size-3.5" />Restore scenario</Button><Button onClick={() => setFormTrain("new")} disabled={loading}><CirclePlus className="size-4" />Add train</Button></div>
    <div role="tablist" className="flex w-fit rounded-lg border border-[#DFE4E8] bg-white p-1"><button role="tab" aria-selected={tab === "trains"} onClick={() => setTab("trains")} className={`rounded-md px-4 py-2 text-xs font-medium ${tab === "trains" ? "bg-[#36638A] text-white" : "text-[#687581] hover:text-[#2D3A45]"}`}>Trains <span className="ml-1 text-[#52616F]">{trains.length}</span></button><button role="tab" aria-selected={tab === "platforms"} onClick={() => setTab("platforms")} className={`rounded-md px-4 py-2 text-xs font-medium ${tab === "platforms" ? "bg-[#36638A] text-white" : "text-[#687581] hover:text-[#2D3A45]"}`}>Platforms <span className="ml-1 text-[#52616F]">{platforms.length}</span></button></div>
    {loading ? <LoadingState /> : error ? <Card className="p-8 text-center"><AlertTriangle className="mx-auto size-5 text-[#956B20]" /><p className="mt-3 text-sm text-[#34424F]">{error}</p><Button className="mt-4" variant="outline" onClick={() => void load(true)}>Try again</Button></Card> : tab === "trains" ? <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]"><Card><CardHeader className="flex-col sm:flex-row sm:items-center"><div><CardTitle>Train register</CardTitle><CardDescription>{filtered.length} of {trains.length} trains</CardDescription></div><div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row"><label className="relative"><Search className="absolute left-3 top-2.5 size-3.5 text-[#687581]" /><input aria-label="Search trains" className={`${inputClass} w-full pl-9 sm:w-48`} placeholder="Search identifier" value={search} onChange={(e) => setSearch(e.target.value)} /></label><select aria-label="Filter by status" className={inputClass} value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">All statuses</option><option value="scheduled">Scheduled</option><option value="delayed">Delayed</option><option value="cancelled">Cancelled</option></select></div></CardHeader><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-[#F6F7F9] text-[10px] uppercase tracking-[0.12em] text-[#687581]"><tr><SortHeader label="Train" value="identifier" current={sortKey} onSort={setSortKey} /><SortHeader label="Arrival" value="arrival_minute" current={sortKey} onSort={setSortKey} /><th className="px-4 py-3">Departure</th><SortHeader label="Priority" value="priority" current={sortKey} onSort={setSortKey} /><SortHeader label="Status" value="service_status" current={sortKey} onSort={setSortKey} /><th className="px-4 py-3 text-right"><button onClick={() => setDescending((value) => !value)} aria-label="Reverse sort"><ArrowDownUp className="size-3.5" /></button></th></tr></thead><tbody className="divide-y divide-[#E5E9EC]">{filtered.map((train) => <tr key={train.id} onClick={() => setSelectedTrainId(train.id)} className={`cursor-pointer transition hover:bg-[#EDF0F2] ${selectedTrainId === train.id ? "bg-[#EDF3F7]" : ""}`}><td className="px-4 py-3 font-medium text-[#2D3A45]">{train.identifier}</td><td className="px-4 py-3 font-mono text-xs text-[#52616F]">{formatMinute(train.arrival_minute)}</td><td className="px-4 py-3 font-mono text-xs text-[#52616F]">{formatMinute(train.departure_minute)}</td><td className="px-4 py-3 text-[#52616F]">P{train.priority}</td><td className="px-4 py-3"><StatusBadge status={train.service_status} delay={train.delay_minutes} /></td><td className="px-4 py-3 text-right"><ChevronRight className="ml-auto size-4 text-[#7C8994]" /></td></tr>)}</tbody></table>{filtered.length === 0 ? <div className="py-16 text-center text-sm text-[#687581]">No trains match the current filters.</div> : null}</div></Card><TrainDetail train={selectedTrain} onEdit={() => selectedTrain && setFormTrain(selectedTrain)} onDelete={() => selectedTrain && setDeleteTarget(selectedTrain)} /></div> : <PlatformView key={selectedPlatform?.id ?? "none"} platforms={platforms} selected={selectedPlatform} onSelect={setSelectedPlatformId} onAvailability={changeAvailability} busy={busy} />}
    <Modal open={formTrain !== null} title={formTrain === "new" ? "Add train" : "Edit train"} onClose={() => setFormTrain(null)}>{formTrain ? <TrainForm key={formTrain === "new" ? "new" : formTrain.id} train={formTrain === "new" ? undefined : formTrain} platforms={platforms} onSubmit={saveTrain} onCancel={() => setFormTrain(null)} /> : null}</Modal>
    <Modal open={deleteTarget !== null} title="Delete train" onClose={() => setDeleteTarget(null)}><div className="p-5"><p className="text-sm leading-6 text-[#34424F]">Delete <strong className="text-[#202B36]">{deleteTarget?.identifier}</strong>? Any existing assignments for this train will also be removed.</p><div className="mt-5 flex justify-end gap-2"><Button variant="ghost" onClick={() => setDeleteTarget(null)}>Cancel</Button><Button className="bg-rose-400 text-slate-950 hover:bg-rose-300" onClick={confirmDelete} disabled={busy}>{busy ? "Deleting…" : "Delete train"}</Button></div></div></Modal>
    <Modal open={scenarioConfirm} title="Restore demo scenario" onClose={() => setScenarioConfirm(false)}><div className="p-5"><p className="text-sm leading-6 text-[#34424F]">Restore <strong className="text-[#202B36]">{scenarios.find((item) => item.key === scenarioKey)?.name}</strong>? Train, platform, incident, and activity data in this workspace will return to the selected scenario.</p><div className="mt-5 flex justify-end gap-2"><Button variant="ghost" onClick={() => setScenarioConfirm(false)}>Cancel</Button><Button onClick={confirmScenarioRestore} disabled={busy}>{busy ? "Restoring…" : "Restore scenario"}</Button></div></div></Modal>
  </div>;
}

function TrainDetail({ train, onEdit, onDelete }: { train: Train | null; onEdit: () => void; onDelete: () => void }) { if (!train) return <Card className="grid min-h-80 place-items-center text-sm text-[#687581]">Select a train to view details.</Card>; return <Card><CardHeader><div><CardTitle>{train.identifier}</CardTitle><CardDescription>Train details</CardDescription></div><StatusBadge status={train.service_status} delay={train.delay_minutes} /></CardHeader><CardContent className="space-y-5"><div className="grid grid-cols-2 gap-4"><Detail label="Operating window" value={`${formatMinute(train.arrival_minute)}–${formatMinute(train.departure_minute)}`} /><Detail label="Minimum dwell" value={`${train.minimum_dwell_minutes} min`} /><Detail label="Length" value={`${train.length_meters} m`} /><Detail label="Priority" value={`P${train.priority}`} /><Detail label="Platform type" value={train.required_platform_type ?? "Any"} /><Detail label="Last updated" value={new Date(train.updated_at).toLocaleDateString()} /></div><div><p className="text-[10px] uppercase tracking-[0.12em] text-[#7C8994]">Compatible platforms</p><div className="mt-2 flex flex-wrap gap-1.5">{train.compatible_platform_codes.length ? train.compatible_platform_codes.map((code) => <Badge key={code}>{code}</Badge>) : <span className="text-xs text-[#687581]">No compatibility assigned</span>}</div></div><div className="flex gap-2 border-t border-[#DFE4E8] pt-4"><Button className="flex-1" variant="outline" onClick={onEdit}><Pencil className="size-3.5" />Edit</Button><Button variant="ghost" onClick={onDelete} aria-label={`Delete ${train.identifier}`}><Trash2 className="size-4 text-[#A14343]" /></Button></div><p className="text-[11px] leading-5 text-[#8A641F]">Changes affecting a ready scheduling plan return that plan to draft for later validation.</p></CardContent></Card>; }

function PlatformView({ platforms, selected, onSelect, onAvailability, busy }: { platforms: Platform[]; selected: Platform | null; onSelect: (id: number) => void; onAvailability: (platform: Platform, available: boolean, reason: string | null) => Promise<void>; busy: boolean }) { const [reason, setReason] = useState(selected?.unavailable_reason ?? ""); return <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{platforms.map((platform) => <button key={platform.id} onClick={() => onSelect(platform.id)} className={`rounded-xl border p-5 text-left transition ${selected?.id === platform.id ? "border-[#7E9DB6] bg-[#EDF3F7]" : "border-[#DFE4E8] bg-white hover:border-[#C9D1D8]"}`}><div className="flex items-center justify-between"><span className="font-mono text-lg font-semibold text-[#202B36]">{platform.code}</span><Badge tone={platform.is_available ? "positive" : "warning"}>{platform.is_available ? "Available" : "Unavailable"}</Badge></div><p className="mt-4 text-xs text-[#687581]">{platform.platform_type} · {platform.length_meters} m</p><p className="mt-1 text-xs text-[#7C8994]">{platform.compatible_train_count} compatible trains</p></button>)}</div>{selected ? <Card><CardHeader><div><CardTitle>Platform {selected.code}</CardTitle><CardDescription>Availability and operating constraints</CardDescription></div><Badge tone={selected.is_available ? "positive" : "warning"}>{selected.is_available ? "Available" : "Unavailable"}</Badge></CardHeader><CardContent className="space-y-5"><div className="grid grid-cols-2 gap-4"><Detail label="Type" value={selected.platform_type} /><Detail label="Length" value={`${selected.length_meters} m`} /><Detail label="Clearance" value={`${selected.clearance_minutes} min`} /><Detail label="Compatible trains" value={String(selected.compatible_train_count)} /></div><div className="border-t border-[#DFE4E8] pt-4">{!selected.is_available ? <div><label className="text-xs text-[#52616F]">Unavailable reason<input className={`${inputClass} mt-1.5 w-full`} value={reason} onChange={(e) => setReason(e.target.value)} /></label><Button className="mt-3 w-full" variant="outline" disabled={busy} onClick={() => void onAvailability(selected, true, null)}>Mark available</Button></div> : <div><label className="text-xs text-[#52616F]">Reason for unavailability<input className={`${inputClass} mt-1.5 w-full`} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Required before closing" /></label><Button className="mt-3 w-full" variant="outline" disabled={busy || !reason.trim()} onClick={() => void onAvailability(selected, false, reason.trim())}>Mark unavailable</Button></div>}</div></CardContent></Card> : null}</div>; }

function SortHeader({ label, value, current, onSort }: { label: string; value: SortKey; current: SortKey; onSort: (value: SortKey) => void }) { return <th className="px-4 py-3"><button className={current === value ? "text-[#36638A]" : ""} onClick={() => onSort(value)}>{label}</button></th>; }
function Detail({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] uppercase tracking-[0.12em] text-[#7C8994]">{label}</p><p className="mt-1 text-sm text-[#34424F]">{value}</p></div>; }
function StatusBadge({ status, delay }: { status: Train["service_status"]; delay: number }) { return <Badge tone={status === "scheduled" ? "positive" : status === "delayed" ? "warning" : "critical"}>{status === "delayed" ? `Delayed ${delay} min` : status[0].toUpperCase() + status.slice(1)}</Badge>; }
function LoadingState() { return <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]"><Skeleton className="h-[540px] rounded-xl" /><Skeleton className="h-96 rounded-xl" /></div>; }
function formatMinute(value: number) { return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`; }
function scheduleMessage(required: boolean) { return required ? "A related scheduling plan returned to draft and requires later validation." : "The isolated workspace has been updated."; }
