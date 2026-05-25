import { FamilyCard } from "./FamilyCard";
import type { FamilySummary } from "@/lib/types";

export function FamilyGrid({ families }: { families: FamilySummary[] }) {
  return (
    <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4">
      {families.map((f, i) => (
        <FamilyCard key={f.key} family={f} priority={i < 4} />
      ))}
    </div>
  );
}
