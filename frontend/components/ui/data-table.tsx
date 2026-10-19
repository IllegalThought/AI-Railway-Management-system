import type { ReactNode } from "react";

import { Inbox } from "lucide-react";

type Column = { key: string; label: string; align?: "left" | "right" };

export function DataTable({ columns, rows, emptyTitle, emptyDescription }: { columns: Column[]; rows: Array<Record<string, ReactNode>>; emptyTitle: string; emptyDescription: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-800">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[540px] border-collapse text-left text-sm">
          <thead className="bg-slate-950/60 text-[11px] uppercase tracking-[0.12em] text-slate-500">
            <tr>{columns.map((column) => <th key={column.key} className={`px-4 py-3 font-medium ${column.align === "right" ? "text-right" : ""}`}>{column.label}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {rows.map((row, index) => (
              <tr key={index} className="bg-slate-900/30 transition-colors hover:bg-slate-800/35">
                {columns.map((column) => <td key={column.key} className={`px-4 py-3 text-slate-300 ${column.align === "right" ? "text-right" : ""}`}>{row[column.key]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 ? (
        <div className="flex min-h-44 flex-col items-center justify-center px-6 py-10 text-center">
          <span className="mb-3 grid size-9 place-items-center rounded-lg border border-slate-800 bg-slate-950/50 text-slate-500"><Inbox className="size-4" /></span>
          <p className="text-sm font-medium text-slate-300">{emptyTitle}</p>
          <p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">{emptyDescription}</p>
        </div>
      ) : null}
    </div>
  );
}
