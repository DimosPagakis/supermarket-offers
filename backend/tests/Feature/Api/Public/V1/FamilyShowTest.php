<?php

namespace Tests\Feature\Api\Public\V1;

use App\Models\Brand;
use App\Models\Offer;
use App\Models\Product;
use App\Support\StringNormalizer;
use Illuminate\Support\Carbon;

/**
 * Feature tests for GET /api/public/v1/families/{key}.
 *
 * Pins the variant grouping, latest-per-product offer collapse,
 * cheapest-brand highlighting, and the 404 path on malformed keys.
 */
class FamilyShowTest extends PublicApiTestCase
{
    private function seedVariant(
        Brand $brand,
        string $manufacturer,
        string $category,
        float $sizeValue,
        string $sizeUnit,
        int $pack,
        ?string $variantDescriptor,
        ?float $price,
        ?string $name = null,
    ): Product {
        $displayName = $name ?? sprintf('%s %s %s %s%s',
            ucfirst($manufacturer), $category, $variantDescriptor ?? '', $sizeValue, $sizeUnit);

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
        if ($price !== null) {
            $this->makeOffer($product, ['price' => $price]);
        }

        return $product;
    }

    private function familyKey(
        string $manufacturer,
        string $category,
        float $sizeValue,
        string $sizeUnit,
        int $pack,
    ): string {
        return sprintf(
            '%s|%s|%s|%s|%d',
            $manufacturer,
            StringNormalizer::normalize($category),
            floor($sizeValue) === $sizeValue ? (int) $sizeValue : $sizeValue,
            $sizeUnit,
            $pack,
        );
    }

    public function test_show_groups_members_by_variant_descriptor(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $sk = $this->makeBrand(['slug' => 'sklavenitis', 'name' => 'Sklavenitis', 'website_url' => 'https://sk']);

        // Family: Axe 150ml. Two scents, each present in both chains.
        $this->seedVariant($ab, 'axe', 'Αποσμητικά', 150, 'ml', 1, 'africa', 2.50);
        $this->seedVariant($sk, 'axe', 'Αποσμητικά', 150, 'ml', 1, 'africa', 2.80);
        $this->seedVariant($ab, 'axe', 'Αποσμητικά', 150, 'ml', 1, 'marine', 2.60);
        $this->seedVariant($sk, 'axe', 'Αποσμητικά', 150, 'ml', 1, 'marine', 2.70);

        $key = $this->familyKey('axe', 'Αποσμητικά', 150, 'ml', 1);
        $r = $this->getJson('/api/public/v1/families/'.rawurlencode($key))->assertOk();

        $r->assertJsonStructure([
            'data' => [
                'key', 'manufacturer_brand', 'category', 'size_value', 'size_unit', 'pack_count',
                'display_name', 'image_url',
                'variants_count', 'brands_count',
                'min_price', 'max_price', 'avg_price',
                'variants' => [['variant_descriptor', 'products', 'min_price', 'max_price', 'cheapest_brand']],
            ],
        ]);

        $this->assertSame(4, $r->json('data.variants_count'));
        $this->assertSame(2, $r->json('data.brands_count'));
        $this->assertEqualsWithDelta(2.50, (float) $r->json('data.min_price'), 0.001);
        $this->assertEqualsWithDelta(2.80, (float) $r->json('data.max_price'), 0.001);

        $variants = $r->json('data.variants');
        $this->assertCount(2, $variants);
        // Variants sort by min_price asc — africa (2.50) before marine (2.60).
        $this->assertSame('africa', $variants[0]['variant_descriptor']);
        $this->assertSame('marine', $variants[1]['variant_descriptor']);
        // Each variant has its 2 products.
        $this->assertCount(2, $variants[0]['products']);
        $this->assertCount(2, $variants[1]['products']);
        // Per-variant cheapest: africa's lowest is AB @ 2.50.
        $this->assertSame('ab', $variants[0]['cheapest_brand']['slug']);
        // Inside the variant, products order cheapest-first.
        $this->assertSame('ab', $variants[0]['products'][0]['brand']['slug']);
    }

    public function test_show_uses_latest_offer_per_product(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);

        $a = $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'africa', 3.00);
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'marine', 2.80);

        // Stale older offer for `a`. The detail endpoint picks the
        // higher offer id (latest) — so `a`'s current price is 1.00.
        // discount_pct satisfies the DB-level promo-signal trigger
        // (offers_require_promo_signal) shipped in the catalogue-leak
        // cleanup migration.
        Offer::create([
            'product_id' => $a->id,
            'price' => 1.00,
            'original_price' => 2.00,
            'discount_pct' => 50,
            'currency' => 'EUR',
            'scraped_at' => Carbon::now()->addMinute(),
        ]);

        $key = $this->familyKey('axe', 'A', 150, 'ml', 1);
        $r = $this->getJson('/api/public/v1/families/'.rawurlencode($key))->assertOk();

        $this->assertEqualsWithDelta(1.00, (float) $r->json('data.min_price'), 0.001);
    }

    public function test_show_404_when_key_malformed(): void
    {
        $this->getJson('/api/public/v1/families/'.rawurlencode('not-enough-parts'))
            ->assertNotFound();
    }

    public function test_show_404_when_family_does_not_exist(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'africa', 2.50);

        $key = $this->familyKey('nonexistent', 'Z', 999, 'g', 1);
        $this->getJson('/api/public/v1/families/'.rawurlencode($key))
            ->assertNotFound();
    }

    public function test_show_excludes_expired_offers_from_pricing(): void
    {
        $ab = $this->makeBrand(['slug' => 'ab']);
        $product = $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'africa', 2.50);
        // Mutate the only offer to expire yesterday — pricing should
        // drop the row, but the product still appears (as null offer).
        Offer::where('product_id', $product->id)->update([
            'valid_from' => Carbon::now()->subDays(5)->toDateString(),
            'valid_to' => Carbon::now()->subDays(1)->toDateString(),
        ]);
        $this->seedVariant($ab, 'axe', 'A', 150, 'ml', 1, 'marine', 2.80);

        $key = $this->familyKey('axe', 'A', 150, 'ml', 1);
        $r = $this->getJson('/api/public/v1/families/'.rawurlencode($key))->assertOk();

        $this->assertEqualsWithDelta(2.80, (float) $r->json('data.min_price'), 0.001);
        $this->assertEqualsWithDelta(2.80, (float) $r->json('data.max_price'), 0.001);
        // Both variants still listed.
        $this->assertSame(2, $r->json('data.variants_count'));
    }
}
