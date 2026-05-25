<?php

namespace App\Services;

use App\Support\FamilyBrands;
use App\Support\StringNormalizer;

/**
 * Derive family-browse features from a raw product name.
 *
 * This is a deliberate PHP mirror of
 * `crawler/scraper/canonical/extractors.py` — the same regexes and
 * brand whitelist live on both sides because:
 *
 *  - the crawler runs the heavy canonical pipeline once per ingest
 *    against the full catalogue;
 *  - the backend needs to re-derive features on every new product so
 *    `(manufacturer_brand, category_normalised, size_value, size_unit)`
 *    is queryable in milliseconds at request time.
 *
 * Keep the two in lockstep. When the crawler list grows a brand, port
 * it here too (see {@see FamilyBrands}). The unit test
 * `Tests\Unit\Services\VariantDescriberTest` pins a handful of real
 * Greek product names + their expected descriptors.
 *
 * Output shape (see {@see VariantDescriber::extract()}):
 *
 *   [
 *     'manufacturer_brand' => 'axe' | null,
 *     'category_normalised' => 'αποσμητικα σωματος' | null,
 *     'size_value' => 150.0 | null,
 *     'size_unit' => 'ml' | null,
 *     'pack_count' => 1,
 *     'variant_descriptor' => 'africa' | null,
 *   ]
 *
 * NULL `manufacturer_brand` is the safe default for own-brand SKUs and
 * unrecognised names — they do not enter any family.
 */
class VariantDescriber
{
    /**
     * Unit aliases (alias => canonical). Order matters: longer aliases
     * win in the alternation, otherwise "lt" gets gobbled by "l".
     * Matches `_UNIT_MAP` in extractors.py.
     *
     * @var array<int, array{0: string, 1: string}>
     */
    private const UNIT_MAP = [
        ['γραμμαρια', 'g'], ['γραμμάρια', 'g'],
        ['γρ.', 'g'], ['γρ', 'g'], ['gr.', 'g'], ['gr', 'g'], ['g.', 'g'], ['g', 'g'],
        ['κιλά', 'kg'], ['κιλα', 'kg'], ['κιλό', 'kg'], ['κιλο', 'kg'],
        ['κιλ.', 'kg'], ['κιλ', 'kg'], ['kg.', 'kg'], ['kg', 'kg'],
        ['ml.', 'ml'], ['ml', 'ml'], ['μλ', 'ml'],
        ['λίτρα', 'l'], ['λιτρα', 'l'], ['λτ.', 'l'], ['λτ', 'l'],
        ['lt.', 'l'], ['lt', 'l'], ['l.', 'l'], ['l', 'l'],
        ['τεμάχια', 'τεμ'], ['τεμαχια', 'τεμ'], ['τεμάχιο', 'τεμ'], ['τεμαχιο', 'τεμ'],
        ['τεμ.', 'τεμ'], ['τεμ', 'τεμ'], ['τμχ.', 'τεμ'], ['τμχ', 'τεμ'],
        ['pcs.', 'τεμ'], ['pcs', 'τεμ'],
    ];

    private const VOLUME_UNITS = ['ml', 'l'];

    /**
     * Stopwords dropped from the variant descriptor — packaging chatter,
     * not product identity. Mirror of `_STOPWORDS` in extractors.py
     * (Greek tokens stored already accent-folded).
     *
     * @var array<int, string>
     */
    private const STOPWORDS = [
        'the', 'of', 'and', 'with', 'for', 'in', 'on', 'from', 'to', 'at',
        'pack', 'value', 'new',
        'kai', 'me', 'se', 'sto', 'sthn', 'stoys', 'stis', 'toy', 'ths', 'ton',
        'twn', 'h', 'o', 'ta', 'oi', 'oti', 'ena', 'mia',
        'tem', 'temaxio', 'temaxia', 'tmx',
        'fyllo', 'fylla', 'rolla', 'rola', 'merides',
    ];

    /**
     * Greek lowercase → Latin look-alike fold. Allows tokens like
     * "Φουντουκιού" and "ΦΟΥΝΤΟΥΚΙΟΥ" to reduce to the same ASCII
     * comparable form.
     *
     * @var array<string, string>
     */
    private const GREEK_TO_LATIN = [
        'α' => 'a', 'β' => 'b', 'γ' => 'g', 'δ' => 'd', 'ε' => 'e', 'ζ' => 'z', 'η' => 'h',
        'θ' => 'th', 'ι' => 'i', 'κ' => 'k', 'λ' => 'l', 'μ' => 'm', 'ν' => 'n', 'ξ' => 'x',
        'ο' => 'o', 'π' => 'p', 'ρ' => 'r', 'σ' => 's', 'τ' => 't', 'υ' => 'y', 'φ' => 'f',
        'χ' => 'x', 'ψ' => 'ps', 'ω' => 'o', 'ς' => 's',
    ];

    /**
     * Cached alias lookups built once per process lifetime — both are
     * pure functions of compile-time constants in {@see FamilyBrands}.
     *
     * @var array<int, array{0: string, 1: string}>|null
     */
    private static ?array $cachedBrandAliases = null;

    /** @var array<int, array{0: string, 1: string}>|null */
    private static ?array $cachedPrivateAliases = null;

    /**
     * Derive every family feature from a raw product name + optional
     * category. `category` arrives verbatim from the crawl payload; we
     * just lowercase + accent-strip it for the indexed comparison
     * column.
     *
     * @return array{manufacturer_brand: string|null, category_normalised: string|null, size_value: float|null, size_unit: string|null, pack_count: int, variant_descriptor: string|null}
     */
    public function extract(string $name, ?string $category = null): array
    {
        $manufacturer = $this->manufacturerBrand($name);
        $size = $this->canonicalSize($name);
        $pack = $this->packCount($name);
        $variant = $this->variantDescriptor($name, $manufacturer);
        $categoryNorm = $category !== null && $category !== ''
            ? StringNormalizer::normalize($category)
            : null;

        return [
            'manufacturer_brand' => $manufacturer,
            'category_normalised' => $categoryNorm,
            'size_value' => $size === null ? null : $size[0],
            'size_unit' => $size === null ? null : $size[1],
            'pack_count' => $pack,
            'variant_descriptor' => $variant,
        ];
    }

    /**
     * Returns the manufacturer brand normalised to its canonical key
     * (e.g. "axe", "coca-cola"), or null when the name leads with a
     * private-label alias or no known brand at all.
     *
     * Strategy mirrors `extract_manufacturer()` in extractors.py:
     * private-label whitelist wins first (fail-closed for own-brand),
     * then the national-brand list with longest-alias-first matching.
     */
    public function manufacturerBrand(string $name): ?string
    {
        if ($name === '') {
            return null;
        }
        $folded = StringNormalizer::normalize($name);

        foreach (self::privateAliases() as [$alias, $_]) {
            if ($this->aliasMatches($folded, $alias)) {
                return null;
            }
        }

        foreach (self::brandAliases() as [$alias, $canonical]) {
            if ($this->aliasMatches($folded, $alias)) {
                return $canonical;
            }
        }

        return null;
    }

    /**
     * Extract `(value, unit_canonical)` from a name. Returns null if no
     * size token is detected. Mirrors `canonical_size()` in
     * extractors.py: volume wins over weight when both appear.
     *
     * @return array{0: float, 1: string}|null
     */
    public function canonicalSize(string $name): ?array
    {
        if ($name === '') {
            return null;
        }
        $folded = StringNormalizer::normalize($name);

        $unitAlt = $this->unitAlternation();
        $pattern = '/(\d+(?:[.,]\d+)?)\s*(?:('.$unitAlt.')(?![a-zα-ω]))/iu';

        if (preg_match_all($pattern, $folded, $m, PREG_OFFSET_CAPTURE) === false) {
            return null;
        }
        if (! isset($m[1]) || count($m[1]) === 0) {
            return null;
        }

        $matches = [];
        foreach ($m[1] as $i => $valueCapture) {
            $rawValue = (string) $valueCapture[0];
            $value = (float) str_replace(',', '.', $rawValue);
            $unit = $this->normaliseUnit(mb_strtolower((string) $m[2][$i][0], 'UTF-8'));
            $matches[] = [$value, $unit, (int) $valueCapture[1]];
        }

        // 1) Volume beats weight.
        $vol = array_values(array_filter(
            $matches,
            fn (array $row) => in_array($row[1], self::VOLUME_UNITS, true),
        ));
        if ($vol !== []) {
            $last = end($vol);

            return [$last[0], $last[1]];
        }

        // 2) Otherwise last occurrence wins.
        $last = end($matches);

        return [$last[0], $last[1]];
    }

    /**
     * Extract the multi-pack count. Returns 1 when no pack pattern
     * matches. "+N Δώρο" promo packaging is folded into the base count
     * — see `pack_count()` in extractors.py for examples.
     */
    public function packCount(string $name): int
    {
        if ($name === '') {
            return 1;
        }
        $folded = StringNormalizer::normalize($name);

        $base = 1;
        if (preg_match('/(?<![a-zα-ω0-9])(\d{1,2})\s*[xχ×]\s*(?=\d)/iu', $folded, $packMatch)) {
            $n = (int) $packMatch[1];
            if ($n >= 1 && $n <= 48) {
                $base = $n;
            }
        }

        if (preg_match('/\+\s*(\d{1,2})\s*(?:δωρο|free|gift)/iu', $folded, $plusMatch)) {
            $extra = (int) $plusMatch[1];
            if ($extra >= 1 && $extra <= 12) {
                $base += $extra;
            }
        }

        return $base;
    }

    /**
     * Tokens left after stripping the brand, size, pack and stopwords.
     * Returns a deterministic hyphen-joined slug ("africa" or
     * "africa-marine") — same ordering rule as the crawler's
     * `_slug()` helper so the descriptor is stable across runs.
     *
     * Returns null when nothing distinguishing is left (e.g. the
     * product name is just "Axe Σπρέι 150ml" — the family-browse
     * detail page renders these under the "—" descriptor bucket).
     */
    public function variantDescriptor(string $name, ?string $manufacturer): ?string
    {
        if ($name === '') {
            return null;
        }
        $folded = StringNormalizer::normalize($name);
        $folded = $this->stripBrand($folded, $manufacturer);
        $folded = $this->stripSizeAndPack($folded);

        // Greek → Latin fold so tokens are comparable across scripts.
        $ascii = strtr($folded, self::GREEK_TO_LATIN);

        $rawTokens = preg_split('/[^a-zα-ω0-9]+/iu', $ascii) ?: [];
        $tokens = [];
        $seen = [];
        foreach ($rawTokens as $token) {
            $token = (string) $token;
            if ($token === '' || mb_strlen($token) < 2) {
                continue;
            }
            if (ctype_digit($token)) {
                continue;
            }
            if (in_array($token, self::STOPWORDS, true)) {
                continue;
            }
            if (isset($seen[$token])) {
                continue;
            }
            $seen[$token] = true;
            $tokens[] = $token;
        }

        if ($tokens === []) {
            return null;
        }

        sort($tokens, SORT_STRING);
        $head = array_slice($tokens, 0, 4);

        return implode('-', $head);
    }

    // -----------------------------------------------------------------
    // Internals
    // -----------------------------------------------------------------

    /**
     * Does `$alias` appear as a leading token of the folded name? The
     * matcher accepts at most one preceding token — same rule as
     * `_alias_matches()` in extractors.py — to avoid "comfort"
     * matching deep inside "OB Pro Comfort".
     */
    private function aliasMatches(string $folded, string $alias): bool
    {
        if ($alias === '') {
            return false;
        }
        $pattern = '/(?:^|[\s\-\/.,(\[])'
            .preg_quote($alias, '/')
            .'(?=$|[\s\-\/.,)\]])/u';

        if (preg_match($pattern, $folded, $m, PREG_OFFSET_CAPTURE) !== 1) {
            return false;
        }
        $offset = $m[0][1];
        $head = mb_substr($folded, 0, $offset + 1, 'UTF-8');
        $head = trim($head);

        return $head === '' || count(preg_split('/\s+/u', $head) ?: []) <= 1;
    }

    private function stripBrand(string $folded, ?string $manufacturer): string
    {
        if ($manufacturer === null) {
            return $folded;
        }
        $out = $folded;
        foreach (self::brandAliases() as [$alias, $canonical]) {
            if ($canonical !== $manufacturer) {
                continue;
            }
            $pattern = '/(?:^|(?<=[\s\-\/.,(\[]))'
                .preg_quote($alias, '/')
                .'(?=$|[\s\-\/.,)\]])/u';
            $out = (string) preg_replace($pattern, ' ', $out);
        }

        return $out;
    }

    private function stripSizeAndPack(string $folded): string
    {
        $out = $folded;
        // Strip pack patterns first ("2x", "6×") so the trailing digits
        // don't leak into the size regex's mouth.
        $out = (string) preg_replace('/(?<![a-zα-ω0-9])\d{1,2}\s*[xχ×]\s*(?=\d)/iu', ' ', $out);
        $out = (string) preg_replace('/\b\d{1,2}\s*[xχ×]\b/iu', ' ', $out);

        $unitAlt = $this->unitAlternation();
        $out = (string) preg_replace('/\d+(?:[.,]\d+)?\s*(?:'.$unitAlt.')(?![a-zα-ω])/iu', ' ', $out);
        $out = (string) preg_replace('/\+\s*\d{1,2}\s*(?:δωρο|free|gift)/iu', ' ', $out);
        $out = (string) preg_replace('/\b\d+(?:[.,]\d+)?\b/iu', ' ', $out);
        $out = (string) preg_replace('/\bx\b/iu', ' ', $out);

        return $out;
    }

    private function normaliseUnit(string $raw): string
    {
        foreach (self::UNIT_MAP as [$alias, $canonical]) {
            if (mb_strtolower($alias, 'UTF-8') === $raw) {
                return $canonical;
            }
        }

        return $raw;
    }

    /**
     * Alternation of unit aliases, longest first, escaped for use
     * inside a non-capturing group. Cached on first build.
     */
    private function unitAlternation(): string
    {
        static $cached = null;
        if ($cached !== null) {
            return $cached;
        }
        $aliases = array_map(fn (array $pair) => $pair[0], self::UNIT_MAP);
        // Sort by length desc so "lt." wins over "l".
        usort($aliases, fn (string $a, string $b) => mb_strlen($b, 'UTF-8') <=> mb_strlen($a, 'UTF-8'));
        $aliases = array_unique($aliases);
        $escaped = array_map(fn (string $a) => preg_quote($a, '/'), $aliases);

        return $cached = implode('|', $escaped);
    }

    /**
     * @return array<int, array{0: string, 1: string}>
     */
    private static function brandAliases(): array
    {
        return self::$cachedBrandAliases ??= FamilyBrands::allAliases();
    }

    /**
     * @return array<int, array{0: string, 1: string}>
     */
    private static function privateAliases(): array
    {
        return self::$cachedPrivateAliases ??= FamilyBrands::privateLabelAliases();
    }
}
