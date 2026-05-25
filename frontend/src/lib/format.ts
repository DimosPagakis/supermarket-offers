/**
 * Locale-aware formatters. All UI uses these — never call Intl directly
 * from components so the strings stay consistent.
 */

const EURO = new Intl.NumberFormat("el-GR", {
  style: "currency",
  currency: "EUR",
});

const PERCENT = new Intl.NumberFormat("el-GR", {
  style: "percent",
  maximumFractionDigits: 0,
});

const DATE_SHORT = new Intl.DateTimeFormat("el-GR", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

const DATE_DAY_MONTH = new Intl.DateTimeFormat("el-GR", {
  day: "2-digit",
  month: "2-digit",
});

export function formatPrice(value: number, currency = "EUR"): string {
  if (currency === "EUR") return EURO.format(value);
  return new Intl.NumberFormat("el-GR", {
    style: "currency",
    currency,
  }).format(value);
}

export function formatDiscountPct(pct: number | null): string {
  if (pct == null) return "";
  return PERCENT.format(pct / 100);
}

export function formatDate(iso: string | null): string {
  if (!iso) return "";
  return DATE_SHORT.format(new Date(iso));
}

export function formatDayMonth(iso: string | null): string {
  if (!iso) return "";
  return DATE_DAY_MONTH.format(new Date(iso));
}

/**
 * "Έως 03/06" / "Λήγει σε 4 ημέρες" / "Λήγει σήμερα" / "Έληξε".
 * Pure function — pass a reference "now" to keep server + client output
 * stable and avoid hydration mismatches.
 */
export function formatValidity(validTo: string | null, now: Date = new Date()): string {
  if (!validTo) return "";
  // Compare on day boundaries in UTC so the result is stable regardless
  // of the runtime's local timezone (server vs. client, CI vs. local).
  const [y, m, d] = validTo.split("-").map(Number);
  const endUtc = Date.UTC(y, (m ?? 1) - 1, d ?? 1);
  const nowUtc = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
  );
  const diffDays = Math.round((endUtc - nowUtc) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return "Έληξε";
  if (diffDays === 0) return "Λήγει σήμερα";
  if (diffDays === 1) return "Λήγει αύριο";
  if (diffDays <= 7) return `Λήγει σε ${diffDays} ημέρες`;
  return `Έως ${formatDayMonth(validTo)}`;
}

export function todayIso(now: Date = new Date()): string {
  return now.toISOString().slice(0, 10);
}
