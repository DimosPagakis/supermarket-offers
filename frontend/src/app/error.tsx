"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <h1 className="text-2xl font-bold">Κάτι πήγε στραβά</h1>
      <p className="max-w-md text-sm text-zinc-600 dark:text-zinc-400">
        Δεν καταφέραμε να φορτώσουμε τις προσφορές. Δοκίμασε ξανά σε λίγο.
      </p>
      <button
        onClick={reset}
        type="button"
        className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
      >
        Επανάληψη
      </button>
    </div>
  );
}
