import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  value?: string | number;
  subtitle?: string;
  icon?: ReactNode;
  className?: string;
  children?: ReactNode;
}

export function StatsCard({
  title,
  value,
  subtitle,
  icon,
  className,
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-6 shadow-sm",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="mt-1 text-3xl font-bold text-card-foreground">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

export function Card({ className, children }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-6 shadow-sm",
        className,
      )}
    >
      {children}
    </div>
  );
}
