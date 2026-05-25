type Props = {
  title?: string;
  message?: string;
};

export function EmptyState({
  title = "Δεν βρέθηκαν προσφορές",
  message = "Δοκίμασε διαφορετικά φίλτρα ή έλεγξε ξανά αύριο.",
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-zinc-300 bg-white px-6 py-16 text-center dark:border-zinc-700 dark:bg-zinc-900">
      <div className="text-5xl" aria-hidden>
        🛒
      </div>
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
        {title}
      </h2>
      <p className="max-w-sm text-sm text-zinc-600 dark:text-zinc-400">
        {message}
      </p>
    </div>
  );
}
