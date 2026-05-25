<?php

namespace Tests\Feature\Api\Public\V1;

use App\Models\Brand;
use Illuminate\Support\Carbon;

class OffersIndexTest extends PublicApiTestCase
{
    public function test_happy_path_returns_paginated_envelope(): void
    {
        $brand = $this->makeBrand();
        for ($i = 0; $i < 3; $i++) {
            $p = $this->makeProduct($brand, ['name' => "Product {$i}", 'normalized_name' => "product {$i}"]);
            $this->makeOffer($p);
        }

        $response = $this->getJson('/api/public/v1/offers')->assertOk();

        $response->assertJsonStructure([
            'data' => [
                ['id', 'price', 'original_price', 'discount_pct', 'currency', 'valid_from', 'valid_to', 'scraped_at', 'product' => ['id', 'name'], 'brand' => ['slug']],
            ],
            'meta' => ['current_page', 'per_page', 'total', 'last_page'],
            'links' => ['first', 'last', 'next', 'prev', 'self'],
        ]);
        $this->assertSame(3, $response->json('meta.total'));
    }

    public function test_brand_filter_csv(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab', 'name' => 'AB']);
        $lidl = $this->makeBrand(['slug' => 'lidl', 'name' => 'Lidl', 'website_url' => 'https://lidl']);
        $mm = $this->makeBrand(['slug' => 'mm', 'name' => 'MM', 'website_url' => 'https://mm']);

        foreach ([$ab, $lidl, $mm] as $b) {
            $p = $this->makeProduct($b, ['name' => $b->slug.'-p', 'normalized_name' => $b->slug.'-p']);
            $this->makeOffer($p);
        }

        $response = $this->getJson('/api/public/v1/offers?brand=ab,lidl')->assertOk();

        $slugs = array_column(array_column($response->json('data'), 'brand'), 'slug');
        sort($slugs);
        $this->assertSame(['ab', 'lidl'], $slugs);
    }

    public function test_category_filter_is_case_insensitive(): void
    {
        $brand = $this->makeBrand();
        $cheese = $this->makeProduct($brand, ['category' => 'Τυριά', 'name' => 'cheese', 'normalized_name' => 'cheese']);
        $bread = $this->makeProduct($brand, ['category' => 'Ψωμί', 'name' => 'bread', 'normalized_name' => 'bread']);
        $this->makeOffer($cheese);
        $this->makeOffer($bread);

        $response = $this->getJson('/api/public/v1/offers?category='.urlencode('τυριά'))->assertOk();

        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame('cheese', $response->json('data.0.product.name'));
    }

    public function test_min_discount_filter(): void
    {
        $brand = $this->makeBrand();
        $p1 = $this->makeProduct($brand, ['name' => 'low', 'normalized_name' => 'low']);
        $p2 = $this->makeProduct($brand, ['name' => 'high', 'normalized_name' => 'high']);
        $this->makeOffer($p1, ['discount_pct' => 10]);
        $this->makeOffer($p2, ['discount_pct' => 40]);

        $response = $this->getJson('/api/public/v1/offers?min_discount=25')->assertOk();

        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame(40, $response->json('data.0.discount_pct'));
    }

    public function test_has_discount_filter(): void
    {
        // Since the discounted-only ingest policy landed (2026-05-25)
        // every persisted offer carries some promo signal — the
        // ``offers_require_promo_signal`` trigger refuses anything
        // else. ``has_discount=true`` narrows to rows with
        // ``discount_pct > 0`` specifically (vs label-only / strike-
        // only signals); test that the filter still does what it
        // says, by mixing a label-only signal row in with a
        // numeric-discount row and asserting only the latter passes.
        $brand = $this->makeBrand();
        $p1 = $this->makeProduct($brand, ['name' => 'label-only', 'normalized_name' => 'label-only']);
        $p2 = $this->makeProduct($brand, ['name' => 'disc', 'normalized_name' => 'disc']);
        // Label-only signal (e.g. AB "1+1 δώρο" path) — passes the
        // ingest trigger but should not match has_discount=true.
        $this->makeOffer($p1, [
            'price' => 5.00,
            'original_price' => null,
            'discount_pct' => null,
            'promo_label' => '1+1 δώρο',
            'promo_type' => 'bxgy_free',
        ]);
        $this->makeOffer($p2, [
            'price' => 4.00,
            'original_price' => 6.00,
            'discount_pct' => 33,
        ]);

        $response = $this->getJson('/api/public/v1/offers?has_discount=true')->assertOk();

        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame('disc', $response->json('data.0.product.name'));
    }

    public function test_valid_on_default_is_today(): void
    {
        $brand = $this->makeBrand();
        $current = $this->makeProduct($brand, ['name' => 'current', 'normalized_name' => 'current']);
        $expired = $this->makeProduct($brand, ['name' => 'expired', 'normalized_name' => 'expired']);
        $future = $this->makeProduct($brand, ['name' => 'future', 'normalized_name' => 'future']);

        $this->makeOffer($current, [
            'valid_from' => Carbon::now()->subDays(1)->toDateString(),
            'valid_to' => Carbon::now()->addDays(7)->toDateString(),
        ]);
        $this->makeOffer($expired, [
            'valid_from' => Carbon::now()->subDays(30)->toDateString(),
            'valid_to' => Carbon::now()->subDays(1)->toDateString(),
        ]);
        $this->makeOffer($future, [
            'valid_from' => Carbon::now()->addDays(5)->toDateString(),
            'valid_to' => Carbon::now()->addDays(30)->toDateString(),
        ]);

        $response = $this->getJson('/api/public/v1/offers')->assertOk();

        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame('current', $response->json('data.0.product.name'));
    }

    public function test_valid_on_explicit(): void
    {
        $brand = $this->makeBrand();
        $p = $this->makeProduct($brand, ['name' => 'p', 'normalized_name' => 'p']);
        $this->makeOffer($p, [
            'valid_from' => '2026-01-01',
            'valid_to' => '2026-01-31',
        ]);

        // Today (default) is outside the window.
        $this->getJson('/api/public/v1/offers')->assertOk()->assertJsonPath('meta.total', 0);

        $this->getJson('/api/public/v1/offers?valid_on=2026-01-15')
            ->assertOk()
            ->assertJsonPath('meta.total', 1);
    }

    public function test_valid_on_null_bounds_are_open(): void
    {
        $brand = $this->makeBrand();
        $p = $this->makeProduct($brand, ['name' => 'p', 'normalized_name' => 'p']);
        $this->makeOffer($p, ['valid_from' => null, 'valid_to' => null]);

        $this->getJson('/api/public/v1/offers?valid_on=2099-12-31')
            ->assertOk()
            ->assertJsonPath('meta.total', 1);
    }

    public function test_q_search_normalises_greek_accents(): void
    {
        $brand = $this->makeBrand();
        $feta = $this->makeProduct($brand, ['name' => 'Φέτα ΠΟΠ 400γρ', 'normalized_name' => \App\Support\StringNormalizer::normalize('Φέτα ΠΟΠ 400γρ')]);
        $other = $this->makeProduct($brand, ['name' => 'Ντομάτες', 'normalized_name' => \App\Support\StringNormalizer::normalize('Ντομάτες')]);
        $this->makeOffer($feta);
        $this->makeOffer($other);

        // Searching with accented and unaccented variants both hit the
        // same normalized row.
        $r1 = $this->getJson('/api/public/v1/offers?q='.urlencode('φετα'))->assertOk();
        $this->assertSame(1, $r1->json('meta.total'));
        $this->assertSame('Φέτα ΠΟΠ 400γρ', $r1->json('data.0.product.name'));

        $r2 = $this->getJson('/api/public/v1/offers?q='.urlencode('Φέτα'))->assertOk();
        $this->assertSame(1, $r2->json('meta.total'));
    }

    public function test_sort_and_dir(): void
    {
        $brand = $this->makeBrand();
        $cheap = $this->makeProduct($brand, ['name' => 'cheap', 'normalized_name' => 'cheap']);
        $mid = $this->makeProduct($brand, ['name' => 'mid', 'normalized_name' => 'mid']);
        $expensive = $this->makeProduct($brand, ['name' => 'expensive', 'normalized_name' => 'expensive']);
        $this->makeOffer($cheap, ['price' => 1.00, 'discount_pct' => 5]);
        $this->makeOffer($mid, ['price' => 5.00, 'discount_pct' => 25]);
        $this->makeOffer($expensive, ['price' => 20.00, 'discount_pct' => 50]);

        // Default: discount_pct desc
        $r1 = $this->getJson('/api/public/v1/offers')->assertOk();
        $this->assertSame([50, 25, 5], array_column($r1->json('data'), 'discount_pct'));

        // price asc. JSON encoding of whole-number floats drops the
        // decimal (1.0 -> 1), so compare as float through (float) cast.
        $r2 = $this->getJson('/api/public/v1/offers?sort=price&dir=asc')->assertOk();
        $this->assertSame(
            [1.0, 5.0, 20.0],
            array_map('floatval', array_column($r2->json('data'), 'price')),
        );
    }

    public function test_pagination(): void
    {
        $brand = $this->makeBrand();
        for ($i = 0; $i < 5; $i++) {
            $p = $this->makeProduct($brand, ['name' => "p{$i}", 'normalized_name' => "p{$i}"]);
            $this->makeOffer($p, ['discount_pct' => 10 + $i]);
        }

        $page1 = $this->getJson('/api/public/v1/offers?per_page=2&page=1')->assertOk();
        $this->assertCount(2, $page1->json('data'));
        $this->assertSame(5, $page1->json('meta.total'));
        $this->assertSame(3, $page1->json('meta.last_page'));

        $page3 = $this->getJson('/api/public/v1/offers?per_page=2&page=3')->assertOk();
        $this->assertCount(1, $page3->json('data'));
    }

    public function test_per_page_above_max_is_rejected(): void
    {
        $this->makeBrand();
        $this->getJson('/api/public/v1/offers?per_page=101')
            ->assertStatus(422)
            ->assertJsonValidationErrors(['per_page']);
    }

    public function test_unknown_query_params_are_rejected(): void
    {
        $this->makeBrand();
        $this->getJson('/api/public/v1/offers?bogus=1&category=x')
            ->assertStatus(422)
            ->assertJsonValidationErrors(['bogus']);
    }

    public function test_invalid_sort_is_rejected(): void
    {
        $this->makeBrand();
        $this->getJson('/api/public/v1/offers?sort=banana')
            ->assertStatus(422)
            ->assertJsonValidationErrors(['sort']);
    }

    public function test_inactive_brand_offers_are_excluded(): void
    {
        $active = $this->makeBrand(['slug' => 'ab']);
        $inactive = $this->makeBrand(['slug' => 'sklavenitis', 'website_url' => 'https://sklav', 'active' => false]);
        $p1 = $this->makeProduct($active, ['name' => 'a', 'normalized_name' => 'a']);
        $p2 = $this->makeProduct($inactive, ['name' => 'b', 'normalized_name' => 'b']);
        $this->makeOffer($p1);
        $this->makeOffer($p2);

        $response = $this->getJson('/api/public/v1/offers')->assertOk();
        $this->assertSame(1, $response->json('meta.total'));
        $this->assertSame('ab', $response->json('data.0.brand.slug'));
    }
}
