<?php

namespace App\Support;

class StringNormalizer
{
    /**
     * Normalize a product name for fuzzy matching.
     *
     * - lowercase
     * - strip Greek accents/diacritics
     * - collapse whitespace
     */
    public static function normalize(string $name): string
    {
        $name = mb_strtolower(trim($name), 'UTF-8');

        // Strip Greek accents/diacritics by transliterating combining marks away.
        if (class_exists(\Transliterator::class)) {
            $tr = \Transliterator::create('NFD; [:Nonspacing Mark:] Remove; NFC');
            if ($tr !== null) {
                $name = $tr->transliterate($name) ?: $name;
            }
        } else {
            // Fallback: manual map of accented Greek vowels to bare forms.
            $name = strtr($name, [
                'ά' => 'α', 'έ' => 'ε', 'ή' => 'η', 'ί' => 'ι',
                'ό' => 'ο', 'ύ' => 'υ', 'ώ' => 'ω', 'ϊ' => 'ι',
                'ϋ' => 'υ', 'ΐ' => 'ι', 'ΰ' => 'υ',
            ]);
        }

        // Collapse all whitespace runs to single spaces.
        $name = preg_replace('/\s+/u', ' ', $name) ?? $name;

        return trim($name);
    }

    /**
     * Enumerate case variants of a Greek-aware string so case-insensitive
     * comparisons survive SQLite's ASCII-only LOWER().
     *
     * Returns the original, lowercase, uppercase and title-case forms
     * with duplicates removed. Callers use the result with `whereIn` to
     * match a column value against any casing the caller might supply.
     * Categories are a curated set (~tens of values), so the cost of a
     * 1–4 element IN-list is negligible.
     *
     * @return array<int, string>
     */
    public static function caseVariants(string $value): array
    {
        return array_values(array_unique([
            $value,
            mb_strtolower($value, 'UTF-8'),
            mb_strtoupper($value, 'UTF-8'),
            mb_convert_case($value, MB_CASE_TITLE, 'UTF-8'),
        ]));
    }
}
