"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type Analytics = {
  scan_grades: { grade: string; count: number }[];
  scan_scores_recent: number[];
  alert_triggers_by_month: { month: string; count: number }[];
  open_incidents: number;
  avg_retry_count: number;
};

function maxCount(items: { count: number }[]) {
  return Math.max(...items.map((i) => i.count), 1);
}

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["ops-analytics"],
    queryFn: () => api<Analytics>("/api/v1/ops/analytics"),
    refetchInterval: 60_000,
  });

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Operational analytics</h1>
          <p className="text-muted-foreground">Security scans, cost alerts, and incident signals.</p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/dashboard">← Dashboard</Link>
        </Button>
      </div>

      {isLoading && (
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {data && (
        <div className="mt-8 space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Open incidents</CardTitle>
                <CardDescription>Auto-created on provision failures</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-amber-400">{data.open_incidents}</p>
                <Link href="/dashboard/incidents" className="mt-2 inline-block text-xs text-primary hover:underline">
                  View incidents
                </Link>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Avg deployment retries</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{data.avg_retry_count}</p>
              </CardContent>
            </Card>
          </div>

          {data.scan_grades.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Scan grades</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.scan_grades.map((g) => (
                  <div key={g.grade}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span>Grade {g.grade}</span>
                      <span>{g.count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${(g.count / maxCount(data.scan_grades)) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {data.scan_scores_recent.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Recent scan scores</CardTitle>
              </CardHeader>
              <CardContent className="flex h-24 items-end gap-1">
                {data.scan_scores_recent.map((score, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-t bg-primary/80"
                    style={{ height: `${score}%` }}
                    title={`Score ${score}`}
                  />
                ))}
              </CardContent>
            </Card>
          )}

          {data.alert_triggers_by_month.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Alert triggers by month</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.alert_triggers_by_month.map((m) => (
                  <div key={m.month} className="flex justify-between text-sm">
                    <span>{m.month}</span>
                    <span className="font-medium">{m.count}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {!data.scan_grades.length && !data.alert_triggers_by_month.length && (
            <p className="text-sm text-muted-foreground">
              Run security scans and configure cost alerts to populate analytics.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
