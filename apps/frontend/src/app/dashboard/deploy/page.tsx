"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CloudProvider } from "@safeclaw/shared-types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Plan = { id: string; name: string; monthly_cost_usd: number; vcpus: number; memory_gb: number };
type Region = { id: string; name: string };

const STEPS = ["Provider", "Region", "Plan", "SSH", "Review", "Deploy"];

export default function DeployWizardPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [provider, setProvider] = useState<CloudProvider>("hetzner");
  const [region, setRegion] = useState("");
  const [planId, setPlanId] = useState("");
  const [serverName, setServerName] = useState("my-openclaw");
  const [sshPublic, setSshPublic] = useState("");
  const [sshPrivate, setSshPrivate] = useState("");
  const [deploying, setDeploying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: regions } = useQuery({
    queryKey: ["regions", provider],
    queryFn: () =>
      api<{ regions: Region[] }>(`/api/v1/deployments/providers/${provider}/regions`),
    enabled: step >= 1,
  });

  const { data: plans } = useQuery({
    queryKey: ["plans", provider, region],
    queryFn: () =>
      api<{ plans: Plan[] }>(
        `/api/v1/deployments/providers/${provider}/plans?region=${region}`
      ),
    enabled: step >= 2 && !!region,
  });

  const selectedPlan = plans?.plans.find((p) => p.id === planId);

  async function deploy() {
    setDeploying(true);
    setError(null);
    try {
      const res = await api<{ id: string }>("/api/v1/deployments", {
        method: "POST",
        body: JSON.stringify({
          provider,
          region,
          server_name: serverName,
          plan_id: planId,
          ssh_public_key: sshPublic,
          ssh_private_key: sshPrivate || undefined,
          idempotency_key: `deploy-${serverName}-${Date.now()}`,
        }),
      });
      router.push(`/dashboard/deployments/${res.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Deploy failed");
      setDeploying(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Deploy wizard</h1>
      <div className="mt-4 flex gap-2 text-xs text-muted-foreground">
        {STEPS.map((s, i) => (
          <span key={s} className={i === step ? "text-primary font-medium" : ""}>
            {i + 1}. {s}
          </span>
        ))}
      </div>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>{STEPS[step]}</CardTitle>
          <CardDescription>
            {step === 4 && selectedPlan
              ? `Estimated ~$${selectedPlan.monthly_cost_usd}/mo`
              : "Configure your hardened OpenClaw server"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {step === 0 && (
            <div className="flex gap-3">
              {(["hetzner", "digitalocean"] as CloudProvider[]).map((p) => (
                <Button
                  key={p}
                  variant={provider === p ? "default" : "outline"}
                  onClick={() => setProvider(p)}
                >
                  {p}
                </Button>
              ))}
            </div>
          )}
          {step === 1 && (
            <div className="grid gap-2">
              {regions?.regions.map((r) => (
                <Button
                  key={r.id}
                  variant={region === r.id ? "default" : "outline"}
                  className="justify-start"
                  onClick={() => setRegion(r.id)}
                >
                  {r.name} ({r.id})
                </Button>
              ))}
            </div>
          )}
          {step === 2 && (
            <div className="grid gap-2">
              {plans?.plans.map((p) => (
                <Button
                  key={p.id}
                  variant={planId === p.id ? "default" : "outline"}
                  className="h-auto flex-col items-start py-3"
                  onClick={() => setPlanId(p.id)}
                >
                  <span>{p.name}</span>
                  <span className="text-xs opacity-80">
                    {p.vcpus} vCPU · {p.memory_gb}GB · ${p.monthly_cost_usd}/mo
                  </span>
                </Button>
              ))}
            </div>
          )}
          {step === 3 && (
            <>
              <Input placeholder="Server name (a-z0-9-)" value={serverName} onChange={(e) => setServerName(e.target.value)} />
              <textarea
                className="min-h-[80px] w-full rounded-md border border-border bg-background p-3 text-sm"
                placeholder="SSH public key"
                value={sshPublic}
                onChange={(e) => setSshPublic(e.target.value)}
              />
              <textarea
                className="min-h-[80px] w-full rounded-md border border-border bg-background p-3 text-sm"
                placeholder="SSH private key (encrypted at rest — required for provisioning)"
                value={sshPrivate}
                onChange={(e) => setSshPrivate(e.target.value)}
              />
            </>
          )}
          {step === 4 && (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt>Provider</dt><dd>{provider}</dd></div>
              <div className="flex justify-between"><dt>Region</dt><dd>{region}</dd></div>
              <div className="flex justify-between"><dt>Plan</dt><dd>{selectedPlan?.name}</dd></div>
              <div className="flex justify-between"><dt>Server</dt><dd>{serverName}</dd></div>
              <div className="flex justify-between"><dt>Est. cost</dt><dd>${selectedPlan?.monthly_cost_usd}/mo</dd></div>
            </dl>
          )}
          {step === 5 && (
            <p className="text-muted-foreground">
              {deploying ? "Starting provisioning…" : "Ready to deploy."}
            </p>
          )}
          {error && <p className="text-sm text-red-400">{error}</p>}
          <div className="flex justify-between pt-4">
            <Button variant="outline" disabled={step === 0 || deploying} onClick={() => setStep(step - 1)}>
              Back
            </Button>
            {step < 4 && (
              <Button
                disabled={
                  (step === 1 && !region) ||
                  (step === 2 && !planId) ||
                  (step === 3 && (!sshPublic || !serverName))
                }
                onClick={() => setStep(step + 1)}
              >
                Next
              </Button>
            )}
            {step === 4 && (
              <Button onClick={() => { setStep(5); deploy(); }} disabled={deploying}>
                Deploy
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
