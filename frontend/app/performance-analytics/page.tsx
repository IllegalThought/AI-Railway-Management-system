import type { Metadata } from "next";
import { SectionPage } from "@/components/section-page";
export const metadata: Metadata = { title: "Performance Analytics" };
export default function Page() { return <SectionPage title="Performance Analytics" description="Analyze service reliability and resource utilization after verified performance data is available." />; }
