<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('offers', function (Blueprint $table) {
            $table->id();
            $table->foreignId('product_id')->constrained()->cascadeOnDelete();
            $table->foreignId('crawl_run_id')->nullable()->constrained()->nullOnDelete();
            $table->decimal('price', 10, 2);
            $table->decimal('original_price', 10, 2)->nullable();
            $table->unsignedTinyInteger('discount_pct')->nullable();
            $table->string('currency', 3)->default('EUR');
            $table->date('valid_from')->nullable();
            $table->date('valid_to')->nullable();
            $table->timestamp('scraped_at');
            $table->timestamps();

            $table->index(['product_id', 'scraped_at']);
            $table->index(['valid_from', 'valid_to']);
            $table->index('scraped_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('offers');
    }
};
