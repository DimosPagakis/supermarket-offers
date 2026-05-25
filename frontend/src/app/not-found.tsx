import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <h1 className="text-4xl font-bold text-ink">404</h1>
      <p className="text-ink-soft">Δεν βρήκαμε αυτή τη σελίδα.</p>
      <Link
        href="/"
        className="rounded-[var(--radius-soft-pill)] bg-brand px-5 py-2 text-sm font-semibold text-white shadow-raised-brand transition-shadow hover:bg-brand-hover active:shadow-inset focus:outline-none focus-visible:ring-2 focus-visible:ring-brand"
      >
        Επιστροφή στην αρχική
      </Link>
    </div>
  );
}
