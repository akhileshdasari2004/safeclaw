"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DeploymentLogs } from "@/components/deploy/DeploymentLogs";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

const ACTIVE = ["queued", "pending", "provisioning", "hardening", "installing", "verifying"];

type Deployment = {
  id: string;
  server_name: string;
  status: string;
  ip_address: string | null;
  error_message: string | null;
  monthly_cost: number | null;
};

type Scan = {
  id: string;
  score: number;
  grade: string;
  created_at: string;
};

export default function DeploymentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const { data: dep, isLoading } = useQuery({
    queryKey: ["deployment", id],
    queryFn: () => api<Deployment>(`/api/v1/deployments/${id}`),
    refetchInterval: (q) =>
      ACTIVE.includes(q.state.data?.status ?? "") ? 3000 : false,
  });

  const { data: scans } = useQuery({
    queryKey: ["scans", id],
    queryFn: () => api<Scan[]>(`/api/v1/scans/deployments/${id}`),
    enabled: dep?.status === "completed" || dep?.status === "running",
  });

  const scanMutation = useMutation({
    mutationFn: () => api<{ id: string }>(`/api/v1/scans/deployments/${id}`, { method: "POST" }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["scans", id] });
      window.location.href = `/dashboard/scans/${data.id}`;
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => api(`/api/v1/deployments/${id}/retry`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deployment", id] }),
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-10">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  const isActive = ACTIVE.includes(dep?.status ?? "");

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold">{dep?.server_name}</h1>
      <p className="mt-1 flex flex-wrap items-center gap-2 text-muted-foreground">
        <Badge variant={dep?.status === "failed" ? "critical" : "info"}>{dep?.status}</Badge>
        {dep?.ip_address ?? "—"}
        {dep?.monthly_cost != null && ` · ~$${dep.monthly_cost}/mo`}
      </p>

      {dep?.status === "failed" && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}>
            Retry deploy
          </Button>
          {dep.error_message && (
            <p className="text-sm text-red-400">{dep.error_message}</p>
          )}
        </div>
      )}

      <div className="mt-8">
        <DeploymentLogs deploymentId={id!} status={dep?.status} enabled={isActive || dep?.status === "failed"} />
      </div>

      {(dep?.status === "completed" || dep?.status === "running") && (
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Security scans</CardTitle>
            <Button size="sm" onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
              Run scan
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {scans?.length === 0 && (
              <p className="text-sm text-muted-foreground">No scans yet.</p>
            )}
            {scans?.map((s) => (
              <Link
                key={s.id}
                href={`/dashboard/scans/${s.id}`}
                className="flex items-center justify-between rounded border border-border px-4 py-3 hover:bg-muted/50"
              >
                <span>
                  Grade <strong>{s.grade}</strong> · Score {s.score}
                </span>
                <span className="text-xs text-muted-foreground">
                  {new Date(s.created_at).toLocaleString()}
                </span>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
