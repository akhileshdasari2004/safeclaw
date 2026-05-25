"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

type Subscription = {
  status: string;
  tier?: string;
  stripe_subscription_id?: string;
  stripe_customer_id?: string;
  updated_at?: string;
};

export default function BillingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => api<Subscription>("/api/v1/billing/subscription"),
  });

  const portal = useMutation({
    mutationFn: () => api<{ portal_url: string }>("/api/v1/billing/portal", { method: "POST" }),
    onSuccess: (res) => {
      window.location.href = res.portal_url;
    },
  });

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Billing</h1>
      <p className="text-muted-foreground">Manage subscription and invoices via Stripe.</p>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle className="text-base">Subscription</CardTitle>
          <CardDescription>Payment state is authoritative from Stripe webhooks only.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <>
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-10 w-full" />
            </>
          ) : (
            <>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd className="font-medium">{data?.status ?? "none"}</dd>
                </div>
                {data?.tier && (
                  <div className="flex justify-between">
                    <dt className="text-muted-foreground">Tier</dt>
                    <dd>{data.tier}</dd>
                  </div>
                )}
                {data?.updated_at && (
                  <div className="flex justify-between">
                    <dt className="text-muted-foreground">Last sync</dt>
                    <dd>{new Date(data.updated_at).toLocaleString()}</dd>
                  </div>
                )}
              </dl>
              <Button
                className="w-full"
                disabled={!data?.stripe_customer_id || portal.isPending}
                onClick={() => portal.mutate()}
              >
                {portal.isPending ? "Opening portal…" : "Open Stripe Customer Portal"}
              </Button>
              {!data?.stripe_customer_id && data?.status !== "none" && (
                <p className="text-xs text-muted-foreground">
                  Customer ID pending — complete checkout or wait for webhook sync.
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
