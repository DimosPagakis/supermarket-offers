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
                // Sklavenitis sits behind Akamai Bot Manager. Plain HTTP +
                // headless Chromium both 403 instantly because Akamai
                // fingerprints the TLS ClientHello. The spider sidesteps
                // that with curl_cffi Chrome JA3 impersonation (see
                // crawler/scraper/spiders/sklavenitis.py). Strategy is
                // labelled `http_api` because the fetch path is plain
                // HTTP (no Playwright); the trick is at the TLS layer.
                'start_url' => 'https://www.sklavenitis.gr/sylloges/prosfores/',
                'strategy' => 'http_api',
                // Seeded inactive (2026-05-25). The `/sylloges/prosfores`
                // URL is misnamed — it ships the chain's full catalogue,
                // not a weekly flyer. The only observable per-card promo
                // signal in the markup is the ``.sign-badges`` "N+M Δώρο"
                // badge, present on ~1 in 24 cards. We refuse to seed the
                // catalogue under the guise of "offers"; the brand will
                // stay inactive until a real flyer entry point is found
                // (or Sklavenitis adds strikethrough markup to the
                // listing). Flip back to `true` once that lands.
                'active' => false,
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
                    // Per-brand override; defaults active unless the
                    // entry explicitly sets `active => false` (e.g.
                    // Sklavenitis — see comment above).
                    'active' => $data['active'] ?? true,
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
