<?php

namespace App\Console\Commands;

use App\Models\Brand;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Process;

class CrawlerDispatchCommand extends Command
{
    protected $signature = 'crawler:dispatch
        {slug? : Brand slug to dispatch. Omit (or pass "all") to dispatch every active brand.}
        {--triggered-by=manual : Trigger source forwarded to the crawler (manual|schedule|...).}';

    protected $description = 'Spawn the Scrapy crawler subprocess for one or all active brands. Non-blocking.';

    /**
     * Per-spider dispatch timeout (seconds). Generous — a full AB crawl is
     * 3+ minutes today and we're about to lift caps. `Process::start()` is
     * non-blocking so this only bounds the eventual `wait()`.
     */
    private const DISPATCH_TIMEOUT_SECONDS = 1800;

    public function handle(): int
    {
        $slug = (string) ($this->argument('slug') ?? 'all');
        $triggeredBy = (string) $this->option('triggered-by');

        if ($slug === '' || $slug === 'all') {
            return $this->dispatchAll($triggeredBy);
        }

        $brand = Brand::where('slug', $slug)->first();

        if ($brand === null) {
            $this->error("Unknown brand slug: {$slug}");

            return self::FAILURE;
        }

        $result = $this->dispatchBrand($brand, $triggeredBy);

        return $result === 'failed' ? self::FAILURE : self::SUCCESS;
    }

    private function dispatchAll(string $triggeredBy): int
    {
        $brands = Brand::where('active', true)->orderBy('slug')->get();

        if ($brands->isEmpty()) {
            $this->warn('No active brands to dispatch.');

            return self::SUCCESS;
        }

        $anyFailure = false;
        foreach ($brands as $brand) {
            $result = $this->dispatchBrand($brand, $triggeredBy);
            if ($result === 'failed') {
                $anyFailure = true;
            }
        }

        return $anyFailure ? self::FAILURE : self::SUCCESS;
    }

    /**
     * @return 'started'|'skipped'|'failed'
     */
    private function dispatchBrand(Brand $brand, string $triggeredBy): string
    {
        if (! $brand->active) {
            Log::info('crawler:dispatch skipped inactive brand', [
                'slug' => $brand->slug,
            ]);
            $this->line(sprintf('%-15s skipped (inactive)', $brand->slug));

            return 'skipped';
        }

        $crawlerPath = (string) config('services.crawler.path');
        $python = (string) config('services.crawler.python');

        if (! is_dir($crawlerPath)) {
            Log::error('crawler:dispatch crawler path missing', [
                'slug' => $brand->slug,
                'path' => $crawlerPath,
            ]);
            $this->error(sprintf('%-15s failed (crawler path not found: %s)', $brand->slug, $crawlerPath));

            return 'failed';
        }

        $env = [
            'BACKEND_URL' => (string) config('services.crawler.backend_url'),
            'BACKEND_TOKEN' => (string) config('services.crawler.backend_token'),
            'TRIGGERED_BY' => $triggeredBy,
        ];

        try {
            $invoked = Process::path($crawlerPath)
                ->env($env)
                ->timeout(self::DISPATCH_TIMEOUT_SECONDS)
                ->forever()
                ->start([$python, '-m', 'scrapy', 'crawl', $brand->slug]);

            $pid = $invoked->id();

            Log::info('crawler:dispatch started spider', [
                'slug' => $brand->slug,
                'pid' => $pid,
                'triggered_by' => $triggeredBy,
                'path' => $crawlerPath,
            ]);

            $this->line(sprintf('%-15s started (pid=%s, triggered_by=%s)', $brand->slug, $pid ?? '?', $triggeredBy));

            return 'started';
        } catch (\Throwable $e) {
            Log::error('crawler:dispatch failed to start spider', [
                'slug' => $brand->slug,
                'error' => $e->getMessage(),
            ]);
            $this->error(sprintf('%-15s failed (%s)', $brand->slug, $e->getMessage()));

            return 'failed';
        }
    }
}
