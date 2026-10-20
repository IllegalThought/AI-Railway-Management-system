import type { Metadata } from "next";
import { LiveOperations } from "@/components/live/live-operations";
export const metadata: Metadata = { title: "Live Operations" };
export default function Page() { return <LiveOperations />; }
