import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/site-header";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SafeClaw — Hardened OpenClaw in minutes",
  description: "Deploy a hardened OpenClaw instance without touching a terminal.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <SiteHeader />
          <main className="min-h-[calc(100vh-4rem)]">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
