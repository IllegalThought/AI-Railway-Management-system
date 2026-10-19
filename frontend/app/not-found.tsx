import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";

export default function NotFound() {
  return <div><EmptyState title="Page not found" description="The requested RailOps AI workspace does not exist." /><Button asChild variant="outline" className="mx-auto -mt-24 flex w-fit"><Link href="/"><ArrowLeft className="size-4" />Return to overview</Link></Button></div>;
}
