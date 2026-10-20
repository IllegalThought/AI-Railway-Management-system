import type { Metadata } from "next";
import { PerformanceAnalytics } from "@/components/analytics/performance-analytics";
export const metadata: Metadata = { title: "Performance Analytics" };
export default function Page() { return <PerformanceAnalytics />; }
