<?php

namespace App\Console\Commands;

use App\Models\Product;
use App\Services\VariantDescriber;
use Illuminate\Console\Command;

/**
 * One-shot backfill that populates the family-browse feature columns
 * (`manufacturer_brand`, `category_normalised`, `size_value`,
 * `size_unit`, `pack_count`, `variant_descriptor`) on every existing
 * `products` row.
 *
 * Going forward {@see \App\Services\ProductResolver} writes these
 * columns on every find-or-create, so this command only needs to run
 * once per environment to fill the rows that pre-date the migration.
 *
 * Idempotent: re-running rewrites the same values. Safe to ship in a
 * deploy hook.
 *
 * The command prints a small summary to stdout: how many products
 * received a `manufacturer_brand`, and how many distinct families
 * emerged. That's the "did the backfill find any signal in the DB"
 * sanity check the task brief asks for.
 */
class EnrichProductFeaturesCommand extends Command
{
    protected $signature = 'products:enrich-features {--chunk=500 : Number of products to process per chunk}';

    protected $description = 'Backfill family-browse feature columns on `products` (manufacturer_brand, size, pack, variant_descriptor).';

    public function handle(VariantDescriber $describer): int
    {
        $chunk = max(1, (int) $this->option('chunk'));
        $touched = 0;
        $brandPopulated = 0;
        $sizePopulated = 0;

        $total = Product::query()->count();
        $this->info("Enriching features for {$total} products (chunk={$chunk})…");

        $bar = $this->output->createProgressBar($total);
        $bar->start();

        Product::query()->orderBy('id')->chunkById($chunk, function ($products) use ($describer, &$touched, &$brandPopulated, &$sizePopulated, $bar): void {
            foreach ($products as $product) {
                $features = $describer->extract((string) $product->name, $product->category);

                $product->manufacturer_brand = $features['manufacturer_brand'];
                $product->category_normalised = $features['category_normalised'];
                $product->size_value = $features['size_value'];
                $product->size_unit = $features['size_unit'];
                $product->pack_count = $features['pack_count'];
                $product->variant_descriptor = $features['variant_descriptor'];
                $product->save();

                $touched++;
                if ($features['manufacturer_brand'] !== null) {
                    $brandPopulated++;
                }
                if ($features['size_value'] !== null) {
                    $sizePopulated++;
                }
                $bar->advance();
            }
        });

        $bar->finish();
        $this->newLine(2);

        $familyCount = Product::query()
            ->whereNotNull('manufacturer_brand')
            ->whereNotNull('size_value')
            ->whereNotNull('size_unit')
            ->distinct()
            ->count(\Illuminate\Support\Facades\DB::raw(
                'manufacturer_brand || \'|\' || category_normalised || \'|\' || size_value || \'|\' || size_unit || \'|\' || pack_count'
            ));

        $this->info("Processed:           {$touched}");
        $this->info("Brand populated:     {$brandPopulated}");
        $this->info("Size populated:      {$sizePopulated}");
        $this->info("Distinct families:   {$familyCount}");

        return self::SUCCESS;
    }
}
