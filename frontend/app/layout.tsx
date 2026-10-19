import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Overview | RailOps AI", template: "%s | RailOps AI" },
  description: "Synthetic railway operations management and decision-support workspace.",
  applicationName: "RailOps AI",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="dark"><body><AppShell>{children}</AppShell></body></html>;
}
