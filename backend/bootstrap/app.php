<?php

use Illuminate\Console\Scheduling\Schedule;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Laravel\Sanctum\Http\Middleware\CheckAbilities;
use Laravel\Sanctum\Http\Middleware\CheckForAnyAbility;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->alias([
            'abilities' => CheckAbilities::class,
            'ability' => CheckForAnyAbility::class,
        ]);
    })
    ->withSchedule(function (Schedule $schedule): void {
        // MVP: read brand schedules straight from the DB at boot. Each active
        // brand with a crawl_config.schedule_cron gets its own scheduled
        // dispatch. This means `php artisan schedule:*` hits the DB on every
        // tick — fine for five brands. Revisit when we go multi-tenant or
        // when boot-time DB reads become a cold-start problem.
        //
        // Guarded so artisan still works on a fresh checkout where the DB
        // hasn't been migrated yet (e.g. `php artisan key:generate` during
        // first-time setup).
        try {
            if (! \Illuminate\Support\Facades\Schema::hasTable('brands')) {
                return;
            }
        } catch (\Throwable $e) {
            return;
        }

        $brands = \App\Models\Brand::query()
            ->where('active', true)
            ->with('crawlConfig')
            ->get();

        foreach ($brands as $brand) {
            $cron = $brand->crawlConfig?->schedule_cron;
            if (! $cron) {
                continue;
            }

            $schedule->command('crawler:dispatch', [
                $brand->slug,
                '--triggered-by=schedule',
            ])
                ->cron($cron)
                ->withoutOverlapping()
                ->name("crawler:dispatch:{$brand->slug}")
                ->appendOutputTo(storage_path('logs/scheduler.log'));
        }
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        //
    })->create();
