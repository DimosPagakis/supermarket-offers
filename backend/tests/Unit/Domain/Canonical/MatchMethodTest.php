<?php

namespace Tests\Unit\Domain\Canonical;

use App\Domain\Canonical\MatchMethod;
use PHPUnit\Framework\TestCase;

/**
 * Pin the wire-stable string values of MatchMethod. Renaming a case
 * (e.g. `Rule` -> `Rules`) silently keeps the enum compiling but
 * breaks the canonicaliser's `match_method` payload contract.
 */
class MatchMethodTest extends TestCase
{
    public function test_wire_values_are_stable(): void
    {
        $this->assertSame('rule', MatchMethod::Rule->value);
        $this->assertSame('embedding', MatchMethod::Embedding->value);
        $this->assertSame('llm', MatchMethod::Llm->value);
        $this->assertSame('manual', MatchMethod::Manual->value);
    }

    public function test_cases_cover_the_full_set(): void
    {
        $values = array_map(fn (MatchMethod $m) => $m->value, MatchMethod::cases());
        sort($values);
        $this->assertSame(['embedding', 'llm', 'manual', 'rule'], $values);
    }
}
