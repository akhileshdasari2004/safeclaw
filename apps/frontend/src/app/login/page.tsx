"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [licenseKey, setLicenseKey] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const path = mode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
      const body =
        mode === "login"
          ? { email, password }
          : { email, password, license_key: licenseKey || undefined };
      const res = await api<{ access_token: string }>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setToken(res.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Auth failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-16">
      <Card>
        <CardHeader>
          <CardTitle>{mode === "login" ? "Log in" : "Create account"}</CardTitle>
          <CardDescription>Access your SafeClaw dashboard</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <Input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <Input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
            {mode === "register" && (
              <Input placeholder="License key (optional)" value={licenseKey} onChange={(e) => setLicenseKey(e.target.value)} />
            )}
            {error && <p className="text-sm text-red-400">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Please wait…" : mode === "login" ? "Log in" : "Register"}
            </Button>
          </form>
          <button
            type="button"
            className="mt-4 w-full text-center text-sm text-muted-foreground hover:text-foreground"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Need an account? Register" : "Have an account? Log in"}
          </button>
          <p className="mt-4 text-center text-sm">
            <Link href="/pricing" className="text-primary hover:underline">Get a license</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
