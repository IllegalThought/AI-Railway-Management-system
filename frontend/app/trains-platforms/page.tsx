import type { Metadata } from "next";
import { SectionPage } from "@/components/section-page";
export const metadata: Metadata = { title: "Trains & Platforms" };
export default function Page() { return <SectionPage title="Trains & Platforms" description="Manage synthetic fleet records, platform resources, and compatibility constraints." />; }
