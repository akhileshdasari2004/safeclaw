"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getToken } from "@/lib/api";

export function SiteHeader() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [authed, setAuthed] = useState(false);
  useEffect(() => setAuthed(!!getToken()), [pathname]);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="font-semibold tracking-tight text-primary">
          SafeClaw
        </Link>
        <nav className="hidden gap-6 text-sm md:flex">
          <Link href="/pricing" className={pathname === "/pricing" ? "text-primary" : "text-muted-foreground hover:text-foreground"}>
            Pricing
          </Link>
          {authed && (
            <>
              <Link href="/dashboard" className={pathname === "/dashboard" ? "text-primary" : "text-muted-foreground hover:text-foreground"}>
                Dashboard
              </Link>
              <Link href="/dashboard/getting-started" className={pathname === "/dashboard/getting-started" ? "text-primary" : "text-muted-foreground hover:text-foreground"}>
                Guide
              </Link>
              <Link href="/dashboard/analytics" className={pathname === "/dashboard/analytics" ? "text-primary" : "text-muted-foreground hover:text-foreground"}>
                Analytics
              </Link>
            </>
          )}
        </nav>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
          {authed ? (
            <Button asChild size="sm"><Link href="/dashboard">Dashboard</Link></Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm"><Link href="/login">Log in</Link></Button>
              <Button asChild size="sm"><Link href="/pricing">Get Started</Link></Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
