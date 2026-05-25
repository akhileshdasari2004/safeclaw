"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Server, Rocket } from "lucide-react";
import { api } from "@/lib/api";
import type { DeploymentPublic } from "@safeclaw/shared-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { OnboardingChecklist } from "@/components/onboarding/OnboardingChecklist";
import { OpsMetricsPanel } from "@/components/dashboard/OpsMetricsPanel";
import { isOnboardingComplete } from "@/lib/onboarding";
import { useEffect, useState } from "react";

const ACTIVE = ["queued", "pending", "provisioning", "hardening", "installing", "verifying"];

export default function DashboardPage() {
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    setShowOnboarding(!isOnboardingComplete());
  }, []);

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
    queryFn: () => api<{ id: string; enabled: boolean }[]>("/api/v1/alerts"),
  });

  const { data: ops } = useQuery({
    queryKey: ["ops-dashboard"],
    queryFn: () => api<{ scans_total: number }>("/api/v1/ops/dashboard"),
  });

  const activeCount = deployments?.filter((d) => ACTIVE.includes(d.status)).length ?? 0;
  const completedCount =
    deployments?.filter((d) => d.status === "completed" || d.status === "running").length ?? 0;
  const hasDeployments = (deployments?.length ?? 0) > 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">{user?.email ?? "…"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/dashboard/getting-started">Getting started</Link>
          </Button>
          <Button asChild>
            <Link href="/dashboard/deploy">New deployment</Link>
          </Button>
        </div>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <section>
            <h2 className="mb-4 text-lg font-semibold">Operational metrics</h2>
            <OpsMetricsPanel />
          </section>
        </div>
        <div className="space-y-4">
          {(showOnboarding || !hasDeployments) && (
            <OnboardingChecklist
              compact={hasDeployments}
              hasDeployments={hasDeployments}
              hasScans={(ops?.scans_total ?? 0) > 0}
              hasAlerts={(alerts?.length ?? 0) > 0}
            />
          )}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick stats</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold">{isLoading ? "…" : deployments?.length ?? 0}</p>
                <p className="text-xs text-muted-foreground">Total</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-amber-400">{activeCount}</p>
                <p className="text-xs text-muted-foreground">In progress</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-primary">{completedCount}</p>
                <p className="text-xs text-muted-foreground">Live</p>
              </div>
              <div>
                <p className="text-2xl font-bold">{alerts?.filter((a) => a.enabled).length ?? 0}</p>
                <p className="text-xs text-muted-foreground">Alerts on</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-4 text-sm">
        <Link href="/dashboard/billing" className="text-primary hover:underline">
          Billing
        </Link>
        <Link href="/dashboard/alerts" className="text-primary hover:underline">
          Alerts
        </Link>
        <Link href="/dashboard/deploy" className="text-primary hover:underline">
          Deploy wizard
        </Link>
        <Link href="/dashboard/analytics" className="text-primary hover:underline">
          Analytics
        </Link>
        <Link href="/dashboard/incidents" className="text-primary hover:underline">
          Incidents
        </Link>
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
                <CardDescription>
                  {d.provider} · {d.region}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    ACTIVE.includes(d.status)
                      ? "medium"
                      : d.status === "failed"
                        ? "critical"
                        : "info"
                  }
                >
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
        {!isLoading && !hasDeployments && (
          <EmptyState
            icon={Server}
            title="No deployments yet"
            description="Launch your first hardened OpenClaw server with the deploy wizard. We provision the VPS, apply CIS-style hardening, and install Docker + OpenClaw."
            actionLabel="Start deploy wizard"
            actionHref="/dashboard/deploy"
          />
        )}
        {!isLoading && hasDeployments && completedCount === 0 && activeCount === 0 && (
          <EmptyState
            icon={Rocket}
            title="No live servers"
            description="Deployments are still provisioning or have failed. Open a deployment to view the live timeline and logs."
            actionLabel="View deployments"
            actionHref="/dashboard/deploy"
          />
        )}
      </div>
    </div>
  );
}
