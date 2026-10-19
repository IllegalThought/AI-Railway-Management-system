import type { Metadata } from "next";
import { SectionPage } from "@/components/section-page";
export const metadata: Metadata = { title: "Network Monitor" };
export default function Page() { return <SectionPage title="Network Monitor" description="Review network topology, resource capacity, and route availability when graph services are implemented." />; }
