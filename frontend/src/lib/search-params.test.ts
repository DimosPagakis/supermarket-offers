import { describe, expect, it } from "vitest";
import {
  parseCanonicalQuery,
  parseOfferQuery,
  toCanonicalSearchString,
  toSearchString,
} from "./search-params";

/**
 * The inbound URL contract. Every list page parses its `searchParams`
 * through these functions; they are the only runtime guard between
 * user-crafted URLs and the typed query objects we hand the backend.
 * See docs/architecture/search-params-contract.md.
 */

describe("parseOfferQuery", () => {
  it("returns an empty query for empty params", () => {
    expect(parseOfferQuery({})).toEqual({});
  });

  it("splits brand CSV into an array, trimming and dropping empties", () => {
    expect(parseOfferQuery({ brand: " ab , lidl ,, " })).toEqual({
      brand: ["ab", "lidl"],
    });
  });

  it("splits category CSV the same way", () => {
    expect(parseOfferQuery({ category: "Τυριά,Ποτά" })).toEqual({
      category: ["Τυριά", "Ποτά"],
    });
  });

  it("takes the first entry when a param arrives as an array", () => {
    // Next gives us `string | string[] | undefined`; the parser must
    // not concatenate or crash on the array case.
    expect(parseOfferQuery({ q: ["feta", "γάλα"] })).toEqual({ q: "feta" });
  });

  it("rejects min_discount outside [0, 100] and NaN", () => {
    expect(parseOfferQuery({ min_discount: "-5" })).toEqual({});
    expect(parseOfferQuery({ min_discount: "101" })).toEqual({});
    expect(parseOfferQuery({ min_discount: "abc" })).toEqual({});
    expect(parseOfferQuery({ min_discount: "" })).toEqual({});
    expect(parseOfferQuery({ min_discount: "20" })).toEqual({ min_discount: 20 });
  });

  it("only honours literal true/false for has_discount", () => {
    expect(parseOfferQuery({ has_discount: "true" })).toEqual({
      has_discount: true,
    });
    expect(parseOfferQuery({ has_discount: "false" })).toEqual({
      has_discount: false,
    });
    expect(parseOfferQuery({ has_discount: "1" })).toEqual({});
    expect(parseOfferQuery({ has_discount: "yes" })).toEqual({});
  });

  it("gates the sort enum and dir enum", () => {
    expect(parseOfferQuery({ sort: "price", dir: "asc" })).toEqual({
      sort: "price",
      dir: "asc",
    });
    expect(parseOfferQuery({ sort: "evil", dir: "sideways" })).toEqual({});
  });

  it("floors page and rejects non-positive values", () => {
    expect(parseOfferQuery({ page: "3.7" })).toEqual({ page: 3 });
    expect(parseOfferQuery({ page: "0" })).toEqual({});
    expect(parseOfferQuery({ page: "-1" })).toEqual({});
    expect(parseOfferQuery({ page: "nope" })).toEqual({});
  });

  it("clamps per_page to 100 and rejects non-positive values", () => {
    expect(parseOfferQuery({ per_page: "999" })).toEqual({ per_page: 100 });
    expect(parseOfferQuery({ per_page: "0" })).toEqual({});
    expect(parseOfferQuery({ per_page: "25" })).toEqual({ per_page: 25 });
  });

  it("passes valid_on through verbatim (date validation is the backend's job)", () => {
    expect(parseOfferQuery({ valid_on: "2026-05-25" })).toEqual({
      valid_on: "2026-05-25",
    });
  });
});

describe("parseCanonicalQuery", () => {
  it("returns an empty query for empty params", () => {
    expect(parseCanonicalQuery({})).toEqual({});
  });

  it("treats category as a scalar (single-select on /compare)", () => {
    // Offers allow multi-select; canonical only one. Confirm the
    // parser does not silently CSV-split.
    expect(parseCanonicalQuery({ category: "Ποτά" })).toEqual({
      category: "Ποτά",
    });
  });

  it("rejects min_brands outside [1, 10] and NaN", () => {
    expect(parseCanonicalQuery({ min_brands: "0" })).toEqual({});
    expect(parseCanonicalQuery({ min_brands: "11" })).toEqual({});
    expect(parseCanonicalQuery({ min_brands: "nope" })).toEqual({});
    expect(parseCanonicalQuery({ min_brands: "3" })).toEqual({ min_brands: 3 });
  });

  it("gates the canonical sort enum", () => {
    expect(parseCanonicalQuery({ sort: "brands_count" })).toEqual({
      sort: "brands_count",
    });
    expect(parseCanonicalQuery({ sort: "members_count" })).toEqual({
      sort: "members_count",
    });
    expect(parseCanonicalQuery({ sort: "display_name" })).toEqual({
      sort: "display_name",
    });
    expect(parseCanonicalQuery({ sort: "price" })).toEqual({});
  });
});

describe("toSearchString / toCanonicalSearchString", () => {
  it("round-trips a non-trivial offer query (modulo encoding)", () => {
    const parsed = parseOfferQuery({
      brand: "ab,lidl",
      min_discount: "20",
      sort: "price",
      dir: "asc",
      page: "2",
    });
    const qs = toSearchString(parsed);
    const sp = new URLSearchParams(qs);
    expect(sp.get("brand")).toBe("ab,lidl");
    expect(sp.get("min_discount")).toBe("20");
    expect(sp.get("sort")).toBe("price");
    expect(sp.get("dir")).toBe("asc");
    expect(sp.get("page")).toBe("2");
  });

  it("drops page=1 from the canonical query string", () => {
    // Pins the documented "don't emit page when it's the default"
    // behaviour — keeps shareable URLs tidy.
    expect(toCanonicalSearchString({ page: 1, brand: ["ab"] })).toBe("brand=ab");
    expect(toCanonicalSearchString({ page: 2, brand: ["ab"] })).toBe(
      "brand=ab&page=2",
    );
  });
});
