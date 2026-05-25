<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('products', function (Blueprint $table) {
            $table->id();
            $table->foreignId('brand_id')->constrained()->cascadeOnDelete();
            $table->string('external_id')->nullable(); // brand's own product ID if available
            $table->string('name');
            $table->string('normalized_name')->nullable(); // lower, no accents, for matching
            $table->string('url')->nullable();
            $table->string('image_url')->nullable();
            $table->string('category')->nullable();
            $table->string('unit')->nullable(); // kg | l | pcs | etc.
            // Future: canonical product unification across brands
            $table->foreignId('canonical_product_id')->nullable();
            $table->timestamps();

            $table->unique(['brand_id', 'external_id']);
            $table->index('normalized_name');
            $table->index('canonical_product_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('products');
    }
};
