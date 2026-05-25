import { describe, expect, it } from "vitest";
import { formatDiscountPct, formatPrice, formatValidity, todayIso } from "./format";

describe("formatPrice", () => {
  it("renders EUR in Greek locale", () => {
    // 6,08 € (with NBSP between number and symbol — locale dependent).
    const out = formatPrice(6.08);
    expect(out).toMatch(/6,08/);
    expect(out).toMatch(/€/);
  });
});

describe("formatDiscountPct", () => {
  it("renders percentage with localized %", () => {
    expect(formatDiscountPct(25)).toMatch(/25\s?%/);
  });
  it("returns empty string for null", () => {
    expect(formatDiscountPct(null)).toBe("");
  });
});

describe("formatValidity", () => {
  const now = new Date("2026-05-25T12:00:00Z");
  it("returns expired when past", () => {
    expect(formatValidity("2026-05-20", now)).toBe("Έληξε");
  });
  it("returns today", () => {
    expect(formatValidity("2026-05-25", now)).toBe("Λήγει σήμερα");
  });
  it("returns tomorrow", () => {
    expect(formatValidity("2026-05-26", now)).toBe("Λήγει αύριο");
  });
  it("returns N days when within a week", () => {
    expect(formatValidity("2026-05-29", now)).toContain("ημέρες");
  });
  it("returns short date when far in the future", () => {
    expect(formatValidity("2026-06-15", now)).toMatch(/^Έως/);
  });
  it("returns empty for null", () => {
    expect(formatValidity(null, now)).toBe("");
  });
});

describe("todayIso", () => {
  it("formats as YYYY-MM-DD", () => {
    expect(todayIso(new Date("2026-05-25T15:00:00Z"))).toBe("2026-05-25");
  });
});
