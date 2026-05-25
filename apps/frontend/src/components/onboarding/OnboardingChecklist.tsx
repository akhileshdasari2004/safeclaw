"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CheckCircle2, Circle, Rocket, Shield, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { isOnboardingComplete, markOnboardingComplete } from "@/lib/onboarding";

const STEPS = [
  {
    id: "account",
    title: "Create your account",
    description: "You are signed in and ready to provision servers.",
    href: "/dashboard",
    icon: CheckCircle2,
    done: true,
  },
  {
    id: "deploy",
    title: "Deploy your first OpenClaw server",
    description: "Pick a provider, region, and plan — we handle hardening and Docker.",
    href: "/dashboard/deploy",
    icon: Rocket,
    done: false,
  },
  {
    id: "scan",
    title: "Run a security scan",
    description: "After deploy completes, scan SSH, firewall, and container posture.",
    href: "/dashboard",
    icon: Shield,
    done: false,
  },
  {
    id: "alerts",
    title: "Set a cost alert",
    description: "Get emailed when monthly spend crosses your threshold.",
    href: "/dashboard/alerts",
    icon: Bell,
    done: false,
  },
] as const;

type OnboardingChecklistProps = {
  hasDeployments?: boolean;
  hasScans?: boolean;
  hasAlerts?: boolean;
  compact?: boolean;
};

export function OnboardingChecklist({
  hasDeployments = false,
  hasScans = false,
  hasAlerts = false,
  compact = false,
}: OnboardingChecklistProps) {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    setDismissed(isOnboardingComplete());
  }, []);

  const steps = STEPS.map((s) => {
    if (s.id === "deploy") return { ...s, done: hasDeployments };
    if (s.id === "scan") return { ...s, done: hasScans };
    if (s.id === "alerts") return { ...s, done: hasAlerts };
    return s;
  });

  const allDone = steps.every((s) => s.done);

  if (dismissed && !compact && allDone) return null;

  function finish() {
    markOnboardingComplete();
    setDismissed(true);
  }

  if (compact) {
    return (
      <Card className="border-primary/30 bg-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Getting started</CardTitle>
          <CardDescription>
            {steps.filter((s) => s.done).length} of {steps.length} steps complete
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {steps.map((step) => (
            <div key={step.id} className="flex items-center gap-2 text-sm">
              {step.done ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
              ) : (
                <Circle className="h-4 w-4 shrink-0 text-muted-foreground" />
              )}
              <Link href={step.href} className={step.done ? "text-muted-foreground line-through" : "hover:text-primary"}>
                {step.title}
              </Link>
            </div>
          ))}
          <Button asChild size="sm" variant="outline" className="mt-2 w-full">
            <Link href="/dashboard/getting-started">View guide</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-primary/40">
      <CardHeader>
        <CardTitle>Welcome to SafeClaw</CardTitle>
        <CardDescription>
          Follow these steps to go from zero to a hardened OpenClaw instance in under 10 minutes.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <ol className="space-y-4">
          {steps.map((step, i) => (
            <li key={step.id} className="flex gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border text-sm font-medium">
                {step.done ? <CheckCircle2 className="h-5 w-5 text-primary" /> : i + 1}
              </span>
              <div className="flex-1">
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-muted-foreground">{step.description}</p>
                {!step.done && (
                  <Button asChild size="sm" variant="ghost" className="mt-1 h-auto px-0">
                    <Link href={step.href}>Continue →</Link>
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ol>
        <div className="flex flex-wrap gap-2">
          {allDone ? (
            <Button onClick={finish}>Finish setup</Button>
          ) : (
            <Button variant="outline" onClick={finish}>
              Skip for now
            </Button>
          )}
          <Button asChild variant="default">
            <Link href="/dashboard/deploy">Start deploy wizard</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
