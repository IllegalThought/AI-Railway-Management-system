import type { Metadata } from "next";

import { DispatchBoard } from "@/components/dispatch/dispatch-board";

export const metadata: Metadata = { title: "Dispatch Board" };

export default function Page() {
  return <DispatchBoard />;
}
