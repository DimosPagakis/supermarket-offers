<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('brands', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('slug')->unique();
            $table->string('website_url');
            $table->string('country_code', 2)->default('GR'); // ISO 3166-1 alpha-2
            $table->boolean('active')->default(true);
            $table->timestamps();

            $table->index('active');
            $table->index('country_code');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('brands');
    }
};
