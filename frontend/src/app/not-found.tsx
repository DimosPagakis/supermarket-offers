import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Δεν βρήκαμε αυτή τη σελίδα.
      </p>
      <Link
        href="/"
        className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
      >
        Επιστροφή στην αρχική
      </Link>
    </div>
  );
}
