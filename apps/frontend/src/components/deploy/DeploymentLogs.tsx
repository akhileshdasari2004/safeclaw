"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { useDeploymentLogs, type DeploymentLogEvent } from "@/hooks/useDeploymentLogs";
import { Loader2, Wifi, WifiOff } from "lucide-react";

const LEVEL_STYLES: Record<string, string> = {
  ERROR: "text-red-400",
  WARN: "text-amber-400",
  INFO: "text-emerald-400",
  DEBUG: "text-muted-foreground",
};

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString();
  } catch {
    return ts;
  }
}

export function DeploymentLogs({
  deploymentId,
  status,
  enabled = true,
}: {
  deploymentId: string;
  status?: string;
  enabled?: boolean;
}) {
  const active = enabled && !["completed", "failed", "running"].includes(status ?? "");
  const { logs, connected, reconnecting, closed, error } = useDeploymentLogs(
    deploymentId,
    active || status === undefined
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="rounded-lg border border-border bg-black/40 font-mono text-xs">
      <div className="flex items-center justify-between border-b border-border px-3 py-2 text-muted-foreground">
        <span>Live provisioning log</span>
        <span className="flex items-center gap-1.5">
          {reconnecting && (
            <>
              <Loader2 className="h-3 w-3 animate-spin" />
              Reconnecting…
            </>
          )}
          {!reconnecting && connected && (
            <>
              <Wifi className="h-3 w-3 text-emerald-400" />
              Live
            </>
          )}
          {!connected && !reconnecting && (
            <>
              <WifiOff className="h-3 w-3" />
              {closed ? "Complete" : "Offline"}
            </>
          )}
        </span>
      </div>
      <div className="max-h-96 overflow-y-auto p-3">
        {logs.length === 0 && (
          <p className="text-muted-foreground">Waiting for log events…</p>
        )}
        {logs.map((line, i) => (
          <LogLine key={`${line.timestamp}-${i}`} line={line} />
        ))}
        <div ref={bottomRef} />
      </div>
      {error && <p className="border-t border-border px-3 py-2 text-red-400">{error}</p>}
    </div>
  );
}

function LogLine({ line }: { line: DeploymentLogEvent }) {
  if (line.step === "heartbeat") return null;
  return (
    <div className="mb-1 flex gap-2">
      <span className="shrink-0 text-muted-foreground">{formatTime(line.timestamp)}</span>
      <span className={cn("shrink-0 uppercase", LEVEL_STYLES[line.level] ?? "text-foreground")}>
        {line.level}
      </span>
      <span className="shrink-0 text-primary/80">[{line.step}]</span>
      <span className="break-all text-foreground/90">{line.message}</span>
    </div>
  );
}
