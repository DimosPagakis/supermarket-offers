import { CanonicalCard } from "./CanonicalCard";
import type { CanonicalProductSummary } from "@/lib/types";

export function CanonicalGrid({
  products,
}: {
  products: CanonicalProductSummary[];
}) {
  return (
    <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
      {products.map((p, i) => (
        <CanonicalCard key={p.id} product={p} priority={i < 6} />
      ))}
    </div>
  );
}
