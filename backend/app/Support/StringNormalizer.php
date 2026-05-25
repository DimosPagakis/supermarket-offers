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
}
