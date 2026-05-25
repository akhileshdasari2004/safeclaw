"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export type DeploymentEventItem = {
  id: string;
  timestamp: string;
  level: string;
  step: string;
  message: string;
  metadata?: Record<string, unknown> | null;
};

const LEVEL_CLASS: Record<string, string> = {
  ERROR: "text-red-400",
  WARN: "text-amber-400",
  INFO: "text-emerald-400",
  DEBUG: "text-muted-foreground",
};

export function DeploymentEventList({
  events,
  className,
}: {
  events: DeploymentEventItem[];
  className?: string;
}) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No events recorded yet.</p>;
  }

  return (
    <ul className={cn("space-y-2", className)}>
      {events.map((ev) => (
        <li
          key={ev.id}
          className="rounded-md border border-border bg-muted/30 px-3 py-2 text-xs font-mono"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-muted-foreground">
              {new Date(ev.timestamp).toLocaleTimeString()}
            </span>
            <Badge variant={ev.level === "ERROR" ? "critical" : "info"}>{ev.level}</Badge>
            <span className="text-primary/90">[{ev.step}]</span>
          </div>
          <p className={cn("mt-1 break-all", LEVEL_CLASS[ev.level] ?? "text-foreground")}>
            {ev.message}
          </p>
        </li>
      ))}
    </ul>
  );
}
