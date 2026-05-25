"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { alertFormSchema } from "@/lib/schemas";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Bell } from "lucide-react";

type Alert = {
  id: string;
  threshold: string;
  enabled: boolean;
  cooldown_hours: number;
};

type History = {
  id: string;
  provider: string | null;
  current_spend: string;
  threshold: string;
  message: string;
  created_at: string;
};

export default function AlertsPage() {
  const [threshold, setThreshold] = useState("50");
  const [cooldown, setCooldown] = useState("24");
  const [formError, setFormError] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data: alerts, isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api<Alert[]>("/api/v1/alerts"),
  });

  const { data: history } = useQuery({
    queryKey: ["alert-history"],
    queryFn: () => api<History[]>("/api/v1/alerts/history"),
  });

  const create = useMutation({
    mutationFn: (body: { threshold: number; cooldown_hours: number }) =>
      api("/api/v1/alerts", { method: "POST", body: JSON.stringify({ ...body, enabled: true }) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      setFormError(null);
    },
    onError: (e: Error) => setFormError(e.message),
  });

  const testAlert = useMutation({
    mutationFn: (id: string) => api(`/api/v1/alerts/${id}/test`, { method: "POST" }),
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api(`/api/v1/alerts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  function handleCreate() {
    const parsed = alertFormSchema.safeParse({
      threshold: parseFloat(threshold),
      enabled: true,
      cooldown_hours: parseInt(cooldown, 10),
    });
    if (!parsed.success) {
      setFormError(parsed.error.errors[0]?.message ?? "Invalid input");
      return;
    }
    create.mutate({
      threshold: parsed.data.threshold,
      cooldown_hours: parsed.data.cooldown_hours ?? 24,
    });
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Cost alerts</h1>
      <p className="text-muted-foreground">Hourly checks with cooldown and duplicate suppression.</p>

      <Card className="mt-8">
        <CardHeader><CardTitle className="text-base">Create alert</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              type="number"
              placeholder="Threshold USD/mo"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
            <Input
              type="number"
              placeholder="Cooldown hrs"
              value={cooldown}
              onChange={(e) => setCooldown(e.target.value)}
              className="w-28"
            />
          </div>
          {formError && <p className="text-sm text-red-400">{formError}</p>}
          <Button onClick={handleCreate} disabled={create.isPending}>
            Add alert
          </Button>
        </CardContent>
      </Card>

      <h2 className="mt-10 text-lg font-semibold">Active alerts</h2>
      {isLoading && <Skeleton className="mt-4 h-20 w-full" />}
      {!isLoading && alerts?.length === 0 && (
        <div className="mt-4">
          <EmptyState
            icon={Bell}
            title="No cost alerts configured"
            description="Set a monthly spend threshold and we'll email you when your infrastructure costs exceed it (with cooldown to avoid spam)."
            actionLabel="Create alert above"
            onAction={() => document.querySelector<HTMLInputElement>('input[type="number"]')?.focus()}
          />
        </div>
      )}
      <ul className="mt-4 space-y-2">
        {alerts?.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-border px-4 py-3 text-sm">
            <span>
              ${a.threshold}/mo · cooldown {a.cooldown_hours}h · {a.enabled ? "on" : "off"}
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => toggle.mutate({ id: a.id, enabled: !a.enabled })}>
                {a.enabled ? "Disable" : "Enable"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => testAlert.mutate(a.id)} disabled={testAlert.isPending}>
                Test email
              </Button>
            </div>
          </li>
        ))}
      </ul>

      <h2 className="mt-10 text-lg font-semibold">Alert history</h2>
      {!history?.length && (
        <p className="mt-4 text-sm text-muted-foreground">No alerts triggered yet — you&apos;re under budget.</p>
      )}
      <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
        {history?.map((h) => (
          <li key={h.id} className="rounded border border-border px-3 py-2">
            {h.message} · {new Date(h.created_at).toLocaleString()}
          </li>
        ))}
      </ul>
    </div>
  );
}
