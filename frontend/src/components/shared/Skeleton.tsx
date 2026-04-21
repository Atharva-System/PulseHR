import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-slate-200/80 dark:bg-slate-700/40",
        className,
      )}
    />
  );
}

export function AuthGateSkeleton() {
  return (
    <div className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-10 w-44 rounded-xl" />
          <Skeleton className="h-9 w-28 rounded-full" />
        </div>
        <div className="grid gap-6 lg:grid-cols-[240px,1fr]">
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <Skeleton className="mb-4 h-5 w-24" />
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-11 w-full rounded-xl" />
              ))}
            </div>
          </div>
          <div className="space-y-6">
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <Skeleton className="h-8 w-56" />
              <Skeleton className="mt-3 h-4 w-80 max-w-full" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="rounded-2xl border border-border bg-card p-6 shadow-sm"
                >
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="mt-4 h-8 w-16" />
                  <Skeleton className="mt-3 h-3 w-28" />
                </div>
              ))}
            </div>
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <Skeleton className="h-5 w-44" />
              <Skeleton className="mt-5 h-72 w-full rounded-2xl" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatsGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="rounded-xl border border-border bg-card p-6 shadow-sm"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-3">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-3 w-28" />
            </div>
            <Skeleton className="h-12 w-12 rounded-xl" />
          </div>
        </div>
      ))}
    </div>
  );
}

function ChartCardSkeleton({
  titleWidth = "w-40",
  height = "h-64",
  className,
}: {
  titleWidth?: string;
  height?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-6 shadow-sm",
        className,
      )}
    >
      <Skeleton className={cn("h-4", titleWidth)} />
      <Skeleton className={cn("mt-5 w-full rounded-2xl", height)} />
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-44" />
        <Skeleton className="h-4 w-56" />
      </div>
      <StatsGridSkeleton />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCardSkeleton />
        <ChartCardSkeleton titleWidth="w-48" />
        <ChartCardSkeleton
          titleWidth="w-44"
          className="lg:col-span-2"
          height="h-72"
        />
      </div>
      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-16" />
        </div>
        <TableRowsSkeleton columns={6} rows={5} />
      </div>
    </div>
  );
}

export function ReportsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-44" />
        </div>
        <Skeleton className="h-10 w-36 rounded-lg" />
      </div>
      <StatsGridSkeleton />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCardSkeleton titleWidth="w-36" />
        <ChartCardSkeleton titleWidth="w-40" />
        <ChartCardSkeleton titleWidth="w-36" />
        <ChartCardSkeleton titleWidth="w-32" />
      </div>
    </div>
  );
}

export function TableRowsSkeleton({
  columns = 6,
  rows = 5,
}: {
  columns?: number;
  rows?: number;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            {Array.from({ length: columns }).map((_, index) => (
              <th key={index} className="px-6 py-3 text-left">
                <Skeleton className="h-3 w-16" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex} className="border-b border-border last:border-0">
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="px-6 py-4">
                  <Skeleton
                    className={cn(
                      "h-4",
                      colIndex === 0
                        ? "w-20"
                        : colIndex === 1
                          ? "w-40"
                          : "w-24",
                    )}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TicketDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-5 w-36" />
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="space-y-3">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-8 w-72 max-w-full" />
            <div className="flex flex-wrap gap-3">
              <Skeleton className="h-6 w-20 rounded-full" />
              <Skeleton className="h-6 w-24 rounded-full" />
              <Skeleton className="h-6 w-32 rounded-full" />
            </div>
          </div>
          <div className="space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-10 w-32 rounded-lg" />
          </div>
        </div>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-4 w-28" />
            </div>
          ))}
        </div>
        <div className="mt-6 space-y-2">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      </div>
      <Skeleton className="h-10 w-48 rounded-lg" />
      <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <Skeleton className="h-4 w-36" />
          <div className="mt-5 space-y-4">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="space-y-2 rounded-xl bg-muted/30 p-4">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="mt-5 h-24 w-full rounded-xl" />
          <Skeleton className="mt-4 h-10 w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}

export function PolicyListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="rounded-xl border border-input bg-white px-5 py-4"
        >
          <div className="flex items-center gap-3">
            <Skeleton className="h-5 w-5 rounded" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-44" />
              <Skeleton className="h-3 w-64 max-w-full" />
            </div>
            <Skeleton className="h-8 w-24 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ThreadListSkeleton({ count = 7 }: { count?: number }) {
  return (
    <div className="space-y-0">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="flex items-start gap-3 border-b border-input/50 px-4 py-3"
        >
          <Skeleton className="h-9 w-9 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-10" />
            </div>
            <Skeleton className="h-3 w-36" />
            <Skeleton className="h-5 w-20 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function MessageColumnSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-4 px-5 py-4">
      {Array.from({ length: count }).map((_, index) => {
        const isRight = index % 2 === 0;
        return (
          <div
            key={index}
            className={cn("flex", isRight ? "justify-end" : "justify-start")}
          >
            <div
              className={cn(
                "max-w-[70%] space-y-2 rounded-2xl px-4 py-3",
                isRight ? "bg-primary/5" : "bg-muted/40",
              )}
            >
              {!isRight && <Skeleton className="h-3 w-20" />}
              <Skeleton className="h-4 w-52 max-w-full" />
              <Skeleton className="h-4 w-40 max-w-full" />
              <Skeleton className="ml-auto h-3 w-12" />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function TicketCardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="rounded-xl border border-border bg-white p-5 shadow-sm"
        >
          <div className="mb-3 flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-5 w-48 max-w-full" />
              <Skeleton className="h-3 w-28" />
            </div>
            <Skeleton className="h-7 w-24 rounded-full" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="mt-2 h-4 w-5/6" />
          <div className="mt-4 flex items-center justify-between">
            <Skeleton className="h-6 w-20 rounded-full" />
            <Skeleton className="h-3 w-36" />
          </div>
          <div className="mt-4 border-t border-border/50 pt-3">
            <div className="flex gap-1">
              {Array.from({ length: 4 }).map((_, stepIndex) => (
                <Skeleton key={stepIndex} className="h-2 flex-1 rounded-full" />
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ChatHistorySkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-4 py-4">
      {Array.from({ length: count }).map((_, index) => {
        const isUser = index % 2 === 1;
        return (
          <div
            key={index}
            className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}
          >
            {!isUser && <Skeleton className="mt-1 h-8 w-8 rounded-lg" />}
            <div
              className={cn(
                "max-w-[75%] space-y-2 rounded-2xl px-4 py-3",
                isUser ? "bg-primary/10" : "border border-border bg-white",
              )}
            >
              <Skeleton className="h-4 w-56 max-w-full" />
              <Skeleton className="h-4 w-40 max-w-full" />
              {!isUser && (
                <div className="flex gap-2 pt-1">
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
              )}
            </div>
            {isUser && <Skeleton className="mt-1 h-8 w-8 rounded-lg" />}
          </div>
        );
      })}
    </div>
  );
}

export function AgentGridSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Skeleton className="h-12 w-12 rounded-xl" />
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-80 max-w-full" />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: count }).map((_, index) => (
          <div
            key={index}
            className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm"
          >
            <div className="mb-4 flex items-center gap-3">
              <Skeleton className="h-11 w-11 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-5 w-20 rounded-full" />
              </div>
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="mt-2 h-4 w-5/6" />
            <Skeleton className="mt-4 h-6 w-32 rounded-md" />
            <Skeleton className="mt-6 h-10 w-full rounded-lg" />
          </div>
        ))}
      </div>
    </div>
  );
}
