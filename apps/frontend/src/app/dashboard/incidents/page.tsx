"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangle } from "lucide-react";

type Incident = {
  id: string;
  deployment_id: string | null;
  severity: string;
  status: string;
  title: string;
  description: string | null;
  created_at: string;
};

export default function IncidentsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["incidents"],
    queryFn: () => api<Incident[]>("/api/v1/incidents"),
  });

  const resolve = useMutation({
    mutationFn: (id: string) => api(`/api/v1/incidents/${id}/resolve`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Incidents</h1>
        <Button asChild variant="outline" size="sm">
          <Link href="/dashboard">← Dashboard</Link>
        </Button>
      </div>

      {isLoading && <Skeleton className="mt-6 h-24 w-full" />}
      {!isLoading && !data?.length && (
        <div className="mt-6">
          <EmptyState
            icon={AlertTriangle}
            title="No incidents"
            description="Incidents are opened automatically when provisioning fails. Resolve them after recovery."
          />
        </div>
      )}
      <ul className="mt-6 space-y-3">
        {data?.map((inc) => (
          <Card key={inc.id}>
            <CardHeader className="flex flex-row items-start justify-between pb-2">
              <div>
                <CardTitle className="text-base">{inc.title}</CardTitle>
                <p className="text-xs text-muted-foreground">{new Date(inc.created_at).toLocaleString()}</p>
              </div>
              <div className="flex gap-2">
                <Badge variant={inc.severity === "high" ? "critical" : "medium"}>{inc.severity}</Badge>
                <Badge variant={inc.status === "open" ? "medium" : "info"}>{inc.status}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              {inc.description && <p>{inc.description}</p>}
              {inc.deployment_id && (
                <Link href={`/dashboard/deployments/${inc.deployment_id}`} className="text-primary hover:underline">
                  View deployment
                </Link>
              )}
              {inc.status === "open" && (
                <Button size="sm" variant="outline" onClick={() => resolve.mutate(inc.id)} disabled={resolve.isPending}>
                  Mark resolved
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </ul>
    </div>
  );
}
