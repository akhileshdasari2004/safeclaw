"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

type DashboardOps = {
  deployments_total: number;
  deployments_active: number;
  deployments_completed: number;
  deployments_failed: number;
  success_rate_pct: number;
  estimated_monthly_spend_usd: number;
  avg_security_score: number | null;
  scans_total: number;
  alerts_enabled: number;
  status_breakdown: { status: string; count: number }[];
  recent_failures: {
    deployment_id: string;
    server_name: string;
    error_message: string | null;
    updated_at: string;
  }[];
};

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-muted-foreground">
        <span className="capitalize">{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function OpsMetricsPanel() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["ops-dashboard"],
    queryFn: () => api<DashboardOps>("/api/v1/ops/dashboard"),
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">Operational metrics unavailable.</p>
    );
  }

  const maxStatus = Math.max(...data.status_breakdown.map((s) => s.count), 1);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Success rate</CardDescription>
            <CardTitle className="text-3xl">{data.success_rate_pct}%</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {data.deployments_completed} completed · {data.deployments_failed} failed
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Est. monthly spend</CardDescription>
            <CardTitle className="text-3xl">${data.estimated_monthly_spend_usd.toFixed(2)}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">Active deployments only</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg security score</CardDescription>
            <CardTitle className="text-3xl">
              {data.avg_security_score != null ? data.avg_security_score : "—"}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {data.scans_total} scan{data.scans_total === 1 ? "" : "s"} run
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active now</CardDescription>
            <CardTitle className="text-3xl text-amber-400">{data.deployments_active}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            {data.alerts_enabled} cost alert{data.alerts_enabled === 1 ? "" : "s"} enabled
          </CardContent>
        </Card>
      </div>

      {data.status_breakdown.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Deployment status breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.status_breakdown.map((s) => (
              <Bar key={s.status} label={s.status} value={s.count} max={maxStatus} />
            ))}
          </CardContent>
        </Card>
      )}

      {data.recent_failures.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent failures</CardTitle>
            <CardDescription>Investigate and resume or rollback from deployment details.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.recent_failures.map((f) => (
              <div
                key={f.deployment_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-border px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium">{f.server_name}</span>
                  <p className="line-clamp-1 text-xs text-muted-foreground">
                    {f.error_message ?? "Unknown error"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="critical">failed</Badge>
                  <Link
                    href={`/dashboard/deployments/${f.deployment_id}`}
                    className="text-xs text-primary hover:underline"
                  >
                    View
                  </Link>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
