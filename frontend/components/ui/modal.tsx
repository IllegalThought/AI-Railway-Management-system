"use client";

import type { ReactNode } from "react";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";

export function Modal({ open, title, description, children, onClose }: { open: boolean; title: string; description?: string; children: ReactNode; onClose: () => void }) {
  if (!open) return null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center p-4"><button type="button" className="absolute inset-0 bg-[#202831]/55 backdrop-blur-sm" aria-label="Close dialog" onClick={onClose} /><div role="dialog" aria-modal="true" aria-labelledby="dialog-title" className="relative max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-[#C9D1D8] bg-white shadow-[0_20px_60px_rgba(32,40,49,.24)]"><div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[#DFE4E8] bg-white px-5 py-4 backdrop-blur"><div><h2 id="dialog-title" className="text-base font-semibold text-[#202B36]">{title}</h2>{description ? <p className="mt-1 text-xs text-[#687581]">{description}</p> : null}</div><Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close dialog"><X className="size-4" /></Button></div>{children}</div></div>;
}
