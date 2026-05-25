<?php

namespace App\Domain\Canonical;

/**
 * How a product was assigned to its canonical group.
 *
 * The values are wire-stable — they appear verbatim in the
 * canonicaliser's `match_method` payload field and are persisted as
 * strings on `products.canonical_match_method`. Anything that adds a
 * new method must update this enum first; the FormRequest validation
 * derives its allow-list from the enum so a typo can't slip through.
 *
 * Ordered roughly by historical precedence (rule-based shipped first,
 * embedding-based came next, LLM is the newest automated tier, manual
 * is the human-reviewed gold standard).
 */
enum MatchMethod: string
{
    case Rule = 'rule';
    case Embedding = 'embedding';
    case Llm = 'llm';
    case Manual = 'manual';
}
