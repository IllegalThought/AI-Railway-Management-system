import type { Metadata } from "next";
import { SectionPage } from "@/components/section-page";
export const metadata: Metadata = { title: "Incident Center" };
export default function Page() { return <SectionPage title="Incident Center" description="Track operational disruptions, severity, ownership, and resolution status from one workspace." />; }
