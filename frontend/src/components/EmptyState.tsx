type Props = {
  title?: string;
  message?: string;
};

export function EmptyState({
  title = "Δεν βρέθηκαν προσφορές",
  message = "Δοκίμασε διαφορετικά φίλτρα ή έλεγξε ξανά αύριο.",
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-soft)] bg-canvas px-6 py-16 text-center shadow-raised">
      <div
        className="flex h-16 w-16 items-center justify-center rounded-[var(--radius-soft-pill)] bg-canvas text-3xl text-brand shadow-inset"
        aria-hidden
      >
        🛒
      </div>
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="max-w-sm text-sm text-ink-soft">{message}</p>
    </div>
  );
}
