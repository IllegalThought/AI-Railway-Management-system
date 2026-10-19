import type { Metadata } from "next";
import { SectionPage } from "@/components/section-page";
export const metadata: Metadata = { title: "Dispatch Board" };
export default function Page() { return <SectionPage title="Dispatch Board" description="Coordinate train movements and platform assignments from a single operational workspace." />; }
