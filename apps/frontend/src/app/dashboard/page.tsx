"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import type { DeploymentPublic } from "@safeclaw/shared-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function DashboardPage() {
  const { data: deployments, isLoading, error } = useQuery({
    queryKey: ["deployments"],
    queryFn: () => api<DeploymentPublic[]>("/api/v1/deployments"),
  });

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<{ email: string }>("/api/v1/auth/me"),
  });

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">{user?.email ?? "…"}</p>
        </div>
        <Button asChild><Link href="/dashboard/deploy">New deployment</Link></Button>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle className="text-base">Deployments</CardTitle></CardHeader>
          <CardContent><p className="text-3xl font-bold">{deployments?.length ?? 0}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Quick links</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Link href="/dashboard/alerts" className="block text-primary hover:underline">Cost alerts</Link>
            <Link href="/dashboard/billing" className="block text-primary hover:underline">Billing</Link>
          </CardContent>
        </Card>
      </div>

      <h2 className="mt-10 text-lg font-semibold">Your servers</h2>
      {isLoading && <p className="mt-4 text-muted-foreground">Loading…</p>}
      {error && <p className="mt-4 text-red-400">{(error as Error).message}</p>}
      <div className="mt-4 space-y-3">
        {deployments?.map((d) => (
          <Card key={d.id}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle className="text-base">{d.server_name}</CardTitle>
                <CardDescription>{d.provider} · {d.region} · {d.status}</CardDescription>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link href={`/dashboard/deployments/${d.id}`}>View</Link>
              </Button>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {d.ip_address ?? "Provisioning…"}
              {d.monthly_cost != null && ` · ~$${d.monthly_cost}/mo`}
            </CardContent>
          </Card>
        ))}
        {!isLoading && deployments?.length === 0 && (
          <p className="text-muted-foreground">No deployments yet. Start the wizard.</p>
        )}
      </div>
    </div>
  );
}
