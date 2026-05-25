import { OfferCard } from "./OfferCard";
import type { Offer } from "@/lib/types";

export function OfferGrid({ offers }: { offers: Offer[] }) {
  return (
    <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {offers.map((o, i) => (
        <OfferCard key={o.id} offer={o} priority={i < 5} />
      ))}
    </div>
  );
}
