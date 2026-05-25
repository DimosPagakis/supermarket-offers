type Props = {
  title?: string;
  message?: string;
};

export function EmptyState({
  title = "Δεν βρέθηκαν προσφορές",
  message = "Δοκίμασε διαφορετικά φίλτρα ή έλεγξε ξανά αύριο.",
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-card)] border border-dashed border-border-strong bg-surface px-6 py-16 text-center">
      <div
        className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-fade text-3xl text-brand"
        aria-hidden
      >
        🛒
      </div>
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="max-w-sm text-sm text-ink-soft">{message}</p>
    </div>
  );
}
