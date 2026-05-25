<?php

namespace Tests\Unit\Services;

use App\Services\VariantDescriber;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

/**
 * Pins {@see VariantDescriber} against a handful of real Greek product
 * names taken from the live `:8001` DB and the canonical-design doc.
 *
 * The descriptor we derive here is the family-browse identity — two
 * products that should land in the same family must yield identical
 * `(manufacturer_brand, size_value, size_unit, pack_count)` tuples,
 * irrespective of the chain's spelling/casing/punctuation quirks.
 */
class VariantDescriberTest extends TestCase
{
    /**
     * @return array<string, array{0: string, 1: array<string, mixed>}>
     */
    public static function realProductCases(): array
    {
        return [
            'Axe deodorant 150ml — Africa scent' => [
                'Axe Αποσμητικό Σπρέι Africa 150ml',
                [
                    'manufacturer_brand' => 'axe',
                    'size_value' => 150.0,
                    'size_unit' => 'ml',
                    'pack_count' => 1,
                    // Variant descriptor concatenates non-brand/size/pack
                    // tokens in deterministic ASCII order. The category
                    // words leak in here because the category isn't part
                    // of the name regex — that's by design, see ADR.
                    'variant_descriptor' => 'africa-aposmhtiko-sprei',
                ],
            ],
            'Axe deodorant 150ml — Marine scent' => [
                'Axe Αποσμητικό Σπρέι Marine 150ml',
                [
                    'manufacturer_brand' => 'axe',
                    'size_value' => 150.0,
                    'size_unit' => 'ml',
                    'pack_count' => 1,
                    'variant_descriptor' => 'aposmhtiko-marine-sprei',
                ],
            ],
            'Coca-Cola 1.5L (comma decimal)' => [
                'Coca-Cola 1,5lt',
                [
                    'manufacturer_brand' => 'coca-cola',
                    'size_value' => 1.5,
                    'size_unit' => 'l',
                    'pack_count' => 1,
                ],
            ],
            'Coca-Cola 6x330ml (sklavenitis casing)' => [
                'COCA-COLA Original Taste 6x330ml',
                [
                    'manufacturer_brand' => 'coca-cola',
                    'size_value' => 330.0,
                    'size_unit' => 'ml',
                    'pack_count' => 6,
                ],
            ],
            'Coca-Cola 5+1 Δώρο promo (collapses to 6-pack)' => [
                'COCA-COLA Original Taste 5x330ml +1 Δώρο',
                [
                    'manufacturer_brand' => 'coca-cola',
                    'size_value' => 330.0,
                    'size_unit' => 'ml',
                    'pack_count' => 6,
                ],
            ],
            'Melissa pasta 400g (gram alias)' => [
                'MELISSA Σπαγγέτι Χωρίς γλουτένη 400γρ.',
                [
                    'manufacturer_brand' => 'melissa',
                    'size_value' => 400.0,
                    'size_unit' => 'g',
                ],
            ],
            'My Gusto private label — no manufacturer' => [
                'My Gusto Πάριζα & Τυρί Gouda 280gr',
                [
                    'manufacturer_brand' => null,
                ],
            ],
            'AB Vassilopoulos own brand — no manufacturer' => [
                'AB Vassilopoulos Surimi Sticks 250g',
                [
                    'manufacturer_brand' => null,
                ],
            ],
            'Schwarzkopf Palette hair dye (descriptor stays)' => [
                'Schwarzkopf Palette Νο 4-0 Καστανό',
                [
                    'manufacturer_brand' => 'schwarzkopf',
                ],
            ],
            'Ariel Pods 29-pack' => [
                'Ariel All-in-1 Pods Original 29τεμ',
                [
                    'manufacturer_brand' => 'ariel',
                ],
            ],
            'Lacta chocolate 100g' => [
                'Lacta Σοκολάτα Γάλακτος 100γρ',
                [
                    'manufacturer_brand' => 'lacta',
                    'size_value' => 100.0,
                    'size_unit' => 'g',
                    'pack_count' => 1,
                ],
            ],
            'Nirvana ice cream — volume beats weight' => [
                'NIRVANA Παγωτό Brownies & Salted Caramel 302g (420ml)',
                [
                    'manufacturer_brand' => 'nirvana',
                    'size_value' => 420.0,
                    'size_unit' => 'ml',
                ],
            ],
        ];
    }

    #[DataProvider('realProductCases')]
    public function test_extracts_features_from_real_names(string $name, array $expected): void
    {
        $describer = new VariantDescriber();
        $features = $describer->extract($name, null);

        foreach ($expected as $key => $value) {
            if (is_float($value)) {
                $this->assertEqualsWithDelta(
                    $value,
                    $features[$key],
                    0.001,
                    "Mismatch on `{$key}` for: {$name}",
                );

                continue;
            }
            $this->assertSame(
                $value,
                $features[$key],
                "Mismatch on `{$key}` for: {$name}",
            );
        }
    }

    public function test_category_is_accent_folded(): void
    {
        $describer = new VariantDescriber();
        $features = $describer->extract('Axe Σπρέι Marine 150ml', 'Αποσμητικά Σώματος');

        $this->assertSame('αποσμητικα σωματος', $features['category_normalised']);
    }

    public function test_empty_name_yields_safe_defaults(): void
    {
        $features = (new VariantDescriber())->extract('', null);

        $this->assertNull($features['manufacturer_brand']);
        $this->assertNull($features['size_value']);
        $this->assertNull($features['size_unit']);
        $this->assertSame(1, $features['pack_count']);
        $this->assertNull($features['variant_descriptor']);
    }

    public function test_two_axe_scents_share_size_and_brand_but_differ_on_descriptor(): void
    {
        $d = new VariantDescriber();
        $a = $d->extract('Axe Αποσμητικό Σπρέι Africa 150ml');
        $b = $d->extract('Axe Αποσμητικό Σπρέι Marine 150ml');

        $this->assertSame($a['manufacturer_brand'], $b['manufacturer_brand']);
        $this->assertSame($a['size_value'], $b['size_value']);
        $this->assertSame($a['size_unit'], $b['size_unit']);
        $this->assertSame($a['pack_count'], $b['pack_count']);
        $this->assertNotSame($a['variant_descriptor'], $b['variant_descriptor']);
    }
}
