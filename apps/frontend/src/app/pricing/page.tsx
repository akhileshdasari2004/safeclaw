"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const tiers = [
  { id: "starter" as const, name: "Starter", price: "$19/mo", features: ["1 deployment", "Security scans", "Email support"] },
  { id: "pro" as const, name: "Pro", price: "$49/mo", features: ["5 deployments", "Cost alerts", "Priority support"] },
];

export default function PricingPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function checkout(tier: "starter" | "pro") {
    setLoading(tier);
    setError(null);
    try {
      const res = await api<{ checkout_url: string }>("/api/v1/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ email, tier }),
      });
      window.location.href = res.checkout_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Checkout failed");
      setLoading(null);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <h1 className="text-center text-3xl font-bold">Simple pricing</h1>
      <p className="mt-2 text-center text-muted-foreground">License key emailed after purchase. No secrets on the client.</p>
      <div className="mx-auto mt-8 max-w-md">
        <Input type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      {error && <p className="mt-4 text-center text-red-400">{error}</p>}
      <div className="mt-10 grid gap-6 md:grid-cols-2">
        {tiers.map((t) => (
          <Card key={t.id}>
            <CardHeader>
              <CardTitle>{t.name}</CardTitle>
              <CardDescription>{t.price}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="mb-6 space-y-2 text-sm text-muted-foreground">
                {t.features.map((f) => (
                  <li key={f}>• {f}</li>
                ))}
              </ul>
              <Button
                className="w-full"
                disabled={!email || loading !== null}
                onClick={() => checkout(t.id)}
              >
                {loading === t.id ? "Redirecting…" : "Subscribe"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
