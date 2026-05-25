<?php

namespace Tests\Feature\Api\Public\V1;

class BrandOffersTest extends PublicApiTestCase
{
    public function test_brand_scoped_sugar_route_works(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $lidl = $this->makeBrand(['slug' => 'lidl', 'website_url' => 'https://lidl']);
        $p1 = $this->makeProduct($ab, ['name' => 'a', 'normalized_name' => 'a']);
        $p2 = $this->makeProduct($lidl, ['name' => 'b', 'normalized_name' => 'b']);
        $this->makeOffer($p1);
        $this->makeOffer($p2);

        $response = $this->getJson('/api/public/v1/brands/ab/offers')->assertOk();

        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame('ab', $response->json('data.0.brand.slug'));
    }

    public function test_unknown_brand_slug_404s(): void
    {
        $this->getJson('/api/public/v1/brands/no-such-brand/offers')->assertNotFound();
    }

    public function test_brand_scope_combines_with_other_filters(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $p1 = $this->makeProduct($ab, ['name' => 'a', 'normalized_name' => 'a']);
        $p2 = $this->makeProduct($ab, ['name' => 'b', 'normalized_name' => 'b']);
        $this->makeOffer($p1, ['discount_pct' => 10]);
        $this->makeOffer($p2, ['discount_pct' => 40]);

        $response = $this->getJson('/api/public/v1/brands/ab/offers?min_discount=25')->assertOk();
        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame(40, $response->json('data.0.discount_pct'));
    }
}
