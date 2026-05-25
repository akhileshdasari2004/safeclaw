"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Deployment = {
  id: string;
  server_name: string;
  status: string;
  ip_address: string | null;
  logs: string | null;
  error_message: string | null;
  monthly_cost: number | null;
};

type Scan = {
  id: string;
  score: number;
  grade: string;
  findings: { issues: { severity: string; description: string; remediation: string }[] };
};

export default function DeploymentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const { data: dep, isLoading } = useQuery({
    queryKey: ["deployment", id],
    queryFn: () => api<Deployment>(`/api/v1/deployments/${id}`),
    refetchInterval: (q) =>
      ["pending", "provisioning", "hardening", "installing"].includes(q.state.data?.status ?? "")
        ? 3000
        : false,
  });

  const { data: scans } = useQuery({
    queryKey: ["scans", id],
    queryFn: () => api<Scan[]>(`/api/v1/scans/deployments/${id}`),
    enabled: dep?.status === "running",
  });

  const scanMutation = useMutation({
    mutationFn: () =>
      api<Scan>(`/api/v1/scans/deployments/${id}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scans", id] }),
  });

  const retryMutation = useMutation({
    mutationFn: () =>
      api(`/api/v1/deployments/${id}/retry`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deployment", id] }),
  });

  if (isLoading) return <p className="p-10 text-muted-foreground">Loading…</p>;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold">{dep?.server_name}</h1>
      <p className="text-muted-foreground">
        {dep?.status} · {dep?.ip_address ?? "—"}
        {dep?.monthly_cost != null && ` · ~$${dep.monthly_cost}/mo`}
      </p>

      {dep?.status === "failed" && (
        <div className="mt-4 flex gap-2">
          <Button onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}>
            Retry deploy
          </Button>
          {dep.error_message && (
            <p className="text-sm text-red-400">{dep.error_message}</p>
          )}
        </div>
      )}

      <Card className="mt-8">
        <CardHeader><CardTitle className="text-base">Provisioning logs</CardTitle></CardHeader>
        <CardContent>
          <pre className="max-h-96 overflow-auto rounded bg-muted p-4 text-xs">
            {dep?.logs || "Waiting for logs…"}
          </pre>
        </CardContent>
      </Card>

      {dep?.status === "running" && (
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Security scans</CardTitle>
            <Button size="sm" onClick={() => scanMutation.mutate()} disabled={scanMutation.isPending}>
              Run scan
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {scans?.map((s) => (
              <div key={s.id} className="rounded border border-border p-4">
                <p className="font-medium">Score {s.score} · Grade {s.grade}</p>
                <ul className="mt-2 space-y-2 text-sm text-muted-foreground">
                  {s.findings.issues.map((issue, i) => (
                    <li key={i}>
                      <span className="text-foreground">[{issue.severity}]</span> {issue.description}
                      <code className="mt-1 block text-xs">{issue.remediation}</code>
                    </li>
                  ))}
                  {s.findings.issues.length === 0 && <li>No issues — great job!</li>}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
