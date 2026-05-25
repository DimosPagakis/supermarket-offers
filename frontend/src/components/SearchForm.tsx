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
        className="flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-emerald-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
      />
      <button
        type="submit"
        className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
      >
        Αναζήτηση
      </button>
    </form>
  );
}
