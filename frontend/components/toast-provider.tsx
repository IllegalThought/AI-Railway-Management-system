"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, Info, X } from "lucide-react";

type Toast = { id: number; title: string; description?: string; tone: "info" | "success" };
type ToastInput = Omit<Toast, "id">;

const ToastContext = createContext<{ toast: (input: ToastInput) => void } | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = useCallback((id: number) => setToasts((current) => current.filter((item) => item.id !== id)), []);
  const toast = useCallback((input: ToastInput) => {
    const id = Date.now();
    setToasts((current) => [...current.slice(-2), { ...input, id }]);
    window.setTimeout(() => dismiss(id), 4500);
  }, [dismiss]);
  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2" aria-live="polite" aria-atomic="true">
        {toasts.map((item) => {
          const Icon = item.tone === "success" ? CheckCircle2 : Info;
          return (
            <div key={item.id} className="pointer-events-auto animate-toast-in rounded-lg border border-[#C9D1D8] bg-white p-4 shadow-[0_12px_30px_rgba(32,40,49,.14)]">
              <div className="flex gap-3">
                <Icon className={`mt-0.5 size-4 shrink-0 ${item.tone === "success" ? "text-[#4F7A63]" : "text-[#36638A]"}`} />
                <div className="min-w-0 flex-1"><p className="text-sm font-medium text-[#202B36]">{item.title}</p>{item.description ? <p className="mt-1 text-xs leading-5 text-[#52616F]">{item.description}</p> : null}</div>
                <button type="button" onClick={() => dismiss(item.id)} aria-label="Dismiss notification" className="-mr-1 -mt-1 grid size-7 place-items-center rounded text-[#687581] hover:bg-[#EDF0F2] hover:text-[#2D3A45]"><X className="size-3.5" /></button>
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider.");
  return context;
}
