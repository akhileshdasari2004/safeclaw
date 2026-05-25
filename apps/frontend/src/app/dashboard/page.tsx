"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import type { DeploymentPublic } from "@safeclaw/shared-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

const ACTIVE = ["queued", "pending", "provisioning", "hardening", "installing", "verifying"];

export default function DashboardPage() {
  const { data: deployments, isLoading } = useQuery({
    queryKey: ["deployments"],
    queryFn: () => api<DeploymentPublic[]>("/api/v1/deployments"),
  });

  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<{ email: string }>("/api/v1/auth/me"),
  });

  const { data: alerts } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api<{ id: string; enabled: boolean; threshold: string }[]>("/api/v1/alerts"),
  });

  const activeCount = deployments?.filter((d) => ACTIVE.includes(d.status)).length ?? 0;
  const completedCount = deployments?.filter((d) => d.status === "completed" || d.status === "running").length ?? 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">{user?.email ?? "…"}</p>
        </div>
        <Button asChild><Link href="/dashboard/deploy">New deployment</Link></Button>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader><CardTitle className="text-base">Deployments</CardTitle></CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-12" /> : (
              <p className="text-3xl font-bold">{deployments?.length ?? 0}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">In progress</CardTitle></CardHeader>
          <CardContent><p className="text-3xl font-bold text-amber-400">{activeCount}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Live servers</CardTitle></CardHeader>
          <CardContent><p className="text-3xl font-bold text-primary">{completedCount}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Alerts</CardTitle></CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{alerts?.filter((a) => a.enabled).length ?? 0}</p>
            <Link href="/dashboard/alerts" className="text-xs text-primary hover:underline">Configure</Link>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 flex gap-4 text-sm">
        <Link href="/dashboard/billing" className="text-primary hover:underline">Billing</Link>
        <Link href="/dashboard/alerts" className="text-primary hover:underline">Alerts</Link>
      </div>

      <h2 className="mt-10 text-lg font-semibold">Deployments</h2>
      {isLoading && (
        <div className="mt-4 space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      )}
      <div className="mt-4 space-y-3">
        {deployments?.map((d) => (
          <Card key={d.id}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle className="text-base">{d.server_name}</CardTitle>
                <CardDescription>{d.provider} · {d.region}</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={ACTIVE.includes(d.status) ? "medium" : d.status === "failed" ? "critical" : "info"}>
                  {d.status}
                </Badge>
                <Button asChild variant="outline" size="sm">
                  <Link href={`/dashboard/deployments/${d.id}`}>
                    {ACTIVE.includes(d.status) ? "View live" : "View"}
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {d.ip_address ?? "Provisioning…"}
              {d.monthly_cost != null && ` · ~$${d.monthly_cost}/mo`}
            </CardContent>
          </Card>
        ))}
        {!isLoading && deployments?.length === 0 && (
          <p className="text-muted-foreground">No deployments yet.</p>
        )}
      </div>
    </div>
  );
}
