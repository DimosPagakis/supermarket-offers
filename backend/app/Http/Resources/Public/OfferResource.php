<?php

namespace App\Http\Resources\Public;

use App\Models\Offer;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Http\Resources\Json\ResourceCollection;
use Illuminate\Pagination\AbstractPaginator;

/**
 * Public-API offer shape.
 *
 * Internal fields (crawl_run_id, offers_persisted, timestamps that
 * leak ingestion-time information) are intentionally absent — the
 * public surface exposes only domain-meaningful columns.
 *
 * The optional price-history array is attached by the controller when
 * ?include_history=true is passed to the show endpoint. It is keyed
 * under `history` and is an array of compact { price, original_price,
 * discount_pct, scraped_at } tuples ordered scraped_at desc.
 *
 * @mixin Offer
 */
class OfferResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $data = [
            'id' => (int) $this->id,
            'price' => $this->price !== null ? (float) $this->price : null,
            'original_price' => $this->original_price !== null ? (float) $this->original_price : null,
            'discount_pct' => $this->discount_pct !== null ? (int) $this->discount_pct : null,
            'promo_label' => $this->promo_label,
            'promo_type' => $this->promo_type,
            'currency' => $this->currency,
            'valid_from' => $this->valid_from?->format('Y-m-d'),
            'valid_to' => $this->valid_to?->format('Y-m-d'),
            'scraped_at' => $this->scraped_at?->toIso8601String(),
            'product' => $this->relationLoaded('product') && $this->product
                ? new ProductResource($this->product)
                : null,
            'brand' => $this->relationLoaded('product') && $this->product?->relationLoaded('brand') && $this->product?->brand
                ? new BrandResource($this->product->brand)
                : null,
        ];

        if (isset($this->additional_history)) {
            $data['history'] = $this->additional_history;
        }

        return $data;
    }

    /**
     * Use a custom collection class so the paginated response surfaces a
     * `self` link alongside the framework-generated first/last/next/prev.
     */
    public static function collection($resource)
    {
        return new OfferResourceCollection($resource, static::class);
    }
}

/**
 * Public-API paginator wrapper that injects a `self` link into the
 * standard `{first, last, prev, next}` block. Defined in the same file
 * because it's an implementation detail of OfferResource.
 */
class OfferResourceCollection extends ResourceCollection
{
    public $collects = OfferResource::class;

    public function __construct($resource, ?string $collects = null)
    {
        parent::__construct($resource);

        if ($collects !== null) {
            $this->collects = $collects;
        }
    }

    public function paginationInformation($request, $paginated, $default)
    {
        $self = $request->getQueryString()
            ? $request->url().'?'.$request->getQueryString()
            : $request->url();

        $default['links']['self'] = $self;

        return $default;
    }
}

