<?php

namespace Tests\Feature\Api;

use App\Models\Brand;
use App\Models\CanonicalProduct;
use App\Models\Product;
use App\Support\StringNormalizer;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use RuntimeException;

class CanonicalBulkUpsertTest extends ApiTestCase
{
    private function makeBrand(string $slug, string $name): Brand
    {
        return Brand::create([
            'name' => $name,
            'slug' => $slug,
            'website_url' => "https://www.{$slug}.gr",
            'active' => true,
        ]);
    }

    private function makeProduct(Brand $brand, string $name, array $overrides = []): Product
    {
        return Product::create(array_merge([
            'brand_id' => $brand->id,
            'external_id' => 'SKU-'.uniqid(),
            'name' => $name,
            'normalized_name' => StringNormalizer::normalize($name),
            'url' => "https://{$brand->slug}.gr/p/x",
            'image_url' => "https://cdn.{$brand->slug}.gr/x.jpg",
            'category' => 'Σοκολάτες',
            'unit' => 'τεμ',
        ], $overrides));
    }

    public function test_unauthenticated_requests_are_rejected(): void
    {
        $this->postJson('/api/v1/canonical-products/bulk-upsert', [])
            ->assertUnauthorized();
    }

    public function test_wrong_ability_is_rejected(): void
    {
        $this->authedAsCrawler(['some:other']);

        $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [],
        ])->assertForbidden();
    }

    public function test_validation_rejects_bad_payload(): void
    {
        $this->authedAsCrawler();

        $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    // missing canonical_key, manufacturer_brand, display_name
                    'members' => [
                        ['product_id' => 1, 'confidence' => 2.0, 'match_method' => 'magic'],
                    ],
                ],
            ],
        ])->assertUnprocessable()->assertJsonValidationErrors([
            'groupings.0.canonical_key',
            'groupings.0.manufacturer_brand',
            'groupings.0.display_name',
            'groupings.0.members.0.confidence',
            'groupings.0.members.0.match_method',
        ]);
    }

    public function test_validation_rejects_empty_members(): void
    {
        $this->authedAsCrawler();

        $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    'canonical_key' => 'lacta:gofreta:31g:1',
                    'manufacturer_brand' => 'Lacta',
                    'display_name' => 'Lacta Γκοφρέτα',
                    'members' => [],
                ],
            ],
        ])->assertUnprocessable()->assertJsonValidationErrors('groupings.0.members');
    }

    public function test_validation_caps_members_at_200(): void
    {
        $this->authedAsCrawler();

        $members = [];
        for ($i = 1; $i <= 201; $i++) {
            $members[] = ['product_id' => $i, 'confidence' => 1.0, 'match_method' => 'rule'];
        }

        $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    'canonical_key' => 'x:y:1g:1',
                    'manufacturer_brand' => 'X',
                    'display_name' => 'X',
                    'members' => $members,
                ],
            ],
        ])->assertUnprocessable()->assertJsonValidationErrors('groupings.0.members');
    }

    public function test_happy_path_creates_canonical_and_assigns_members(): void
    {
        $this->authedAsCrawler();
        $sklav = $this->makeBrand('sklavenitis', 'Sklavenitis');
        $mm = $this->makeBrand('my-market', 'My Market');
        $p1 = $this->makeProduct($sklav, 'LACTA Γκοφρέτα Φουντούκι 31g');
        $p2 = $this->makeProduct($mm, 'Lacta Γκοφρέτα Φουντουκιού 31gr');

        $response = $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    'canonical_key' => 'lacta:gofreta-foundouki:31g:1',
                    'manufacturer_brand' => 'Lacta',
                    'size_value' => 31.0,
                    'size_unit' => 'g',
                    'pack_count' => 1,
                    'variant_descriptor' => 'Φουντούκι',
                    'display_name' => 'Lacta Γκοφρέτα Φουντούκι 31g',
                    'category' => 'Σοκολάτες',
                    'image_url' => 'https://cdn.example/lacta.jpg',
                    'members' => [
                        ['product_id' => $p1->id, 'confidence' => 1.0, 'match_method' => 'rule'],
                        ['product_id' => $p2->id, 'confidence' => 0.98, 'match_method' => 'rule'],
                    ],
                ],
            ],
        ])->assertOk();

        $response->assertJsonPath('created', 1);
        $response->assertJsonPath('updated', 0);
        $response->assertJsonPath('products_assigned', 2);
        $response->assertJsonPath('errors', []);

        $this->assertDatabaseHas('canonical_products', [
            'canonical_key' => 'lacta:gofreta-foundouki:31g:1',
            'manufacturer_brand' => 'Lacta',
            'size_unit' => 'g',
            'pack_count' => 1,
            'members_count' => 2,
            'brands_count' => 2,
        ]);

        $canonical = CanonicalProduct::query()
            ->where('canonical_key', 'lacta:gofreta-foundouki:31g:1')
            ->firstOrFail();

        $p1->refresh();
        $p2->refresh();
        $this->assertSame($canonical->id, (int) $p1->canonical_product_id);
        $this->assertSame($canonical->id, (int) $p2->canonical_product_id);
        $this->assertSame('rule', $p1->canonical_match_method);
        $this->assertSame(1.0, (float) $p1->canonical_match_confidence);
        $this->assertSame(0.98, round((float) $p2->canonical_match_confidence, 2));
        $this->assertNotNull($p1->canonical_matched_at);
    }

    public function test_reupsert_is_idempotent_and_updates_display_name(): void
    {
        $this->authedAsCrawler();
        $sklav = $this->makeBrand('sklavenitis', 'Sklavenitis');
        $p1 = $this->makeProduct($sklav, 'LACTA Γκοφρέτα 31g');

        $body = [
            'groupings' => [
                [
                    'canonical_key' => 'lacta:gofreta:31g:1',
                    'manufacturer_brand' => 'Lacta',
                    'display_name' => 'Lacta Γκοφρέτα 31g',
                    'category' => 'Σοκολάτες',
                    'members' => [
                        ['product_id' => $p1->id, 'confidence' => 1.0, 'match_method' => 'rule'],
                    ],
                ],
            ],
        ];

        $this->postJson('/api/v1/canonical-products/bulk-upsert', $body)
            ->assertOk()
            ->assertJsonPath('created', 1);

        // Second push: nothing changed -> no `updated` increment, but
        // products_assigned still counts the (idempotent) re-stamp.
        $this->postJson('/api/v1/canonical-products/bulk-upsert', $body)
            ->assertOk()
            ->assertJsonPath('created', 0)
            ->assertJsonPath('updated', 0);

        // Third push: change display_name -> updated++.
        $body['groupings'][0]['display_name'] = 'Lacta Γκοφρέτα Φουντούκι 31g';
        $this->postJson('/api/v1/canonical-products/bulk-upsert', $body)
            ->assertOk()
            ->assertJsonPath('updated', 1);

        $this->assertDatabaseHas('canonical_products', [
            'canonical_key' => 'lacta:gofreta:31g:1',
            'display_name' => 'Lacta Γκοφρέτα Φουντούκι 31g',
        ]);
        // Only ever one row.
        $this->assertSame(1, CanonicalProduct::query()
            ->where('canonical_key', 'lacta:gofreta:31g:1')->count());
    }

    public function test_higher_confidence_assignment_is_not_overwritten(): void
    {
        $this->authedAsCrawler();
        $sklav = $this->makeBrand('sklavenitis', 'Sklavenitis');
        $p1 = $this->makeProduct($sklav, 'LACTA Γκοφρέτα 31g');

        // Seed: a manual reviewer (confidence 1.0) assigned p1 to canonical A.
        $a = CanonicalProduct::create([
            'canonical_key' => 'a',
            'manufacturer_brand' => 'Lacta',
            'display_name' => 'A',
        ]);
        $p1->canonical_product_id = $a->id;
        $p1->canonical_match_confidence = 1.0;
        $p1->canonical_match_method = 'manual';
        $p1->canonical_matched_at = now();
        $p1->save();
        $a->refreshAggregates();

        // Now a rule-based pass tries to move it to canonical B at 0.95.
        $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    'canonical_key' => 'b',
                    'manufacturer_brand' => 'Lacta',
                    'display_name' => 'B',
                    'members' => [
                        ['product_id' => $p1->id, 'confidence' => 0.95, 'match_method' => 'rule'],
                    ],
                ],
            ],
        ])->assertOk();

        $p1->refresh();
        // Still pointed at A, untouched.
        $this->assertSame($a->id, (int) $p1->canonical_product_id);
        $this->assertSame('manual', $p1->canonical_match_method);
        $this->assertSame(1.0, (float) $p1->canonical_match_confidence);

        // Aggregates: A still owns 1 member; B has 0.
        $a->refresh();
        $b = CanonicalProduct::where('canonical_key', 'b')->firstOrFail();
        $this->assertSame(1, $a->members_count);
        $this->assertSame(0, $b->members_count);
    }

    public function test_unknown_product_ids_are_collected_in_errors(): void
    {
        $this->authedAsCrawler();
        $sklav = $this->makeBrand('sklavenitis', 'Sklavenitis');
        $p1 = $this->makeProduct($sklav, 'LACTA Γκοφρέτα 31g');

        $response = $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    'canonical_key' => 'x',
                    'manufacturer_brand' => 'Lacta',
                    'display_name' => 'X',
                    'members' => [
                        ['product_id' => $p1->id, 'confidence' => 1.0, 'match_method' => 'rule'],
                        ['product_id' => 999999, 'confidence' => 1.0, 'match_method' => 'rule'],
                    ],
                ],
            ],
        ])->assertOk();

        $response->assertJsonPath('products_assigned', 1);
        $this->assertCount(1, $response->json('errors'));
        $this->assertSame('product_not_found', $response->json('errors.0.reason'));
        $this->assertSame(999999, $response->json('errors.0.product_id'));
    }

    public function test_aggregates_track_brand_count(): void
    {
        $this->authedAsCrawler();
        $sklav = $this->makeBrand('sklavenitis', 'Sklavenitis');
        $mm = $this->makeBrand('my-market', 'My Market');
        $masoutis = $this->makeBrand('masoutis', 'Masoutis');

        $p1 = $this->makeProduct($sklav, 'LACTA Γκοφρέτα 31g');
        $p2 = $this->makeProduct($mm, 'Lacta Γκοφρέτα 31gr');
        $p3 = $this->makeProduct($masoutis, 'Lacta Γκοφρέτα 31γρ.');

        $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    'canonical_key' => 'lacta:gofreta:31g:1',
                    'manufacturer_brand' => 'Lacta',
                    'display_name' => 'Lacta Γκοφρέτα 31g',
                    'members' => [
                        ['product_id' => $p1->id, 'confidence' => 1.0, 'match_method' => 'rule'],
                        ['product_id' => $p2->id, 'confidence' => 1.0, 'match_method' => 'rule'],
                        ['product_id' => $p3->id, 'confidence' => 1.0, 'match_method' => 'rule'],
                    ],
                ],
            ],
        ])->assertOk();

        $c = CanonicalProduct::where('canonical_key', 'lacta:gofreta:31g:1')->firstOrFail();
        $this->assertSame(3, $c->members_count);
        $this->assertSame(3, $c->brands_count);
    }

    public function test_duplicate_brand_member_is_skipped_not_fatal(): void
    {
        // Phase 2.1 regression: when two same-brand products are pushed
        // as members of one canonical, the partial unique index on
        // (canonical_product_id, brand_id) rejects the second one. The
        // action must log a structured warning, skip the loser, and
        // surface the count in the response envelope — never bubble.
        $this->authedAsCrawler();
        $mm = $this->makeBrand('my-market', 'My Market');

        $p1 = $this->makeProduct($mm, 'Axe Αποσμητικό Σπρέι Marine 150ml');
        $p2 = $this->makeProduct($mm, 'Axe Αποσμητικό Σπρέι Africa 150ml');

        // Capture log lines emitted by the warning channel.
        $records = [];
        Log::listen(function ($message) use (&$records): void {
            $records[] = $message;
        });

        $response = $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    'canonical_key' => 'axe:aposmhtiko-sprei:150ml:1',
                    'manufacturer_brand' => 'Axe',
                    'size_value' => 150.0,
                    'size_unit' => 'ml',
                    'pack_count' => 1,
                    'display_name' => 'Axe Αποσμητικό Σπρέι 150ml',
                    'members' => [
                        ['product_id' => $p1->id, 'confidence' => 0.95, 'match_method' => 'rule'],
                        ['product_id' => $p2->id, 'confidence' => 0.95, 'match_method' => 'rule'],
                    ],
                ],
            ],
        ]);

        // No exception bubbled — request succeeded.
        $response->assertOk();
        // (a) One member landed.
        $response->assertJsonPath('products_assigned', 1);
        // (c) duplicate_brand_skipped counter is 1.
        $response->assertJsonPath('duplicate_brand_skipped', 1);

        // (b) The first landed, the second is unassigned. The unique
        // index can theoretically pick either one as the winner, but
        // both rows existing in their pre/post state is the invariant
        // we care about: exactly one product points at the canonical.
        $p1->refresh();
        $p2->refresh();
        $canonical = CanonicalProduct::query()
            ->where('canonical_key', 'axe:aposmhtiko-sprei:150ml:1')
            ->firstOrFail();
        $assignedIds = Product::query()
            ->where('canonical_product_id', $canonical->id)
            ->pluck('id')
            ->all();
        $this->assertCount(1, $assignedIds);
        $this->assertContains($assignedIds[0], [$p1->id, $p2->id]);

        // (d) A structured warning was emitted with the right shape.
        $skipped = array_filter(
            $records,
            fn ($r) => is_object($r)
                && property_exists($r, 'message')
                && $r->message === 'canonical_bulk_upsert.duplicate_brand_skipped'
        );
        $this->assertNotEmpty($skipped, 'expected a duplicate_brand_skipped log line');
        /** @var object $log */
        $log = array_values($skipped)[0];
        $this->assertSame($canonical->id, $log->context['canonical_id']);
        $this->assertSame($mm->id, $log->context['brand_id']);
        $this->assertContains(
            $log->context['skipped_product_id'],
            [$p1->id, $p2->id]
        );
        $this->assertContains(
            $log->context['existing_product_id'],
            [$p1->id, $p2->id]
        );
        $this->assertNotSame(
            $log->context['skipped_product_id'],
            $log->context['existing_product_id']
        );

        // Canonical aggregates reflect the one member that landed.
        $canonical->refresh();
        $this->assertSame(1, $canonical->members_count);
        $this->assertSame(1, $canonical->brands_count);
    }

    public function test_transaction_rolls_back_on_exception(): void
    {
        $this->authedAsCrawler();
        $sklav = $this->makeBrand('sklavenitis', 'Sklavenitis');
        $p1 = $this->makeProduct($sklav, 'LACTA Γκοφρέτα 31g');

        // Force a DB exception mid-transaction by mocking DB::transaction
        // would be invasive; instead, send a payload with a member that
        // exists, then poison the products table with a query listener
        // that throws on the second canonical's insert.
        DB::listen(function ($query): void {
            if (str_starts_with($query->sql, 'insert into "canonical_products"')
                && str_contains((string) ($query->bindings[0] ?? ''), 'boom')
            ) {
                throw new RuntimeException('boom');
            }
        });

        $response = $this->postJson('/api/v1/canonical-products/bulk-upsert', [
            'groupings' => [
                [
                    'canonical_key' => 'ok',
                    'manufacturer_brand' => 'Lacta',
                    'display_name' => 'OK',
                    'members' => [
                        ['product_id' => $p1->id, 'confidence' => 1.0, 'match_method' => 'rule'],
                    ],
                ],
                [
                    'canonical_key' => 'boom',
                    'manufacturer_brand' => 'Lacta',
                    'display_name' => 'BOOM',
                    'members' => [
                        ['product_id' => $p1->id, 'confidence' => 1.0, 'match_method' => 'rule'],
                    ],
                ],
            ],
        ])->assertStatus(500);

        $response->assertJsonPath('error', 'canonical_bulk_upsert_failed');
        $this->assertStringContainsString('Safe to retry', $response->json('message'));

        // Full rollback: no canonical rows from this batch.
        $this->assertSame(0, CanonicalProduct::query()->count());
        $p1->refresh();
        $this->assertNull($p1->canonical_product_id);
    }
}
