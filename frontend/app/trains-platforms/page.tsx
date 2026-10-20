import type { Metadata } from "next";
import { OperationsManager } from "@/components/operations/operations-manager";
export const metadata: Metadata = { title: "Trains & Platforms" };
export default function Page() { return <OperationsManager />; }
