import Link from "next/link";
import { Suspense } from "react";
import { SearchForm } from "./SearchForm";

export function Header() {
  return (
    <header className="sticky top-0 z-20 bg-canvas shadow-raised">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-lg font-bold text-brand transition-colors hover:text-brand-hover"
          >
            <span aria-hidden>🛒</span>
            <span>Προσφορές</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm text-ink-soft">
            <Link
              href="/offers"
              className="rounded-md py-1 transition-colors hover:text-brand"
            >
              Όλες οι προσφορές
            </Link>
            <Link
              href="/compare"
              className="rounded-md py-1 transition-colors hover:text-brand"
            >
              Σύγκριση
            </Link>
            <Link
              href="/families"
              className="rounded-md py-1 transition-colors hover:text-brand"
            >
              Παραλλαγές
            </Link>
            <Link
              href="/about"
              className="rounded-md py-1 transition-colors hover:text-brand"
            >
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
