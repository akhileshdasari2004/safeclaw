"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield, Zap, Cloud } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16">
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <p className="mb-4 text-sm font-medium text-primary">Production-ready self-hosting</p>
        <h1 className="text-4xl font-bold tracking-tight md:text-6xl">
          Deploy hardened OpenClaw in under 5 minutes
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          SafeClaw provisions a VPS, hardens Ubuntu 22.04, installs Docker and OpenClaw — with security scans and cost alerts built in.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Button asChild size="lg"><Link href="/pricing">Get Started</Link></Button>
          <Button asChild variant="outline" size="lg"><Link href="/login">Log in</Link></Button>
        </div>
      </motion.section>

      <section className="mt-24 grid gap-6 md:grid-cols-3">
        {[
          { icon: Cloud, title: "One-click deploy", desc: "Hetzner or DigitalOcean — pick region, plan, and SSH key." },
          { icon: Shield, title: "Security first", desc: "UFW, fail2ban, SSH hardening, and automated scans with grades." },
          { icon: Zap, title: "Cost control", desc: "Monthly estimates and email alerts when spend crosses your threshold." },
        ].map((f, i) => (
          <motion.div key={f.title} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
            <Card>
              <CardHeader>
                <f.icon className="mb-2 h-8 w-8 text-primary" />
                <CardTitle>{f.title}</CardTitle>
                <CardDescription>{f.desc}</CardDescription>
              </CardHeader>
            </Card>
          </motion.div>
        ))}
      </section>
    </div>
  );
}
