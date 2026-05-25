<?php

namespace Tests\Feature\Console;

use App\Models\Brand;
use App\Models\CrawlConfig;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Process\PendingProcess;
use Illuminate\Support\Facades\Process;
use Tests\TestCase;

class CrawlerDispatchCommandTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();

        // Point the crawler path at a directory we know exists so the
        // "crawler path missing" guard doesn't fire and short-circuit
        // dispatch. The backend's own base path is a convenient real dir.
        config()->set('services.crawler.path', base_path());
        config()->set('services.crawler.python', '.venv/bin/python');
        config()->set('services.crawler.backend_url', 'http://127.0.0.1:8001');
        config()->set('services.crawler.backend_token', 'test-token');

        Process::fake();
    }

    private function makeBrand(string $slug, bool $active = true, string $cron = '0 6 * * *'): Brand
    {
        $brand = Brand::create([
            'name' => ucfirst($slug),
            'slug' => $slug,
            'website_url' => "https://www.{$slug}.gr",
            'country_code' => 'GR',
            'active' => $active,
        ]);

        CrawlConfig::create([
            'brand_id' => $brand->id,
            'strategy' => 'scrapy',
            'start_url' => "https://www.{$slug}.gr/offers",
            'rate_limit_ms' => 2000,
            'respect_robots_txt' => true,
            'cache_ttl_seconds' => 86400,
            'schedule_cron' => $cron,
        ]);

        return $brand;
    }

    public function test_dispatch_by_slug_starts_process_with_expected_command_cwd_and_env(): void
    {
        $this->makeBrand('lidl');

        $this->artisan('crawler:dispatch', ['slug' => 'lidl'])
            ->assertSuccessful();

        Process::assertRan(function (PendingProcess $process, $result) {
            $command = $process->command;
            $this->assertIsArray($command);
            $this->assertSame(['.venv/bin/python', '-m', 'scrapy', 'crawl', 'lidl'], $command);
            $this->assertSame(base_path(), $process->path);
            $this->assertSame('http://127.0.0.1:8001', $process->environment['BACKEND_URL'] ?? null);
            $this->assertSame('test-token', $process->environment['BACKEND_TOKEN'] ?? null);
            $this->assertSame('manual', $process->environment['TRIGGERED_BY'] ?? null);

            return true;
        });
    }

    public function test_dispatch_unknown_slug_fails_gracefully(): void
    {
        $this->artisan('crawler:dispatch', ['slug' => 'nope'])
            ->expectsOutputToContain('Unknown brand slug: nope')
            ->assertFailed();

        Process::assertNothingRan();
    }

    public function test_dispatch_inactive_brand_is_skipped(): void
    {
        $this->makeBrand('sklavenitis', active: false);

        $this->artisan('crawler:dispatch', ['slug' => 'sklavenitis'])
            ->expectsOutputToContain('skipped (inactive)')
            ->assertSuccessful();

        Process::assertNothingRan();
    }

    public function test_triggered_by_schedule_is_passed_through(): void
    {
        $this->makeBrand('ab');

        $this->artisan('crawler:dispatch', [
            'slug' => 'ab',
            '--triggered-by' => 'schedule',
        ])->assertSuccessful();

        Process::assertRan(function (PendingProcess $process, $result) {
            return ($process->environment['TRIGGERED_BY'] ?? null) === 'schedule'
                && is_array($process->command)
                && in_array('ab', $process->command, true);
        });
    }

    public function test_dispatch_all_dispatches_every_active_brand_exactly_once(): void
    {
        $this->makeBrand('ab');
        $this->makeBrand('lidl');
        $this->makeBrand('masoutis');
        $this->makeBrand('sklavenitis', active: false);

        $this->artisan('crawler:dispatch')->assertSuccessful();

        $dispatchedSlugs = [];
        Process::assertRan(function (PendingProcess $process, $result) use (&$dispatchedSlugs) {
            if (is_array($process->command)) {
                // last token is the spider slug
                $dispatchedSlugs[] = end($process->command);
            }

            return true;
        });

        sort($dispatchedSlugs);
        $this->assertSame(['ab', 'lidl', 'masoutis'], $dispatchedSlugs);
    }

    public function test_dispatch_all_with_explicit_all_argument_works(): void
    {
        $this->makeBrand('ab');
        $this->makeBrand('lidl');

        $this->artisan('crawler:dispatch', ['slug' => 'all'])->assertSuccessful();

        $dispatchedSlugs = [];
        Process::assertRan(function (PendingProcess $process, $result) use (&$dispatchedSlugs) {
            if (is_array($process->command)) {
                $dispatchedSlugs[] = end($process->command);
            }

            return true;
        });

        sort($dispatchedSlugs);
        $this->assertSame(['ab', 'lidl'], $dispatchedSlugs);
    }

    public function test_dispatch_fails_if_crawler_path_does_not_exist(): void
    {
        config()->set('services.crawler.path', '/nonexistent/path/that/should/not/exist');
        $this->makeBrand('lidl');

        $this->artisan('crawler:dispatch', ['slug' => 'lidl'])
            ->expectsOutputToContain('failed (crawler path not found')
            ->assertFailed();

        Process::assertNothingRan();
    }
}
