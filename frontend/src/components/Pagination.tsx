import Link from "next/link";

type Props = {
  currentPage: number;
  lastPage: number;
  /** Returns the href for a given page; we delegate URL building to the caller. */
  hrefForPage: (page: number) => string;
};

function pagesToShow(current: number, last: number): (number | "…")[] {
  if (last <= 7) return Array.from({ length: last }, (_, i) => i + 1);
  const pages: (number | "…")[] = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(last - 1, current + 1);
  if (start > 2) pages.push("…");
  for (let i = start; i <= end; i++) pages.push(i);
  if (end < last - 1) pages.push("…");
  pages.push(last);
  return pages;
}

export function Pagination({ currentPage, lastPage, hrefForPage }: Props) {
  if (lastPage <= 1) return null;
  const items = pagesToShow(currentPage, lastPage);
  const prev = currentPage > 1 ? hrefForPage(currentPage - 1) : null;
  const next = currentPage < lastPage ? hrefForPage(currentPage + 1) : null;

  const baseBtn =
    "inline-flex h-9 min-w-9 items-center justify-center rounded-md px-3 text-sm font-medium transition";

  return (
    <nav className="flex items-center justify-center gap-1" aria-label="Σελιδοποίηση">
      {prev ? (
        <Link
          href={prev}
          className={`${baseBtn} border border-zinc-200 text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-800`}
        >
          ← Προηγούμενη
        </Link>
      ) : (
        <span className={`${baseBtn} border border-zinc-200 text-zinc-300 dark:border-zinc-800 dark:text-zinc-700`}>
          ← Προηγούμενη
        </span>
      )}
      {items.map((p, i) =>
        p === "…" ? (
          <span key={`gap-${i}`} className="px-2 text-zinc-400">
            …
          </span>
        ) : p === currentPage ? (
          <span
            key={p}
            className={`${baseBtn} bg-emerald-600 text-white`}
            aria-current="page"
          >
            {p}
          </span>
        ) : (
          <Link
            key={p}
            href={hrefForPage(p)}
            className={`${baseBtn} border border-zinc-200 text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-800`}
          >
            {p}
          </Link>
        ),
      )}
      {next ? (
        <Link
          href={next}
          className={`${baseBtn} border border-zinc-200 text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-800`}
        >
          Επόμενη →
        </Link>
      ) : (
        <span className={`${baseBtn} border border-zinc-200 text-zinc-300 dark:border-zinc-800 dark:text-zinc-700`}>
          Επόμενη →
        </span>
      )}
    </nav>
  );
}
