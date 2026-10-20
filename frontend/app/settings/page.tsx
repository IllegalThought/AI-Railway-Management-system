import type { Metadata } from "next";
import { SystemStatus } from "@/components/settings/system-status";
export const metadata: Metadata = { title: "System Status" };
export default function Page() { return <SystemStatus />; }
