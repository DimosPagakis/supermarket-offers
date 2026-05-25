<?php

namespace Tests\Feature\Api\Public\V1;

use App\Support\StringNormalizer;

class SearchTest extends PublicApiTestCase
{
    public function test_search_is_alias_of_offers_q(): void
    {
        $brand = $this->makeBrand();
        $feta = $this->makeProduct($brand, [
            'name' => 'Φέτα ΠΟΠ 400γρ',
            'normalized_name' => StringNormalizer::normalize('Φέτα ΠΟΠ 400γρ'),
        ]);
        $other = $this->makeProduct($brand, [
            'name' => 'Ντομάτες',
            'normalized_name' => StringNormalizer::normalize('Ντομάτες'),
        ]);
        $this->makeOffer($feta);
        $this->makeOffer($other);

        $r = $this->getJson('/api/public/v1/search?q='.urlencode('φετα'))->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('Φέτα ΠΟΠ 400γρ', $r->json('data.0.product.name'));
    }

    public function test_search_requires_q(): void
    {
        $this->getJson('/api/public/v1/search')
            ->assertStatus(422)
            ->assertJsonValidationErrors(['q']);
    }
}
