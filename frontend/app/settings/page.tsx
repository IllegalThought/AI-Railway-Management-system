import type { Metadata } from "next";
import { SectionPage } from "@/components/section-page";
export const metadata: Metadata = { title: "Settings" };
export default function Page() { return <SectionPage title="Settings" description="Configure workspace preferences and environment connections in a later implementation phase." />; }
