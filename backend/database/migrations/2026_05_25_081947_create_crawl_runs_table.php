<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('crawl_runs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('brand_id')->constrained()->cascadeOnDelete();
            $table->timestamp('started_at');
            $table->timestamp('finished_at')->nullable();
            $table->string('status')->default('running'); // running | success | failed | partial
            $table->unsignedInteger('offers_found')->default(0);
            $table->unsignedInteger('offers_persisted')->default(0);
            $table->text('error_message')->nullable();
            $table->string('triggered_by')->default('schedule'); // schedule | manual | api
            $table->timestamps();

            $table->index(['brand_id', 'status']);
            $table->index('finished_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('crawl_runs');
    }
};
