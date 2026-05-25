"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useState } from "react";

type Finding = {
  severity: string;
  title: string;
  description: string;
  remediation: string;
};

type ScanDetail = {
  id: string;
  deployment_id: string;
  score: number;
  grade: string;
  created_at: string;
  findings: {
    score: number;
    grade: string;
    findings: Finding[];
    risk_summary: string;
  };
};

export default function ScanResultsPage() {
  const { id } = useParams<{ id: string }>();
  const [expanded, setExpanded] = useState<number | null>(0);

  const { data, isLoading, error } = useQuery({
    queryKey: ["scan", id],
    queryFn: () => api<ScanDetail>(`/api/v1/scans/${id}`),
  });

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-10">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (error || !data) {
    return <p className="p-10 text-red-400">{(error as Error)?.message ?? "Scan not found"}</p>;
  }

  const findings = data.findings.findings ?? [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-2xl font-bold">Security scan</h1>
      <p className="text-muted-foreground">{new Date(data.created_at).toLocaleString()}</p>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle className="text-base">Score</CardTitle></CardHeader>
          <CardContent><p className="text-4xl font-bold">{data.score}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Grade</CardTitle></CardHeader>
          <CardContent><p className="text-4xl font-bold text-primary">{data.grade}</p></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Risk</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {data.findings.risk_summary || "—"}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle className="text-base">Findings ({findings.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {findings.length === 0 && (
            <p className="text-muted-foreground">No issues detected.</p>
          )}
          {findings.map((f, i) => (
            <div key={i} className="rounded-lg border border-border">
              <button
                type="button"
                className="flex w-full items-center justify-between px-4 py-3 text-left"
                onClick={() => setExpanded(expanded === i ? null : i)}
              >
                <span className="flex items-center gap-2">
                  <Badge variant={f.severity}>{f.severity}</Badge>
                  <span className="font-medium">{f.title}</span>
                </span>
                <span className="text-xs text-muted-foreground">{expanded === i ? "−" : "+"}</span>
              </button>
              {expanded === i && (
                <div className="border-t border-border px-4 py-3 text-sm">
                  <p className="text-muted-foreground">{f.description}</p>
                  <pre className="mt-3 overflow-x-auto rounded bg-muted p-3 text-xs">{f.remediation}</pre>
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2"
                    onClick={() => navigator.clipboard.writeText(f.remediation)}
                  >
                    Copy remediation
                  </Button>
                </div>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
