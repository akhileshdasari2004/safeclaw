"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "@/lib/api";

export type DeploymentLogEvent = {
  timestamp: string;
  deployment_id: string;
  level: string;
  step: string;
  message: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useDeploymentLogs(deploymentId: string | undefined, enabled = true) {
  const [logs, setLogs] = useState<DeploymentLogEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [closed, setClosed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const retriesRef = useRef(0);

  const connect = useCallback(() => {
    if (!deploymentId || !enabled) return;
    const token = getToken();
    if (!token) {
      setError("Not authenticated");
      return;
    }

    sourceRef.current?.close();
    setReconnecting(retriesRef.current > 0);

    const url = `${API_URL}/api/v1/logs/${deploymentId}/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    sourceRef.current = es;

    es.addEventListener("open", () => {
      setConnected(true);
      setReconnecting(false);
      setError(null);
      retriesRef.current = 0;
    });

    es.addEventListener("log", (ev) => {
      try {
        const data = JSON.parse(ev.data) as DeploymentLogEvent;
        if (data.step === "heartbeat") return;
        setLogs((prev) => [...prev, data]);
      } catch {
        /* ignore malformed */
      }
    });

    es.addEventListener("heartbeat", () => {
      setConnected(true);
    });

    es.addEventListener("close", () => {
      setClosed(true);
      setConnected(false);
      es.close();
    });

    es.onerror = () => {
      setConnected(false);
      es.close();
      if (retriesRef.current < 5 && !closed) {
        retriesRef.current += 1;
        setReconnecting(true);
        setTimeout(connect, Math.min(1000 * 2 ** retriesRef.current, 15000));
      } else {
        setError("Log stream disconnected");
      }
    };
  }, [deploymentId, enabled, closed]);

  useEffect(() => {
    if (!enabled || !deploymentId) return;
    setLogs([]);
    setClosed(false);
    retriesRef.current = 0;
    connect();
    return () => {
      sourceRef.current?.close();
    };
  }, [deploymentId, enabled, connect]);

  return { logs, connected, reconnecting, closed, error, reconnect: connect };
}
