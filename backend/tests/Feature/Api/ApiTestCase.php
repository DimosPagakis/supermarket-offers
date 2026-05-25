<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

abstract class ApiTestCase extends TestCase
{
    use RefreshDatabase;

    protected function authedAsCrawler(array $abilities = ['crawler:write']): User
    {
        $user = User::factory()->create([
            'email' => 'crawler-test@system.local',
            'name' => 'Crawler Test',
        ]);

        Sanctum::actingAs($user, $abilities);

        return $user;
    }
}
