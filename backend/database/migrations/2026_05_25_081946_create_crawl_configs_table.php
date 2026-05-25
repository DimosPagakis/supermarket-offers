<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('crawl_configs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('brand_id')->unique()->constrained()->cascadeOnDelete();
            $table->string('strategy')->default('scrapy'); // scrapy | playwright | http_api
            $table->string('start_url');
            $table->unsignedInteger('rate_limit_ms')->default(2000);
            $table->boolean('respect_robots_txt')->default(true);
            $table->unsignedInteger('cache_ttl_seconds')->default(86400);
            $table->string('schedule_cron')->default('0 6 * * *'); // daily 06:00
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('crawl_configs');
    }
};
