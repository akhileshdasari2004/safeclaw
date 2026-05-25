"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DeploymentLogs } from "@/components/deploy/DeploymentLogs";
import { DeploymentTimeline } from "@/components/deployment/DeploymentTimeline";
import { DeploymentEventList } from "@/components/deployment/DeploymentEventList";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Shield } from "lucide-react";

const ACTIVE = ["queued", "pending", "provisioning", "hardening", "installing", "verifying"];

type Deployment = {
  id: string;
  server_name: string;
  status: string;
  ip_address: string | null;
  error_message: string | null;
  monthly_cost: number | null;
  provision_state?: string;
  retry_count?: number;
  ssh_key_version?: number;
  ssh_rotated_at?: string | null;
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
  const [newPub, setNewPub] = useState("");
  const [newPriv, setNewPriv] = useState("");
  const [rotateError, setRotateError] = useState<string | null>(null);

  const { data: dep, isLoading } = useQuery({
    queryKey: ["deployment", id],
    queryFn: () => api<Deployment>(`/api/v1/deployments/${id}`),
    refetchInterval: (q) =>
      ACTIVE.includes(q.state.data?.status ?? "") ? 3000 : false,
  });

  const { data: persistedEvents } = useQuery({
    queryKey: ["deployment-events", id],
    queryFn: () =>
      api<
        {
          id: string;
          timestamp: string;
          level: string;
          step: string;
          message: string;
          metadata?: Record<string, unknown> | null;
        }[]
      >(`/api/v1/deployments/${id}/events`),
    enabled: !!id,
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

  const rotateMutation = useMutation({
    mutationFn: () =>
      api(`/api/v1/deployments/${id}/rotate-ssh`, {
        method: "POST",
        body: JSON.stringify({ new_public_key: newPub, new_private_key: newPriv }),
      }),
    onSuccess: () => {
      setRotateError(null);
      qc.invalidateQueries({ queryKey: ["deployment", id] });
    },
    onError: (e: Error) => setRotateError(e.message),
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

      {(dep?.status === "failed" || dep?.provision_state === "FAILED") && (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}>
            Resume ({dep?.retry_count ?? 0} retries)
          </Button>
          <Button
            variant="outline"
            onClick={() => api(`/api/v1/deployments/${id}/rollback`, { method: "POST" }).then(() => qc.invalidateQueries({ queryKey: ["deployment", id] }))}
          >
            Rollback
          </Button>
          {dep.error_message && (
            <p className="text-sm text-red-400">{dep.error_message}</p>
          )}
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-3 text-sm font-semibold">Live log</h2>
          <DeploymentLogs deploymentId={id!} status={dep?.status} enabled={isActive || dep?.status === "failed"} />
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold">Timeline</h2>
          <DeploymentTimeline deploymentId={id!} />
        </div>
      </div>

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold">Event history</h2>
        <DeploymentEventList
          events={(persistedEvents ?? []).map((e) => ({
            id: e.id,
            timestamp: e.timestamp,
            level: e.level,
            step: e.step,
            message: e.message,
            metadata: e.metadata,
          }))}
        />
      </div>

      {(dep?.status === "completed" || dep?.status === "running") && (
        <>
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">SSH key rotation</CardTitle>
            <p className="text-xs text-muted-foreground">
              Version {dep.ssh_key_version ?? 1}
              {dep.ssh_rotated_at && ` · last rotated ${new Date(dep.ssh_rotated_at).toLocaleString()}`}
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            <textarea
              className="min-h-[60px] w-full rounded-md border border-border bg-background p-2 text-sm"
              placeholder="New SSH public key"
              value={newPub}
              onChange={(e) => setNewPub(e.target.value)}
            />
            <textarea
              className="min-h-[60px] w-full rounded-md border border-border bg-background p-2 text-sm"
              placeholder="New SSH private key (PEM)"
              value={newPriv}
              onChange={(e) => setNewPriv(e.target.value)}
            />
            {rotateError && <p className="text-sm text-red-400">{rotateError}</p>}
            <Button
              size="sm"
              variant="outline"
              disabled={!newPub || !newPriv || rotateMutation.isPending}
              onClick={() => rotateMutation.mutate()}
            >
              Rotate keys
            </Button>
          </CardContent>
        </Card>
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Security scans</CardTitle>
            <Button size="sm" onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
              Run scan
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {scans?.length === 0 && (
              <EmptyState
                icon={Shield}
                title="No security scans yet"
                description="Run a scan to check firewall, SSH hardening, Docker socket permissions, and disk usage on this server."
                actionLabel="Run first scan"
                onAction={() => scanMutation.mutate()}
              />
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
        </>
      )}
    </div>
  );
}
