import type { Metadata } from "next";
import { IncidentCenter } from "@/components/incidents/incident-center";
export const metadata: Metadata = { title: "Incident Center" };
export default function Page() { return <IncidentCenter />; }
