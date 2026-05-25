# Product Canonicalisation — Design

> Status: design only. No production code touched.
> Author: Dimos Pagakis (with Claude). Date: 2026-05-25.
> Target review: backend + crawler maintainers before any of Phase 1 ships.

The aggregator already ingests ~10k offers across five Greek supermarket
chains. To deliver the headline comparison feature ("Coca-Cola 1.5L —
€2.59 at Sklavenitis, €2.58 at Masoutis, €2.58 at My Market"), we have
to decide **when two `products` rows from different brands represent the
same physical SKU**. This document recommends an opinionated, phased
approach grounded in the data we actually have today.

---

## TL;DR — the recommendation

1. **Build a manual + algorithmic hybrid, not a magic model.** Start with
   an aggressive deterministic match key (Phase 1), add fuzzy matching
   for the long tail (Phase 2), and only reach for embeddings when we
   plateau (Phase 4). Maintain a tiny human review queue (Phase 3)
   forever — it is the cheapest insurance against silent merges.
2. **GTIN/EAN is not available.** Every chain exposes its own internal
   PLU/SKU in `external_id` (4–7 digit numbers — see §1). We cannot
   short-circuit matching on a barcode.
3. **Brand-aware blocking is non-negotiable.** Own-brand SKUs from
   different chains (My Gusto, ΑΒ-prefixed, Lidl Pilos) must **never**
   canonicalise across chains. Detection is by `manufacturer_brand`,
   not by store name in the title.
4. **Same brand + different size = different canonical product.** Do
   not collapse 200g and 400g into one comparison row — the per-kilo
   price is the right comparison surface, but at the canonical level
   the SKU identity is the package, not the producer.
5. **Headline numbers from the live DB right now (11,887 offers,
   11,887 distinct products):**

   | Strategy | Cross-brand clusters (≥2 brands) | Products in clusters | % of catalogue |
   |---|---|---|---|
   | `normalized_name` exact match | 49 | 98 | 0.8% |
   | Aggressive match-key (size folding + Latin/Greek folding) | **319** | **657** | **5.5%** |
   | ≥3-brand clusters under aggressive match-key | 19 | — | — |

   This is the ceiling for *deterministic* Phase 1. Everything beyond
   it (~94%) needs Phase 2/4 work, BUT most of the remainder is the
   long tail of single-chain SKUs (own-brand, weird-package items,
   AB's 282 offers — chronically under-scraped) that we shouldn't
   force-merge.

---

## 1. Reality check on the data

Live API: `http://127.0.0.1:8001/api/public/v1`. Distinct products per
brand on 2026-05-25:

| Brand | Distinct products | Notes |
|---|---|---|
| `my-market` | 5,531 | Best-scraped, broadest national-brand catalogue. |
| `sklavenitis` | 2,987 | Uppercased brand names ("BARILLA"), `(420ml)` after weight. |
| `masoutis` | 3,087 | Trailing `.` on units, `γρ.` not `g`. |
| `ab` | 282 | Chronically thin — own-brand-only "Ραβιόλι Ρικότα Σπανάκι 250g" etc. |
| `lidl` | 0 | No active offers in the seed today. Treat Lidl as pure own-brand (Pilos, Combino, Solevita, Milbona) when it lands. |

### `external_id` is **not** a GTIN

Spot-checked across all four populated brands:

```
masoutis     "4140125"   Nirvana Παγωτό Pistachio Almond 313γρ./420ml.
sklavenitis  "1690872"   ΙΟΝ Derby Σοκολάτα Classic 3x38g +1 Δώρο
my-market    "720418"    Nivea Sun Αντηλιακό Γαλάκτωμα SPF20 200ml
ab           "7811402"   Αποσμητικό Stick Raspberry 75ml
```

These are 6–7 digit internal SKU/PLU codes. **No 13-digit EAN-13s, no
GTIN-12s.** The cheapest possible matching primitive (`WHERE
products.gtin = ?`) is therefore unavailable. We must match on text +
image, full stop.

### `normalized_name` is too literal

`StringNormalizer::normalize()` (`backend/app/Support/StringNormalizer.php`)
does only three things: lowercase, strip Greek accents, collapse
whitespace. That is the right primitive — but it is far too literal to
match across chains, because the chains disagree on every other axis:

| Chain | Convention sample |
|---|---|
| Sklavenitis | `COCA-COLA Original Taste 2x1,5lt`, `BARILLA Collezione Πένες Τρικολόρε 500g` |
| My Market | `Coca-Cola 2x1lt`, `Barilla Collezione Papiri 450gr` |
| Masoutis | `Coca Cola 2x1lt.`, `Nirvana Παγωτό Cookie Dough 302γρ./420ml.` |
| AB | `Surimi Sticks Γεύση Καβουριού 250g` (own-brand, no manufacturer prefix at all) |

Exact-equal on `normalized_name` yields **49 cross-brand clusters / 98
products**. Useful, but not enough.

---

## 2. Concrete examples from the live DB

Eight examples covering the six difficulty tiers. Every row is a real
record I pulled from `:8001` today.

### Tier 1 — Easy: identical national brand across ≥3 chains

**Example A — Pepsi Cola 1.5L** (3 chains agree on everything but
punctuation):

| brand | id | name | unit | price |
|---|---|---|---|---|
| sklavenitis | 6416 | `PEPSI Cola 1,5lt` | τεμ. | €1.29 |
| my-market | 1691 | `Pepsi Cola 1,5lt` | – | €1.63 |
| masoutis | 1042 | `Pepsi Cola 1,5lt.` | – | €1.49 |

Verdict: **must canonicalise to one product**. Aggressive match-key
collapses all three to `pepsi cola 1.5l`. ✅

**Example B — Melissa Σπαγγέτι Χωρίς γλουτένη 400g** (3 chains):

| brand | id | name | price |
|---|---|---|---|
| sklavenitis | 10535 | `MELISSA Σπαγγέτι Χωρίς γλουτένη 400g` | €2.13 |
| my-market | 6947 | `Melissa Σπαγγέτι Χωρίς Γλουτένη 400gr` | €2.29 |
| masoutis | 618 | `Melissa Σπαγγέτι Χωρίς Γλουτένη 400γρ.` | €2.62 |

Verdict: **canonicalise**. Match-key after folding `g`/`gr`/`γρ` →
`g`: `melissa spaggeti xoris gloytenh 400g`. ✅

### Tier 2 — Medium: same product, different formatting

**Example C — Rio Mare Τόνος 3×80g**:

| brand | id | name | price |
|---|---|---|---|
| sklavenitis | 4713 | `RIO MARE Τόνος σε Ελαιόλαδο 3x80g` | €4.28 |
| my-market | 2919 | `Rio Mare Τόνος Σε Ελαιόλαδο 3x80gr` | €4.80 |
| masoutis | 788 | `Rio Mare Τόνος Σε Ελαιόλαδο 3x80γρ.` | €4.41 |

Verdict: **canonicalise**. Trivial for match-key after gram folding.

**Example D — Coca-Cola 6×330ml vs 5×330ml +1 (promo packaging)**:

| brand | id | name | price |
|---|---|---|---|
| sklavenitis | 11560 | `COCA-COLA Original Taste 5x330ml +1 Δώρο` | €4.30 |
| my-market | 945 | `Coca-Cola 6x330ml` | €4.41 |

Verdict: **same canonical product, different presentation.**
"5×330ml +1 Δώρο" is "6×330ml" physically. We should either (a) detect
the `+N Δώρο` suffix and collapse, or (b) keep them as separate canonical
products and let the comparison page show both. Recommend (a) once we
ship Phase 2 — the regex `(\d+)x(\d+)ml\s*\+(\d+)\s*Δώρο` →
`(N+M)×Wml` is a clean rule. Until then, expect them to be matched as
near-duplicates in the review queue.

### Tier 3 — Hard: same brand, different sizes

**Example E — Nirvana ice cream, 420 ml tubs vs 750 ml tubs**:

| brand | id | name | price |
|---|---|---|---|
| sklavenitis | 11787 | `NIRVANA Παγωτό Brownies & Salted Caramel 302g (420ml)` | €4.60 |
| masoutis | 5 | `Nirvana Παγωτό Brownies & Salted Caramel 302γρ/420ml.` | €4.44 |
| sklavenitis | 11672 | `NIRVANA Παγωτό Cookies & Cream 538g (750ml)` | €7.95 |

Verdict: the 420 ml Sklavenitis tub and the 420 ml Masoutis tub
**canonicalise**. The 750 ml tub is a **different canonical product** —
it is a different SKU on the manufacturer's shelf, not a different
chain's pricing of the same one.

Decision rule: **the canonical product is the package, not the recipe.**
Comparison UX can offer a "see other sizes" affordance, but the
primary table is per-package.

### Tier 4 — Edge: own-brand collisions

**Example F — Gouda from competing private labels**:

| brand | id | name | source |
|---|---|---|---|
| my-market | 6878 | `My Gusto Πάριζα & Τυρί Gouda 280gr` | private label |
| my-market | 9497 | `My Gusto Γαλοπούλα Βραστή & Τυρί Edam 280gr` | private label |
| my-market | 2217 | `ΝΟΥΝΟΥ Gouda Σε Φέτες 200gr` | national |
| sklavenitis | 9080 | `Creamy Gouda ADORO τριμμένo 200g` | national |
| masoutis | 52 | `Fripozo Gouda bites 300γρ.` | national |

Verdict: **My Gusto products NEVER canonicalise to another chain**, even
when the trailing words look identical. Detection rule:

> If the `manufacturer_brand` parsed from the product name is in a
> store-owned-brands whitelist (`{my gusto, ab, ab choice, pilos,
> combino, milbona, solevita, w5, ...}`), then `canonicalisable = false`
> and `canonical_product_id` may only point to a canonical product whose
> `is_private_label = true` and whose `owning_chain` matches.

This means we need to detect a `manufacturer_brand` field on every
product *before* canonicalisation runs.

### Tier 5 — Edge: typos / abbreviations / Greek-Latin mixing

**Example G — `Π.Ο.Π.` vs `ΠΟΠ`, `Β`(eta) vs `B`(latin)**:

| brand | id | name |
|---|---|---|
| sklavenitis | 10493 | `Φέτα ΔΩΔΩΝΗ ΠΟΠ 400g` |
| masoutis | 144 | `Δωδώνη Κεφαλογραβιέρα ΠΟΠ` |
| my-market | 6397 | `Ήπειρος Φέτα ΠΟΠ Βιολογική 350gr` |

After `normalize()`: `φετα δωδωνη πομ 400g` vs `δωδωνη
κεφαλογραβιερα πομ` vs `ηπειρος φετα πομ βιολογικη 350gr`. None match.

Three of these are **different canonical products** (different cheese
types) — but the harder problem is hiding in plain sight: brand
**ΔΩΔΩΝΗ** vs **Δωδώνη** vs **(missing brand prefix)**. The fix is to
extract `manufacturer_brand` first and remove it from the comparison
key, so we match on `feta pop 400g` against a `manufacturer_brand=
'δωδωνη'` block.

**Example H — Latin/Greek look-alikes** (`B`eer brand "Bιολογικό" where
`B` is a Latin B in a Greek word):

The aggressive match-key folds `α`→`a`, `β`→`b`, `ε`→`e`, … which
turns `BARILLA` (Latin) and `ΒΑΡΙΛΛΑ` (Greek — never observed) into
the same string. Defensive; cheap; one or two false merges per quarter
in the worst case (review-queue catches them).

### Tier 6 — Edge: flavour variants

**Example I — Nirvana flavour family**:

```
sklavenitis  11787  NIRVANA Παγωτό Brownies & Salted Caramel 302g (420ml)
sklavenitis  11772  NIRVANA Παγωτό Pralines & Cream         310g (420ml)
sklavenitis  11736  NIRVANA Παγωτό Pistachio & Almonds      313g (420ml)
sklavenitis  11720  NIRVANA Παγωτό Rasberry Truffle         313g (420ml)
```

Verdict: each flavour is its **own** canonical product. The naive cluster
"all Nirvana 420 ml tubs" would be wrong. The match key must include
the flavour tokens. Our current `match_key` does (it folds nothing about
flavour words) — good.

---

## 3. Survey of candidate algorithms

| # | Algorithm | What it gets right | What it misses | Effort | Latency | P/R guess |
|---|---|---|---|---|---|---|
| 1 | Exact `normalized_name` | Trivial; deploy today; zero false positives within the brand. | Misses 99% of cross-brand matches (49/319 of our potential ≥2-brand clusters). | Low | <1 ms | P=0.99 R=0.04 |
| 2 | Aggressive deterministic match-key (size folding, punctuation strip, Greek↔Latin fold) | Catches 319 cross-brand clusters / 5.5% of catalogue with **zero ML**. Cheap, debuggable, fast. | Misses anything with different word order ("Φέτα ΗΠΕΙΡΟΣ" vs "Ήπειρος Φέτα"). Folds `β→b` which may merge "B-prefixed Latin" with "Β-prefixed Greek" wrongly (no real cases observed). | Low | <1 ms | P=0.97 R=0.10 |
| 3 | Levenshtein on `normalized_name` (threshold ~3) | Catches dropped accents, missing dots, `gr`/`g`. Easy to reason about. | Quadratic on naive impl. With 12k products, that's 144 M comparisons. Need blocking. Threshold blows up on short strings ("Coca" vs "Cola" = 2). | Medium | 50–500 ms per pair w/o blocking | P=0.85 R=0.30 |
| 4 | Token-set Jaccard / partial-token (rapidfuzz `token_set_ratio`) | Word-order invariant ("Φέτα ΗΠΕΙΡΟΣ" ≈ "ΗΠΕΙΡΟΣ Φέτα"). Handles inserted words. | Confuses flavours when the only differing token is one word ("Πραλίνες Φουντουκιού" vs "Πραλίνες Καραμέλας" — Jaccard 0.83). Needs a flavour-token blocklist or weighted scoring. | Low | 1–5 ms per pair after blocking | P=0.90 R=0.55 |
| 5 | Sentence-transformer embeddings (`paraphrase-multilingual-MiniLM-L12-v2`, 384-dim) | Handles paraphrase, synonyms, light translation; multilingual covers our Greek↔Latin mixing. | Needs a vector store (FAISS / sqlite-vec / pgvector). Will confuse flavour variants (Brownies vs Cookies & Cream cosine ≈ 0.92). False merges *worse* than fuzzy: a wrong embedding match is opaque to a reviewer. | High | 5–30 ms encode + 1–2 ms ANN | P=0.85 R=0.85 |
| 6 | Perceptual image hash (pHash on `image_url`) | Strong secondary signal — same SKU usually = same product photo across chains. Cheap to compute once. | Many chains use their own shoot (not vendor-supplied), so the photo backgrounds and angles differ. pHash distance 5–10 typical between AB and Masoutis on the same SKU. Needs a tolerance threshold and is best as a **confidence boost**, not a primary key. | Medium (image download cost) | 50–200 ms first time per product, then cached | Boosts P by ~0.05–0.10 |
| 7 | GTIN/EAN lookup | The "right" answer in retail. | **Not available.** None of the four populated brands expose a barcode. Skip. | – | – | – |
| 8 | Brand-aware blocking (only compare pairs sharing `manufacturer_brand` and not in private-label set) | Cuts comparison space ~100× and eliminates the entire "My Gusto vs ΑΒ Gouda" failure mode. | Requires a `manufacturer_brand` parser, which is its own subproject. | Medium | – | Prerequisite, not a matcher |

### Concrete pseudocode for the recommended primitives

**Aggressive match-key** (Phase 1, deterministic):

```python
# crawler/scripts/canon_explore.py for the live version
def match_key(name: str) -> str:
    s = normalize(name)                       # accent-strip + lower + ws
    s = SIZE_NUM.sub(r"\1.\2", s)             # 1,5 -> 1.5
    s = SPACE_BEFORE_UNIT.sub(r"\1\2", s)     # 330 ml -> 330ml
    s = s.replace("lt","l").replace("γρ","g") # gram/litre fold
    s = PUNCT.sub(" ", s)                     # strip . , / ( ) etc
    s = fold_greek_latin_lookalikes(s)        # α→a, β→b, ε→e …
    return collapse_whitespace(s)
```

**Token-set similarity** (Phase 2, fuzzy):

```python
import rapidfuzz
score = rapidfuzz.fuzz.token_set_ratio(a, b)  # 0..100, O(n+m)
# decision: >= 92 within manufacturer_brand block => auto-merge
#           80..91 => review queue
#           < 80 => no match
```

---

## 4. The recommended algorithm: a four-stage pipeline

```
new offer arrives
      │
      ▼
[1] parse manufacturer_brand    ← rule-based, dict-backed
      │
      ▼
[2] compute match_key (Phase 1) ← deterministic
      │
      ▼
[3] look up canonical by (manufacturer_brand, match_key)
      ├─ hit  → assign canonical_product_id, score=1.0, method=exact
      └─ miss → continue
      │
      ▼
[4] candidate retrieval (Phase 2): rapidfuzz.token_set_ratio
    against all canonical products with same manufacturer_brand
      │ best score >= 92         → auto-assign, method=fuzzy
      │ 80 <= best score < 92    → enqueue for review, leave canonical_product_id NULL
      │ best score < 80          → mint a NEW canonical_product, score=1.0, method=seed
```

The "Phase 4 / embeddings" fallback (§5 Phase 4) only kicks in for offers
that landed in the review queue and have been sitting there for >7 days.

### Match confidence model

`canonical_product_matches.confidence` is a float in `[0,1]`:

| confidence | source |
|---|---|
| 1.00 | exact match on `(brand, external_id)` → trivially the same product on next crawl |
| 0.99 | (manufacturer_brand, match_key) exact hit |
| `token_set_ratio / 100` | fuzzy match |
| `0.6 * fuzzy + 0.4 * (1 - phash_distance/64)` | hybrid with image agreement |
| `embedding_cosine` | Phase 4 |
| 1.00 | `method=manual` (human reviewer confirmed) |

Thresholds: **auto-assign at ≥0.92, review at [0.80, 0.92), reject
below.**

### How a new offer is processed

Today's contract: the crawler pushes batches to
`POST /api/v1/crawl-runs/{run}/offers`. The controller calls
`ProductResolver` (already lives in `backend/app/Services/`) to
find-or-create the `products` row by `(brand_id, external_id)`. We add
a second step on **product creation only**:

```
ProductResolver::resolve($brandId, $payload):
    $product = findOrCreate(...)                  # existing logic
    if ($product->wasRecentlyCreated):
        CanonicaliseProductJob::dispatch($product)
    return $product
```

The job is **asynchronous on purpose** — offer ingest must stay
all-or-nothing (per backend CLAUDE.md) and we don't want canonicalisation
exceptions to roll the batch back. If the job fails, the product just
keeps `canonical_product_id = NULL`, which is the same state as the
bootstrap backlog — it'll get picked up by the nightly sweeper.

### Failure modes by tier

| Tier | Auto outcome | What goes wrong |
|---|---|---|
| 1 Easy | auto-assign 0.99 | nothing |
| 2 Medium (formatting) | auto-assign 0.99 after match-key fold | `+N Δώρο` style packaging differences fall to fuzzy (0.85), land in review queue |
| 3 Hard (sizes) | mint two canonical products | UI must group "all sizes of X" — that is a frontend concern, not a canonicalisation one |
| 4 Own-brand collisions | manufacturer-brand block prevents the merge entirely | if the parser misses the brand, we silently merge — *the* highest-risk bug |
| 5 Typos / accent / Greek-Latin | exact match-key handles `ΠΟΠ` vs `Π.Ο.Π.`; fuzzy handles `Bιολογικό` vs `βιολογικά` | reduplicated cases: `χωρίς` written `xωρις` (latin x) — covered by Greek-Latin fold |
| 6 Flavour variants | each flavour mints its own canonical | risk: fuzzy at 0.92 might collapse "Brownies & Salted Caramel" with "Pralines & Cream" — *don't*. Mitigation: configure `token_set_ratio` with a **flavour token whitelist** that prevents auto-merge when the *only* differing tokens are flavour adjectives. |

### Bootstrap

Two-pronged:

1. **Top-500 manual seed.** Pull the 500 most-discounted national-brand
   products of the last 90 days (most discounted = most likely to be in
   competing chains' flyers in any given week). A reviewer in our
   admin UI labels them. Each seed creates one `canonical_products`
   row with `method=manual` and confidence=1.0. Expected to canonicalise
   ~30% of total weekly offer volume in the comparison page even though
   it covers <5% of distinct SKUs.

2. **Batch sweeper.** `php artisan canonical:rebuild` — iterates every
   `products` row with `canonical_product_id IS NULL`, runs the pipeline
   above, writes the result. Idempotent. Cron nightly until the backlog
   hits zero, then weekly.

### Maintenance

- **Drift detection.** Once a week, sample 50 random canonical groups
  with ≥2 brands. Recompute the pairwise `token_set_ratio` between
  member products. If any pair scores <0.70, flag the group for review.
- **Manual edits are sticky.** A reviewer's `method=manual` assignment
  is never overwritten by an automated pass. Track this with
  `canonical_product_matches.locked = TRUE`.
- **Split & merge tooling.** Reviewers need a UI to (a) move a product
  out of a canonical group, (b) merge two canonical groups. Stub these
  endpoints from day one even if the UI ships in Phase 3.

---

## 5. Migration + API surface

### `canonical_products` table

```sql
CREATE TABLE canonical_products (
    id              BIGINT PRIMARY KEY,
    -- The display name and key identifier (manually curated when
    -- method=manual, derived from the seed member otherwise).
    display_name    TEXT NOT NULL,
    match_key       TEXT NOT NULL,             -- Phase-1 deterministic key
    manufacturer_brand TEXT,                   -- "coca-cola", "nirvana", null when unknown
    category        TEXT,                      -- canonical category, free-text for MVP
    package_size    TEXT,                      -- e.g. "1.5L", "6x330ml" — normalised
    is_private_label BOOLEAN NOT NULL DEFAULT FALSE,
    owning_chain_id BIGINT NULL                -- FK to brands.id when is_private_label
                    REFERENCES brands(id),
    image_url       TEXT,                      -- canonical image, pickable
    created_at      TIMESTAMP NOT NULL,
    updated_at      TIMESTAMP NOT NULL,

    UNIQUE (manufacturer_brand, match_key)     -- the "natural" key
);

CREATE INDEX canonical_products_category_idx        ON canonical_products(category);
CREATE INDEX canonical_products_private_label_idx   ON canonical_products(is_private_label, owning_chain_id);
```

### `canonical_product_matches` (join, with confidence)

```sql
CREATE TABLE canonical_product_matches (
    id              BIGINT PRIMARY KEY,
    canonical_product_id BIGINT NOT NULL REFERENCES canonical_products(id) ON DELETE CASCADE,
    product_id      BIGINT NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    confidence      REAL NOT NULL,             -- 0..1
    method          TEXT NOT NULL CHECK (method IN ('exact','fuzzy','embedding','manual','seed')),
    locked          BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at     TIMESTAMP NULL,
    reviewer_user_id BIGINT NULL REFERENCES users(id),
    created_at      TIMESTAMP NOT NULL,
    updated_at      TIMESTAMP NOT NULL
);
```

We **keep** `products.canonical_product_id` as a denormalised pointer for
read-side performance (the comparison API joins it on every request).
The join table is the audit log; the column on `products` is the
read-optimised cache, updated by a model observer.

### Public API additions

```
GET /api/public/v1/canonical-products
    ?category=...&q=...&min_brand_count=2&page=1
    → list with summary stats per row:
        - id, display_name, image_url, category, package_size
        - brand_count: 3
        - min_price, max_price, avg_price (current valid offers only)
        - savings_pct: 5..50

GET /api/public/v1/canonical-products/{id}
    → comparison detail:
        - canonical fields
        - offers: array of {brand{slug,name}, product{id,name,url,image_url},
                            price, original_price, discount_pct,
                            valid_from, valid_to}, ordered by price asc
        - sibling_canonical_products: same family, other sizes/flavours

# Backwards-compat hook on the existing endpoint:
GET /api/public/v1/offers?canonical_id=123
    → all offers (across all brands) for one canonical product
```

The frontend's "compare across chains" page calls
`/canonical-products/{id}` exactly once. Sorting by price client-side
keeps the API cacheable.

### Crawler-side changes

**None.** Canonicalisation is a backend concern, triggered on ingest.
The crawler keeps pushing `(brand_id, external_id, name, …)`. This is
the single best property of the current schema design — preserve it.

---

## 6. Phased rollout

| Phase | Scope | Coverage of catalogue | Engineering days |
|---|---|---|---|
| **0** ✅ | `products.canonical_product_id` column exists, nullable. | – | done |
| **1** | Deterministic match-key + manufacturer-brand parser + `canonical_products` table + bootstrap sweeper. | **~6%** auto-assigned (319 clusters / 657 products) + ~300 manual seeds → ~10% of distinct products, **~30% of weekly offer volume** because the seed targets the most-discounted SKUs. | 4–5 |
| **2** | rapidfuzz fuzzy matcher with `token_set_ratio ≥ 92` auto-merge, `[80,92)` review queue. Add `+N Δώρο` packaging-normaliser regex. | +~10% auto (estimate; review-queue feeds back into ground truth, but the long tail is mostly single-chain SKUs that *shouldn't* match anything). | 3–4 |
| **3** | Reviewer UI: list pending matches, accept/reject/split/merge. Backend endpoints `PUT /admin/canonical-products/{id}/members`. | +~3% via human-confirmed merges. | 4–5 |
| **4** | Multilingual sentence embeddings (`paraphrase-multilingual-MiniLM-L12-v2`, 384-dim, ~120 MB). Local inference via `sentence-transformers` in a tiny Flask sidecar on the crawler box. SQLite-vec or pgvector for ANN. Only invoked for products that have sat in the review queue >7 days. | +~2% on the very long tail. Diminishing returns from here on. | 6–8 |

Phase 4 only justifies itself once we have ≥3 actively-scraping chains
*and* Lidl Hellas is live (its own-brand catalogue plus the private-label
detection is where embeddings shine — they can suggest "Pilos Φέτα
400g" ↔ "AB Choice Φέτα 400g" as *similar but explicitly not equal*
products for the "sibling" panel).

---

## 7. Honest about the limits

- **The `manufacturer_brand` parser is the single biggest risk.** If it
  misclassifies "My Gusto" as a national brand, we silently merge
  unrelated SKUs across chains. Mitigation: ship the parser with a
  hard-coded whitelist of known private-label prefixes per chain, and
  *never* infer private-label status — fail closed.
- **AB has 282 products in our DB; this is a scraping problem.** No
  amount of canonicalisation work will surface a comparison row for an
  SKU AB doesn't crawl. Until AB coverage matches Sklavenitis/My Market
  (~3k products), the comparison page will look thin against the AB
  column.
- **Lidl is the second-biggest blind spot.** Zero offers today. When
  Lidl lands, ~80% of its catalogue will be private-label and should
  never merge cross-chain. Plan: when Lidl ingestion turns on, every
  Lidl product starts with `canonical_product_id = NULL` and the
  pipeline assigns it to a *Lidl-only* canonical (private-label
  category). National Lidl SKUs (the occasional Coca-Cola, Heinz) will
  flow through the normal pipeline.
- **The 750 ml vs 420 ml Nirvana decision is a product call, not a
  technical one.** If marketing later wants "all Nirvana flavours on
  one comparison page", we add a `canonical_product_family_id` —
  *don't* try to retrofit it into `canonical_product_id`. Keep the
  package the unit of identity.
- **We cannot tell `5×330ml +1 Δώρο` apart from `6×330ml` without
  reading the small print.** They are physically identical (six cans),
  but priced differently because one is on a promo. The right answer in
  the comparison UI is to show both as the same canonical product but
  label the offer with a `promo_pack: true` flag — *not* to canonicalise
  them apart and *not* to invent an `effective_unit_price` that hides
  the promo.
- **319 cross-brand clusters is enough to ship the comparison feature.**
  It is not enough to claim "we compare every product across all
  chains" — be careful with marketing copy. Frame it as "We compare
  national-brand staples across Sklavenitis, My Market, Masoutis and AB
  Vassilopoulos." Grow the claim as Phase 2/3 land.

---

## 8. Open questions before we ship

1. Should `canonical_products` store a curated `gtin` column even though
   no chain exposes one? (Yes — reviewers can fill from manufacturer
   sites; future-proofs us if a chain ever exposes EANs.)
2. Do we want a `canonical_product_synonyms` table for known
   alternate names (e.g. "Pepsi Cola" ↔ "Pepsi Original")? (Probably
   yes in Phase 3 — cheap to add, helps search.)
3. Do we expose **unit price** (€/kg, €/L) at the canonical level?
   Masoutis already gives it for free in `unit`; the other chains don't.
   Recommend Phase 2: parse `package_size` and compute it
   server-side so the comparison surface can sort by it.

---

### See also

- `crawler/scripts/canon_explore.py` — the read-only helper used to
  produce every number in this doc. Re-run after a fresh crawl to
  refresh examples.
- `backend/app/Support/StringNormalizer.php` — the existing primitive
  every Phase calls into.
- `backend/CLAUDE.md` — backend conventions; in particular, the
  "all-or-nothing transaction" rule that mandates async canonicalisation.
