"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";

type TimelineStep = {
  event_id: string;
  step: string;
  level: string;
  message: string;
  timestamp: string;
  duration_ms: number | null;
  metadata?: Record<string, unknown> | null;
};

type Timeline = {
  deployment_id: string;
  correlation_id: string | null;
  status: string | null;
  provision_state?: string | null;
  retry_count?: number;
  total_duration_ms: number | null;
  step_count: number;
  steps: TimelineStep[];
};

function formatDuration(ms: number | null) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function DeploymentTimeline({ deploymentId }: { deploymentId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["deployment-timeline", deploymentId],
    queryFn: () => api<Timeline>(`/api/v1/deployments/${deploymentId}/timeline`),
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-red-400">{(error as Error).message}</p>;
  }

  if (!data?.steps.length) {
    return <p className="text-sm text-muted-foreground">Timeline will appear as provisioning runs.</p>;
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3 text-sm text-muted-foreground">
        {data.correlation_id && <span>Run: {data.correlation_id}</span>}
        {data.total_duration_ms != null && (
          <span>Total: {formatDuration(data.total_duration_ms)}</span>
        )}
        {data.status && <Badge variant="info">{data.status}</Badge>}
        {data.provision_state && <Badge variant="outline">{data.provision_state}</Badge>}
        {(data.retry_count ?? 0) > 0 && <span>Retries: {data.retry_count}</span>}
      </div>
      <ol className="relative border-l border-border pl-6">
        {data.steps.map((step, i) => (
          <motion.li
            key={step.event_id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.03 }}
            className="mb-6 last:mb-0"
          >
            <span className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full border-2 border-primary bg-background" />
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-medium capitalize">{step.step.replace(/_/g, " ")}</span>
              <span className="text-xs text-muted-foreground">
                {new Date(step.timestamp).toLocaleString()}
                {step.duration_ms != null && ` · +${formatDuration(step.duration_ms)}`}
              </span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{step.message}</p>
            {step.level === "ERROR" && (
              <Badge variant="critical" className="mt-2">
                Error
              </Badge>
            )}
          </motion.li>
        ))}
      </ol>
    </div>
  );
}
