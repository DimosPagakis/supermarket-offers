export function OfferCardSkeleton() {
  return (
    <div className="flex animate-pulse flex-col overflow-hidden rounded-[var(--radius-card)] border border-border bg-surface shadow-card">
      <div className="aspect-square w-full bg-canvas-muted" />
      <div className="space-y-2 p-3">
        <div className="h-3 w-16 rounded bg-canvas-muted" />
        <div className="h-4 w-full rounded bg-canvas-muted" />
        <div className="h-4 w-3/4 rounded bg-canvas-muted" />
        <div className="h-5 w-20 rounded bg-canvas-muted" />
      </div>
    </div>
  );
}

export function OfferGridSkeleton({ count = 12 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {Array.from({ length: count }).map((_, i) => (
        <OfferCardSkeleton key={i} />
      ))}
    </div>
  );
}
