<?php

namespace Tests\Feature\Api\Public\V1;

use Illuminate\Support\Facades\RateLimiter;

class ThrottleTest extends PublicApiTestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        // The throttle keys are derived from the route signature + IP.
        // Clear them between tests so a previous run doesn't poison this
        // one, and so this test starts with a fresh counter.
        RateLimiter::clear($this->throttleKeyForBrands());
        RateLimiter::clear($this->throttleKeyForCanonicalProducts());
    }

    protected function tearDown(): void
    {
        RateLimiter::clear($this->throttleKeyForBrands());
        RateLimiter::clear($this->throttleKeyForCanonicalProducts());
        parent::tearDown();
    }

    public function test_121st_request_returns_429(): void
    {
        $this->makeBrand();

        // 120 are allowed.
        for ($i = 0; $i < 120; $i++) {
            $this->getJson('/api/public/v1/brands')->assertOk();
        }

        // 121st within the same minute trips the throttle.
        $this->getJson('/api/public/v1/brands')->assertStatus(429);
    }

    public function test_canonical_products_endpoint_is_also_throttled(): void
    {
        // 120 are allowed.
        for ($i = 0; $i < 120; $i++) {
            $this->getJson('/api/public/v1/canonical-products')->assertOk();
        }

        // 121st trips the throttle.
        $this->getJson('/api/public/v1/canonical-products')->assertStatus(429);
    }

    /**
     * Mirrors the key Laravel's ThrottleRequests middleware computes for
     * a guest hitting our public route — sha1 of the route signature +
     * the client IP. Tests run with 127.0.0.1 by default.
     */
    private function throttleKeyForBrands(): string
    {
        return sha1('api/public/v1/brands|127.0.0.1');
    }

    private function throttleKeyForCanonicalProducts(): string
    {
        return sha1('api/public/v1/canonical-products|127.0.0.1');
    }
}
