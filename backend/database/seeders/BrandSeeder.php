<?php

namespace Database\Seeders;

use App\Models\Brand;
use App\Models\CrawlConfig;
use Illuminate\Database\Seeder;

class BrandSeeder extends Seeder
{
    public function run(): void
    {
        $brands = [
            [
                'name' => 'AB Vassilopoulos',
                'slug' => 'ab',
                'website_url' => 'https://www.ab.gr',
                // Site is fully JS-rendered. /search/promotions is the offers gateway —
                // requires browser execution to surface product listings.
                'start_url' => 'https://www.ab.gr/search/promotions',
                'strategy' => 'playwright',
            ],
            [
                'name' => 'Sklavenitis',
                'slug' => 'sklavenitis',
                'website_url' => 'https://www.sklavenitis.gr',
                // Bot-protected on plain HTTP fetches — use Playwright with realistic UA.
                'start_url' => 'https://www.sklavenitis.gr/sylloges/prosfores',
                'strategy' => 'playwright',
            ],
            [
                'name' => 'Lidl Hellas',
                'slug' => 'lidl',
                'website_url' => 'https://www.lidl-hellas.gr',
                // Stable flyer landing page. Spider parses current-week flyer link from here,
                // then follows. Avoids weekly seed updates (week-specific slugs change Thursdays).
                'start_url' => 'https://www.lidl-hellas.gr/c/fylladio-lidl/s10020481',
                'strategy' => 'scrapy',
            ],
            [
                'name' => 'My Market',
                'slug' => 'my-market',
                'website_url' => 'https://www.mymarket.gr',
                'start_url' => 'https://www.mymarket.gr/offers',
                'strategy' => 'scrapy',
            ],
            [
                'name' => 'Masoutis',
                'slug' => 'masoutis',
                'website_url' => 'https://www.masoutis.gr',
                // JS-rendered listing.
                'start_url' => 'https://www.masoutis.gr/categories/index/prosfores?item=0',
                'strategy' => 'playwright',
            ],
        ];

        foreach ($brands as $data) {
            $brand = Brand::updateOrCreate(
                ['slug' => $data['slug']],
                [
                    'name' => $data['name'],
                    'website_url' => $data['website_url'],
                    'country_code' => 'GR',
                    'active' => true,
                ],
            );

            CrawlConfig::updateOrCreate(
                ['brand_id' => $brand->id],
                [
                    'strategy' => $data['strategy'],
                    'start_url' => $data['start_url'],
                    'rate_limit_ms' => 2000,
                    'respect_robots_txt' => true,
                    'cache_ttl_seconds' => 86400,
                    'schedule_cron' => '0 6 * * *',
                ],
            );
        }
    }
}
