import { CanonicalCard } from "./CanonicalCard";
import type { CanonicalProductSummary } from "@/lib/types";

export function CanonicalGrid({
  products,
}: {
  products: CanonicalProductSummary[];
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {products.map((p, i) => (
        <CanonicalCard key={p.id} product={p} priority={i < 5} />
      ))}
    </div>
  );
}
