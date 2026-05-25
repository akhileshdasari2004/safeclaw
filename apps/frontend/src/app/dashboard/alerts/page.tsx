"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Alert = { id: string; threshold: string; enabled: boolean };

export default function AlertsPage() {
  const [threshold, setThreshold] = useState("50");
  const qc = useQueryClient();

  const { data: alerts } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => api<Alert[]>("/api/v1/alerts"),
  });

  const create = useMutation({
    mutationFn: () =>
      api("/api/v1/alerts", {
        method: "POST",
        body: JSON.stringify({ threshold: parseFloat(threshold), enabled: true }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <h1 className="text-2xl font-bold">Cost alerts</h1>
      <p className="text-muted-foreground">Email when estimated monthly spend exceeds threshold.</p>
      <Card className="mt-6">
        <CardHeader><CardTitle className="text-base">New alert</CardTitle></CardHeader>
        <CardContent className="flex gap-2">
          <Input type="number" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
          <Button onClick={() => create.mutate()} disabled={create.isPending}>Add</Button>
        </CardContent>
      </Card>
      <ul className="mt-6 space-y-2">
        {alerts?.map((a) => (
          <li key={a.id} className="rounded border border-border px-4 py-2 text-sm">
            ${a.threshold}/mo threshold · {a.enabled ? "enabled" : "disabled"}
          </li>
        ))}
      </ul>
    </div>
  );
}
