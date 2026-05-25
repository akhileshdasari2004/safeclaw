"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import type { DeploymentPublic } from "@safeclaw/shared-types";
import { OnboardingChecklist } from "@/components/onboarding/OnboardingChecklist";
import { Button } from "@/components/ui/button";

export default function GettingStartedPage() {
  const { data: deployments } = useQuery({
    queryKey: ["deployments"],
    queryFn: () => api<DeploymentPublic[]>("/api/v1/deployments"),
  });

  const { data: alerts } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api<{ id: string }[]>("/api/v1/alerts"),
  });

  const { data: ops } = useQuery({
    queryKey: ["ops-dashboard"],
    queryFn: () => api<{ scans_total: number }>("/api/v1/ops/dashboard"),
  });

  const hasDeployments = (deployments?.length ?? 0) > 0;
  const hasScans = (ops?.scans_total ?? 0) > 0;
  const hasAlerts = (alerts?.length ?? 0) > 0;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Getting started</h1>
          <p className="text-muted-foreground">Your checklist to a production-ready OpenClaw VPS.</p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/dashboard">← Dashboard</Link>
        </Button>
      </div>
      <OnboardingChecklist
        hasDeployments={hasDeployments}
        hasScans={hasScans}
        hasAlerts={hasAlerts}
      />
    </div>
  );
}
