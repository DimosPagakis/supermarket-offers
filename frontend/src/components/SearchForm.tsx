"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

export function SearchForm({ initial }: { initial?: string }) {
  const router = useRouter();
  const sp = useSearchParams();
  // The initial value reflects whatever ?q was on the URL when this
  // component mounted; after that the input is fully user-controlled.
  // Navigating to a different page re-mounts this component (it's inside
  // the Header layout that re-renders on route changes), so we don't
  // need a useEffect sync.
  const [value, setValue] = useState(initial ?? sp.get("q") ?? "");

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        const trimmed = value.trim();
        const qs = new URLSearchParams();
        if (trimmed) qs.set("q", trimmed);
        router.push(qs.toString() ? `/offers?${qs.toString()}` : "/offers");
      }}
      className="flex w-full max-w-md items-center gap-2"
    >
      <input
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Αναζήτηση π.χ. φέτα"
        aria-label="Αναζήτηση προσφορών"
        className="flex-1 rounded-[var(--radius-soft-pill)] bg-canvas px-4 py-2 text-sm text-ink shadow-inset placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
      />
      <button
        type="submit"
        className="rounded-[var(--radius-soft-pill)] bg-brand px-5 py-2 text-sm font-semibold text-white shadow-raised-brand transition-shadow hover:bg-brand-hover active:shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
      >
        Αναζήτηση
      </button>
    </form>
  );
}
