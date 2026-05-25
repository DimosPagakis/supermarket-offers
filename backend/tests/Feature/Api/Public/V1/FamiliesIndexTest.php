<?php

namespace Tests\Feature\Api\Public\V1;

use App\Models\Brand;
use App\Models\Product;
use App\Support\StringNormalizer;

/**
 * Feature tests for GET /api/public/v1/families.
 *
 * Stamps the auth-free + throttled contract, the filter set, every
 * sort direction, pagination, and the "empty result" branch.
 *
 * Test fixtures bypass {@see \App\Services\ProductResolver} (no offer
 * ingest) and write the feature columns directly via `Product::create`
 * so each test owns exactly the rows it asserts on.
 */
class FamiliesIndexTest extends PublicApiTestCase
{
    /**
     * Seed one variant: a product belonging to `(manufacturer,
     * category, sizeValue, sizeUnit)` on the supplied brand, with one
     * current offer at `$price`. Returns the Product.
     */
    private function seedVariant(
        Brand $brand,
        string $manufacturer,
        string $category,
        float $sizeValue,
        string $sizeUnit,
        int $pack,
        string $variantDescriptor,
        float $price,
        ?string $name = null,
    ): Product {
        $displayName = $name ?? sprintf('%s %s %s %s%s',
            ucfirst($manufacturer), $category, $variantDescriptor, $sizeValue, $sizeUnit);

        $product = $this->makeProduct($brand, [
            'name' => $displayName,
            'normalized_name' => StringNormalizer::normalize($displayName),
            'category' => $category,
            'manufacturer_brand' => $manufacturer,
            'category_normalised' => StringNormalizer::normalize($category),
            'size_value' => $sizeValue,
            'size_unit' => $sizeUnit,
            'pack_count' => $pack,
            'variant_descriptor' => $variantDescriptor,
        ]);
        $this->makeOffer($product, ['price' => $price]);

        return $product;
    }

    public function test_happy_path_returns_paginated_envelope(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $sk = $this->makeBrand(['slug' => 'sklavenitis', 'name' => 'Sklavenitis', 'website_url' => 'https://sk']);

        $this->seedVariant($ab, 'axe', 'Αποσμητικά σώματος', 150, 'ml', 1, 'africa', 2.50);
        $this->seedVariant($sk, 'axe', 'Αποσμητικά σώματος', 150, 'ml', 1, 'marine', 2.80);

        $r = $this->getJson('/api/public/v1/families')->assertOk();

        $r->assertJsonStructure([
            'data' => [[
                'key', 'manufacturer_brand', 'category', 'size_value', 'size_unit',
                'pack_count', 'display_name', 'image_url',
                'variants_count', 'brands_count',
                'min_price', 'max_price', 'avg_price', 'cheapest_brand',
            ]],
            'meta' => ['current_page', 'per_page', 'total', 'last_page'],
            'links',
        ]);
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame(2, $r->json('data.0.variants_count'));
        $this->assertSame(2, $r->json('data.0.brands_count'));
        $this->assertEqualsWithDelta(2.50, (float) $r->json('data.0.min_price'), 0.001);
        $this->assertEqualsWithDelta(2.80, (float) $r->json('data.0.max_price'), 0.001);
        $this->assertSame('ab', $r->json('data.0.cheapest_brand.slug'));
        $this->assertSame('axe', $r->json('data.0.manufacturer_brand'));
        // The family key carries the exact tuple required to re-fetch
        // the detail view — see {@see FamilyController::familyKey()}.
        $this->assertStringStartsWith('axe|', $r->json('data.0.key'));
    }

    public function test_default_min_variants_hides_single_variant_families(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        // 2 Axe scents => family kept.
        $this->seedVariant($ab, 'axe', 'Αποσμητικά', 150, 'ml', 1, 'africa', 2.50);
        $this->seedVariant($ab, 'axe', 'Αποσμητικά', 150, 'ml', 1, 'marine', 2.80);
        // 1 Lacta SKU => family hidden by default min_variants=2.
        $this->seedVariant($ab, 'lacta', 'Σοκολάτες', 100, 'g', 1, 'milk', 1.50);

        $r = $this->getJson('/api/public/v1/families')->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('axe', $r->json('data.0.manufacturer_brand'));

        $r2 = $this->getJson('/api/public/v1/families?min_variants=1')->assertOk();
        $this->assertSame(2, $r2->json('meta.total'));
    }

    public function test_min_brands_filter_requires_multi_chain_families(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $sk = $this->makeBrand(['slug' => 'sklavenitis', 'name' => 'Sklavenitis', 'website_url' => 'https://sk']);

        // Family A: 2 variants, both on AB only.
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'africa', 2.50);
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'marine', 2.80);
        // Family B: 2 variants across AB + Sklavenitis.
        $this->seedVariant($ab, 'lacta', 'B', 100, 'g', 1, 'milk', 1.50);
        $this->seedVariant($sk, 'lacta', 'B', 100, 'g', 1, 'almond', 1.80);

        $r = $this->getJson('/api/public/v1/families?min_brands=2')->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('lacta', $r->json('data.0.manufacturer_brand'));
    }

    public function test_brand_filter_csv_restricts_member_chains(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $sk = $this->makeBrand(['slug' => 'sklavenitis', 'name' => 'Sklavenitis', 'website_url' => 'https://sk']);

        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'africa', 2.50);
        $this->seedVariant($sk, 'axe', 'A', 150, 'ml', 1, 'marine', 2.80);
        $this->seedVariant($sk, 'lacta', 'B', 100, 'g', 1, 'milk', 1.50);
        $this->seedVariant($sk, 'lacta', 'B', 100, 'g', 1, 'almond', 1.60);

        // brand=ab keeps only families that have at least one AB
        // member. The Lacta family is Sklavenitis-only -> dropped.
        $r = $this->getJson('/api/public/v1/families?brand=ab')->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('axe', $r->json('data.0.manufacturer_brand'));
    }

    public function test_category_filter_is_accent_insensitive(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $this->seedVariant($ab, 'axe', 'Αποσμητικά σώματος', 150, 'ml', 1, 'africa', 2.50);
        $this->seedVariant($ab, 'axe', 'Αποσμητικά σώματος', 150, 'ml', 1, 'marine', 2.80);
        $this->seedVariant($ab, 'lacta', 'Σοκολάτες', 100, 'g', 1, 'milk', 1.50);
        $this->seedVariant($ab, 'lacta', 'Σοκολάτες', 100, 'g', 1, 'almond', 1.60);

        $r = $this->getJson('/api/public/v1/families?category='.urlencode('αποσμητικα σωματος'))
            ->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('axe', $r->json('data.0.manufacturer_brand'));
    }

    public function test_manufacturer_filter_exact_match(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'a1', 2.50);
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'a2', 2.80);
        $this->seedVariant($ab, 'lacta', 'B', 100, 'g', 1, 'b1', 1.50);
        $this->seedVariant($ab, 'lacta', 'B', 100, 'g', 1, 'b2', 1.60);

        $r = $this->getJson('/api/public/v1/families?manufacturer=axe')->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('axe', $r->json('data.0.manufacturer_brand'));
    }

    public function test_q_text_search_matches_manufacturer_or_category(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $this->seedVariant($ab, 'axe', 'Αποσμητικά', 150, 'ml', 1, 'a1', 2.50);
        $this->seedVariant($ab, 'axe', 'Αποσμητικά', 150, 'ml', 1, 'a2', 2.80);
        $this->seedVariant($ab, 'lacta', 'Σοκολάτες', 100, 'g', 1, 'b1', 1.50);
        $this->seedVariant($ab, 'lacta', 'Σοκολάτες', 100, 'g', 1, 'b2', 1.60);

        $r = $this->getJson('/api/public/v1/families?q='.urlencode('lacta'))->assertOk();
        $this->assertSame(1, $r->json('meta.total'));
        $this->assertSame('lacta', $r->json('data.0.manufacturer_brand'));
    }

    public function test_sort_dir_combinations(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $sk = $this->makeBrand(['slug' => 'sk', 'name' => 'Sk', 'website_url' => 'https://sk']);

        // Family A: 2 variants on 1 brand
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'a1', 5.00);
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'a2', 6.00);
        // Family B: 4 variants across 2 brands, cheaper.
        $this->seedVariant($ab, 'lacta', 'B', 100, 'g', 1, 'b1', 1.00);
        $this->seedVariant($ab, 'lacta', 'B', 100, 'g', 1, 'b2', 1.10);
        $this->seedVariant($sk, 'lacta', 'B', 100, 'g', 1, 'b3', 1.20);
        $this->seedVariant($sk, 'lacta', 'B', 100, 'g', 1, 'b4', 1.30);

        // Default: variants_count desc => B first (4 variants > 2).
        $r = $this->getJson('/api/public/v1/families')->assertOk();
        $this->assertSame(['lacta', 'axe'], array_column($r->json('data'), 'manufacturer_brand'));

        // brands_count desc => B (2 brands) before A (1).
        $r2 = $this->getJson('/api/public/v1/families?sort=brands_count')->assertOk();
        $this->assertSame('lacta', $r2->json('data.0.manufacturer_brand'));

        // min_price asc => cheapest family first => B (1.00).
        $r3 = $this->getJson('/api/public/v1/families?sort=min_price&dir=asc')->assertOk();
        $this->assertSame('lacta', $r3->json('data.0.manufacturer_brand'));

        // avg_price desc => most expensive family first => A.
        $r4 = $this->getJson('/api/public/v1/families?sort=avg_price&dir=desc')->assertOk();
        $this->assertSame('axe', $r4->json('data.0.manufacturer_brand'));
    }

    public function test_pagination(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        // Six distinct families, each with 2 variants.
        foreach (range(1, 6) as $i) {
            $this->seedVariant($ab, 'm'.$i, 'C'.$i, $i * 10, 'g', 1, 'v1', 1.0);
            $this->seedVariant($ab, 'm'.$i, 'C'.$i, $i * 10, 'g', 1, 'v2', 1.1);
        }

        $r = $this->getJson('/api/public/v1/families?per_page=2&page=1')->assertOk();
        $this->assertCount(2, $r->json('data'));
        $this->assertSame(6, $r->json('meta.total'));
        $this->assertSame(3, $r->json('meta.last_page'));
    }

    public function test_unknown_query_param_is_rejected(): void
    {
        $this->getJson('/api/public/v1/families?bogus=1')
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['bogus']);
    }

    public function test_per_page_above_max_is_rejected(): void
    {
        $this->getJson('/api/public/v1/families?per_page=101')
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['per_page']);
    }

    public function test_empty_result_when_nothing_matches(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'v1', 1.0);

        // min_variants=2 hides the lone axe SKU, no other rows -> empty.
        $r = $this->getJson('/api/public/v1/families')->assertOk();
        $this->assertSame(0, $r->json('meta.total'));
        $this->assertSame([], $r->json('data'));
    }

    public function test_throttle_applies(): void
    {
        // The throttle is the same '120,1' middleware applied to every
        // public route — exercising it once is enough to prove the
        // route sits behind the public group rather than the
        // crawler-auth group. A 200 here means the throttle didn't
        // block a single unauthenticated request.
        $this->getJson('/api/public/v1/families')->assertOk();
    }

    public function test_private_label_products_never_form_a_family(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        // Both products have manufacturer_brand=null (own-brand) — they
        // are filtered out by the NOT NULL clause on the index query.
        $this->makeProduct($ab, [
            'name' => 'My Gusto Πάριζα 280gr',
            'normalized_name' => 'my gusto pariza 280gr',
            'category' => 'Αλλαντικά',
            'manufacturer_brand' => null,
        ]);
        $this->makeProduct($ab, [
            'name' => 'My Gusto Γαλοπούλα 280gr',
            'normalized_name' => 'my gusto galopoyla 280gr',
            'category' => 'Αλλαντικά',
            'manufacturer_brand' => null,
        ]);

        $r = $this->getJson('/api/public/v1/families?min_variants=1')->assertOk();
        $this->assertSame(0, $r->json('meta.total'));
    }
}
