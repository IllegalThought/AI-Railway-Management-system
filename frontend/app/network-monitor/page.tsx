import type { Metadata } from "next";
import { NetworkMonitorView } from "@/components/network/network-monitor";
export const metadata: Metadata = { title: "Network Monitor" };
export default function Page() { return <NetworkMonitorView />; }
