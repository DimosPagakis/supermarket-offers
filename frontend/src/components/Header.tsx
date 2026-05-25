import Link from "next/link";
import { Suspense } from "react";
import { SearchForm } from "./SearchForm";

export function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 text-lg font-bold text-emerald-600">
            <span aria-hidden>🛒</span>
            <span>Προσφορές</span>
          </Link>
          <nav className="flex items-center gap-3 text-sm text-zinc-600 dark:text-zinc-400">
            <Link href="/offers" className="hover:text-emerald-600">
              Όλες οι προσφορές
            </Link>
            <Link href="/about" className="hover:text-emerald-600">
              Σχετικά
            </Link>
          </nav>
        </div>
        <Suspense fallback={<div className="h-10 w-full max-w-md" />}>
          <SearchForm />
        </Suspense>
      </div>
    </header>
  );
}
