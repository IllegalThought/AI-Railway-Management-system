import type { Metadata } from "next";
import { SectionPage } from "@/components/section-page";
export const metadata: Metadata = { title: "Live Operations" };
export default function Page() { return <SectionPage title="Live Operations" description="Monitor current train movements, running state, and service conditions as operational APIs become available." />; }
