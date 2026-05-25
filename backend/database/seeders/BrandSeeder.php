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
                'start_url' => 'https://www.ab.gr/shop/discounts',
            ],
            [
                'name' => 'Sklavenitis',
                'slug' => 'sklavenitis',
                'website_url' => 'https://www.sklavenitis.gr',
                'start_url' => 'https://www.sklavenitis.gr/prosfores/',
            ],
            [
                'name' => 'Lidl Hellas',
                'slug' => 'lidl',
                'website_url' => 'https://www.lidl-hellas.gr',
                'start_url' => 'https://www.lidl-hellas.gr/c/prosfores-evdomadas/s10020863',
            ],
            [
                'name' => 'My Market',
                'slug' => 'my-market',
                'website_url' => 'https://www.mymarket.gr',
                'start_url' => 'https://www.mymarket.gr/offers',
            ],
            [
                'name' => 'Masoutis',
                'slug' => 'masoutis',
                'website_url' => 'https://www.masoutis.gr',
                'start_url' => 'https://www.masoutis.gr/prosfores',
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
                    'strategy' => 'scrapy',
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
