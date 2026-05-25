import Link from "next/link";

const SOURCES = ["AB Βασιλόπουλος", "Σκλαβενίτης", "Lidl Hellas", "My Market", "Μασούτης"];

export function Footer() {
  return (
    <footer className="mt-12 border-t border-zinc-200 bg-zinc-50 py-8 text-sm text-zinc-600 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-400">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 sm:flex-row sm:justify-between">
        <div>
          <p className="font-semibold text-zinc-700 dark:text-zinc-300">
            Δεδομένα από: {SOURCES.join(" · ")}
          </p>
          <p className="mt-1 text-xs">
            Ανοιχτά δεδομένα — διαθέσιμα μέσω δημόσιου API.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/about" className="hover:text-emerald-600">
            Σχετικά
          </Link>
          <a
            href="https://github.com/"
            target="_blank"
            rel="noreferrer noopener"
            className="hover:text-emerald-600"
          >
            GitHub
          </a>
          <a
            href="/api/public/v1/offers"
            className="hover:text-emerald-600"
          >
            API
          </a>
        </div>
      </div>
    </footer>
  );
}
