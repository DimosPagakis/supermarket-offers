export function OfferCardSkeleton() {
  return (
    <div className="flex animate-pulse flex-col overflow-hidden rounded-[var(--radius-soft)] bg-canvas p-3 shadow-raised">
      <div className="aspect-square w-full rounded-[var(--radius-soft)] bg-canvas shadow-inset" />
      <div className="space-y-2 px-1 pt-3">
        <div className="h-3 w-16 rounded bg-canvas shadow-inset" />
        <div className="h-4 w-full rounded bg-canvas shadow-inset" />
        <div className="h-4 w-3/4 rounded bg-canvas shadow-inset" />
        <div className="h-5 w-20 rounded bg-canvas shadow-inset" />
      </div>
    </div>
  );
}

export function OfferGridSkeleton({ count = 12 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {Array.from({ length: count }).map((_, i) => (
        <OfferCardSkeleton key={i} />
      ))}
    </div>
  );
}
