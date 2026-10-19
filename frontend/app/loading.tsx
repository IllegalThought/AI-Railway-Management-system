import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <div aria-label="Loading page" className="space-y-6"><div><Skeleton className="h-3 w-28" /><Skeleton className="mt-3 h-8 w-72" /><Skeleton className="mt-3 h-4 w-full max-w-xl" /></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-32 rounded-xl" />)}</div><Skeleton className="h-56 rounded-xl" /><div className="grid gap-6 xl:grid-cols-2"><Skeleton className="h-80 rounded-xl" /><Skeleton className="h-80 rounded-xl" /></div></div>;
}
