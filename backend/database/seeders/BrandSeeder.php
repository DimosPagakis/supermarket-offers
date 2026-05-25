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
                // /search/promotions is the user-facing URL; the spider actually
                // talks to AB's GraphQL persisted-query endpoint at
                // https://www.ab.gr/api/v1/ (no Playwright needed).
                'start_url' => 'https://www.ab.gr/search/promotions',
                'strategy' => 'http_api',
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
                // Homepage is the most stable URL on the site. The spider walks
                // every "/c/<theme>-<YY>kw<WW>/a<id>" campaign anchor it finds
                // (weekly-selections + themed promos) and parses the JSON
                // payload that every campaign page embeds in `data-grid-data`
                // attributes. No flyer / PDF viewer involvement.
                'start_url' => 'https://www.lidl-hellas.gr/',
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
