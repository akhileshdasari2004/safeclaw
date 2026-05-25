import { cn } from "@/lib/utils";

const VARIANTS: Record<string, string> = {
  critical: "bg-red-500/20 text-red-300 border-red-500/40",
  high: "bg-orange-500/20 text-orange-300 border-orange-500/40",
  medium: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  low: "bg-blue-500/20 text-blue-300 border-blue-500/40",
  info: "bg-muted text-muted-foreground",
};

export function Badge({
  children,
  variant = "info",
  className,
}: {
  children: React.ReactNode;
  variant?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium capitalize",
        VARIANTS[variant] ?? VARIANTS.info,
        className
      )}
    >
      {children}
    </span>
  );
}
