"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function BillingPage() {
  const { data } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => api<{ status: string; tier?: string }>("/api/v1/billing/subscription"),
  });

  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <h1 className="text-2xl font-bold">Billing</h1>
      <Card className="mt-6">
        <CardHeader><CardTitle className="text-base">Subscription</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm">Status: <strong>{data?.status ?? "…"}</strong></p>
          {data?.tier && <p className="text-sm text-muted-foreground">Tier: {data.tier}</p>}
          <p className="mt-4 text-xs text-muted-foreground">
            Manage payment methods in Stripe Customer Portal (configure in production).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
