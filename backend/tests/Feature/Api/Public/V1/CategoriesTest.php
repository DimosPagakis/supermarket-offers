<?php

namespace Tests\Feature\Api\Public\V1;

use App\Http\Controllers\Api\Public\V1\CategoryController;
use App\Models\Product;
use Illuminate\Support\Facades\Cache;

class CategoriesTest extends PublicApiTestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        Cache::forget(CategoryController::CACHE_KEY);
    }

    public function test_returns_distinct_non_null_categories(): void
    {
        $brand = $this->makeBrand();
        $this->makeProduct($brand, ['name' => 'a', 'normalized_name' => 'a', 'category' => 'Τυριά']);
        $this->makeProduct($brand, ['name' => 'b', 'normalized_name' => 'b', 'category' => 'Τυριά']);
        $this->makeProduct($brand, ['name' => 'c', 'normalized_name' => 'c', 'category' => 'Ψωμί']);
        $this->makeProduct($brand, ['name' => 'd', 'normalized_name' => 'd', 'category' => null]);

        $response = $this->getJson('/api/public/v1/categories')->assertOk();

        $names = array_column($response->json('data'), 'name');
        $this->assertCount(2, $names);
        $this->assertContains('Τυριά', $names);
        $this->assertContains('Ψωμί', $names);
    }

    public function test_inactive_brand_categories_excluded(): void
    {
        $active = $this->makeBrand(['slug' => 'ab']);
        $inactive = $this->makeBrand(['slug' => 'sklav', 'website_url' => 'https://sklav', 'active' => false]);
        $this->makeProduct($active, ['name' => 'a', 'normalized_name' => 'a', 'category' => 'Active-Cat']);
        $this->makeProduct($inactive, ['name' => 'b', 'normalized_name' => 'b', 'category' => 'Hidden-Cat']);

        $response = $this->getJson('/api/public/v1/categories')->assertOk();

        $names = array_column($response->json('data'), 'name');
        $this->assertContains('Active-Cat', $names);
        $this->assertNotContains('Hidden-Cat', $names);
    }

    public function test_categories_are_cached(): void
    {
        $brand = $this->makeBrand();
        $this->makeProduct($brand, ['name' => 'a', 'normalized_name' => 'a', 'category' => 'Cat-1']);

        // First call populates cache.
        $first = $this->getJson('/api/public/v1/categories')->assertOk();
        $this->assertCount(1, $first->json('data'));

        // Add a new category after the cache populated. A non-cached
        // implementation would surface it; a cached one will not.
        $this->makeProduct($brand, ['name' => 'b', 'normalized_name' => 'b', 'category' => 'Cat-2']);

        $second = $this->getJson('/api/public/v1/categories')->assertOk();
        $this->assertCount(1, $second->json('data'), 'Second call should hit the cache.');

        // Bust cache; freshly added value should now appear.
        Cache::forget(CategoryController::CACHE_KEY);
        $third = $this->getJson('/api/public/v1/categories')->assertOk();
        $this->assertCount(2, $third->json('data'));
    }
}
