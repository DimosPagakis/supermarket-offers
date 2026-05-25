import Link from "next/link";

const SOURCES = ["AB Βασιλόπουλος", "Σκλαβενίτης", "Lidl Hellas", "My Market", "Μασούτης"];

export function Footer() {
  return (
    <footer className="mt-12 border-t border-border bg-canvas-muted py-8 text-sm text-ink-muted">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 sm:flex-row sm:justify-between">
        <div>
          <p className="font-semibold text-ink-soft">
            Δεδομένα από: {SOURCES.join(" · ")}
          </p>
          <p className="mt-1 text-xs">
            Ανοιχτά δεδομένα — διαθέσιμα μέσω δημόσιου API.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/about" className="transition-colors hover:text-brand">
            Σχετικά
          </Link>
          <a
            href="https://github.com/"
            target="_blank"
            rel="noreferrer noopener"
            className="transition-colors hover:text-brand"
          >
            GitHub
          </a>
          <a
            href="/api/public/v1/offers"
            className="transition-colors hover:text-brand"
          >
            API
          </a>
        </div>
      </div>
    </footer>
  );
}
