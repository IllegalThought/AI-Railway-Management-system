"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, type Platform, type Train, type TrainInput, type TrainStatus } from "@/lib/api";

type FormState = {
  identifier: string; priority: string; arrival: string; departure: string; dwell: string; length: string;
  platformType: string; compatible: string[]; status: TrainStatus; delay: string;
  origin: string; destination: string;
};

function minuteToTime(value: number) { return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`; }
function timeToMinute(value: string) { const [hours, minutes] = value.split(":").map(Number); return hours * 60 + minutes; }

function initialState(train?: Train): FormState {
  return train ? { identifier: train.identifier, priority: String(train.priority), arrival: minuteToTime(train.arrival_minute), departure: minuteToTime(train.departure_minute), dwell: String(train.minimum_dwell_minutes), length: String(train.length_meters), platformType: train.required_platform_type ?? "", compatible: train.compatible_platform_codes, status: train.service_status, delay: String(train.delay_minutes), origin: train.origin_node_code ?? "ENTRY-W", destination: train.destination_node_code ?? "EXIT-E" } : { identifier: "", priority: "3", arrival: "08:00", departure: "08:15", dwell: "10", length: "220", platformType: "passenger", compatible: [], status: "scheduled", delay: "0", origin: "ENTRY-W", destination: "EXIT-E" };
}

const inputClass = "mt-1.5 h-9 w-full rounded-md border border-[#C9D1D8] bg-[#F6F7F9] px-3 text-sm text-[#2D3A45] outline-none transition focus:border-[#36638A] focus:ring-2 focus:ring-[#36638A]/15";

export function TrainForm({ train, platforms, onSubmit, onCancel }: { train?: Train; platforms: Platform[]; onSubmit: (data: TrainInput) => Promise<void>; onCancel: () => void }) {
  const [form, setForm] = useState(() => initialState(train));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (!form.identifier.trim()) nextErrors.identifier = "Train identifier is required.";
    const arrival = timeToMinute(form.arrival); const departure = timeToMinute(form.departure); const dwell = Number(form.dwell);
    if (departure <= arrival) nextErrors.departure_minute = "Departure must be after arrival.";
    if (departure - arrival < dwell) nextErrors.minimum_dwell_minutes = "The operating window must include the minimum dwell time.";
    if (form.status === "delayed" && Number(form.delay) <= 0) nextErrors.delay_minutes = "Enter a positive delay for a delayed train.";
    if (Object.keys(nextErrors).length) { setErrors(nextErrors); return; }
    setBusy(true); setErrors({});
    try {
      await onSubmit({ identifier: form.identifier.trim(), priority: Number(form.priority), arrival_minute: arrival, departure_minute: departure, minimum_dwell_minutes: dwell, length_meters: Number(form.length), required_platform_type: form.platformType.trim() || null, compatible_platform_codes: form.compatible, service_status: form.status, delay_minutes: form.status === "delayed" ? Number(form.delay) : 0, origin_node_code: form.origin, destination_node_code: form.destination });
    } catch (error) {
      if (error instanceof ApiError) {
        const fieldErrors = Object.fromEntries(error.details.map((detail) => [detail.field ?? "form", detail.message.replace(/^Value error, /, "")]));
        setErrors(Object.keys(fieldErrors).length ? fieldErrors : { form: error.message });
      } else setErrors({ form: "The train could not be saved." });
    } finally { setBusy(false); }
  }

  return <form onSubmit={submit} className="space-y-5 p-5">
    {errors.form ? <p role="alert" className="rounded-md border border-rose-400/20 bg-rose-400/10 px-3 py-2 text-xs text-[#A14343]">{errors.form}</p> : null}
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label="Train identifier" error={errors.identifier}><input className={inputClass} value={form.identifier} onChange={(e) => set("identifier", e.target.value)} placeholder="RA-121" /></Field>
      <Field label="Service status" error={errors.service_status}><select className={inputClass} value={form.status} onChange={(e) => set("status", e.target.value as TrainStatus)}><option value="scheduled">Scheduled</option><option value="delayed">Delayed</option><option value="cancelled">Cancelled</option></select></Field>
      <Field label="Arrival time" error={errors.arrival_minute}><input type="time" className={inputClass} value={form.arrival} onChange={(e) => set("arrival", e.target.value)} /></Field>
      <Field label="Departure time" error={errors.departure_minute}><input type="time" className={inputClass} value={form.departure} onChange={(e) => set("departure", e.target.value)} /></Field>
      <Field label="Minimum dwell (minutes)" error={errors.minimum_dwell_minutes}><input type="number" min="1" className={inputClass} value={form.dwell} onChange={(e) => set("dwell", e.target.value)} /></Field>
      <Field label="Train length (meters)" error={errors.length_meters}><input type="number" min="1" className={inputClass} value={form.length} onChange={(e) => set("length", e.target.value)} /></Field>
      <Field label="Priority" error={errors.priority}><select className={inputClass} value={form.priority} onChange={(e) => set("priority", e.target.value)}>{[1,2,3,4,5].map((value) => <option key={value} value={value}>{value} — {value === 1 ? "Highest" : value === 5 ? "Lowest" : "Standard"}</option>)}</select></Field>
      <Field label="Required platform type" error={errors.required_platform_type}><input className={inputClass} value={form.platformType} onChange={(e) => set("platformType", e.target.value)} /></Field>
      <Field label="Entry point" error={errors.origin_node_code}><select className={inputClass} value={form.origin} onChange={(e) => set("origin", e.target.value)}><option value="ENTRY-W">West Entry</option><option value="ENTRY-E">East Entry</option></select></Field>
      <Field label="Exit point" error={errors.destination_node_code}><select className={inputClass} value={form.destination} onChange={(e) => set("destination", e.target.value)}><option value="EXIT-E">East Exit</option><option value="EXIT-W">West Exit</option></select></Field>
      {form.status === "delayed" ? <Field label="Delay (minutes)" error={errors.delay_minutes}><input type="number" min="1" className={inputClass} value={form.delay} onChange={(e) => set("delay", e.target.value)} /></Field> : null}
    </div>
    <fieldset><legend className="text-xs font-medium text-[#52616F]">Compatible platforms</legend><div className="mt-2 grid gap-2 sm:grid-cols-3">{platforms.map((platform) => <label key={platform.id} className="flex items-center gap-2 rounded-md border border-[#DFE4E8] bg-[#F8F9FA] px-3 py-2 text-xs text-[#34424F]"><input type="checkbox" className="accent-[#36638A]" checked={form.compatible.includes(platform.code)} onChange={(e) => set("compatible", e.target.checked ? [...form.compatible, platform.code] : form.compatible.filter((code) => code !== platform.code))} />{platform.code}<span className="ml-auto text-[#7C8994]">{platform.length_meters} m</span></label>)}</div>{errors.compatible_platform_codes ? <p className="mt-1.5 text-xs text-[#A14343]">{errors.compatible_platform_codes}</p> : null}</fieldset>
    <div className="flex justify-end gap-2 border-t border-[#DFE4E8] pt-4"><Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? "Saving…" : train ? "Save changes" : "Add train"}</Button></div>
  </form>;
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) { return <label className="text-xs font-medium text-[#52616F]">{label}{children}{error ? <span className="mt-1.5 block text-xs font-normal text-[#A14343]">{error}</span> : null}</label>; }
