<?php

namespace App\Http\Requests\Api\V1;

use App\Models\CrawlRun;
use App\Models\Offer;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreOffersRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Shape rules for the bulk push payload.
     *
     * Business invariants enforced via withValidator() below:
     *  - The route-bound CrawlRun must still be in the `running` state.
     *    Pushing offers to a terminal run (success/failed/partial) is a
     *    bug on the crawler side and we reject it loudly.
     *  - Per-offer valid_to must be on or after valid_from when both are
     *    present.
     *  - Every offer MUST carry at least one promo signal — a positive
     *    discount_pct, a non-null promo_label, or an original_price
     *    strictly above price. Defensive backstop: parsers are gated
     *    too, but a buggy parser must not be able to seed the chain
     *    catalogue into the public /offers feed. See backend CLAUDE.md.
     *
     * We deliberately keep the per-offer ruleset permissive about
     * external_id (nullable). Some chains expose stable SKUs, others
     * don't — the ProductResolver falls back to normalized_name when
     * external_id is null.
     */
    public function rules(): array
    {
        return [
            'offers' => ['required', 'array', 'min:1', 'max:500'],
            'offers.*.external_id' => ['nullable', 'string', 'max:255'],
            'offers.*.name' => ['required', 'string', 'max:500'],
            'offers.*.url' => ['nullable', 'string', 'max:2048'],
            'offers.*.image_url' => ['nullable', 'string', 'max:2048'],
            'offers.*.category' => ['nullable', 'string', 'max:255'],
            'offers.*.unit' => ['nullable', 'string', 'max:50'],
            'offers.*.price' => ['required', 'numeric', 'min:0'],
            'offers.*.original_price' => ['nullable', 'numeric', 'min:0'],
            'offers.*.discount_pct' => ['nullable', 'integer', 'min:0', 'max:100'],
            'offers.*.promo_label' => ['nullable', 'string', 'max:80'],
            'offers.*.promo_type' => ['nullable', 'string', 'max:32', Rule::in(Offer::PROMO_TYPES)],
            'offers.*.currency' => ['nullable', 'string', 'size:3'],
            'offers.*.valid_from' => ['nullable', 'date_format:Y-m-d'],
            'offers.*.valid_to' => ['nullable', 'date_format:Y-m-d'],
            'offers.*.scraped_at' => ['required', 'date'],
        ];
    }

    public function withValidator(Validator $validator): void
    {
        $validator->after(function (Validator $v): void {
            $run = $this->route('run');

            if ($run instanceof CrawlRun && $run->status !== CrawlRun::STATUS_RUNNING) {
                $v->errors()->add(
                    'run',
                    "Cannot push offers to a crawl run in status '{$run->status}'. Run must be 'running'.",
                );
            }

            // Per-offer date sanity + promo-signal requirement.
            $offers = $this->input('offers', []);
            if (! is_array($offers)) {
                return;
            }
            foreach ($offers as $i => $offer) {
                $from = $offer['valid_from'] ?? null;
                $to = $offer['valid_to'] ?? null;
                if ($from && $to && $to < $from) {
                    $v->errors()->add(
                        "offers.{$i}.valid_to",
                        'valid_to must be on or after valid_from.',
                    );
                }

                if (! $this->offerCarriesPromoSignal($offer)) {
                    $v->errors()->add(
                        "offers.{$i}",
                        'must carry a real promo signal (discount_pct>0, promo_label, or original_price>price).',
                    );
                }
            }
        });
    }

    /**
     * Return true iff an offer payload carries at least one observable
     * promo signal.
     *
     * Accepted signals (any one suffices):
     *  - `discount_pct` numeric and > 0,
     *  - `promo_label` non-null and non-blank (the brand-supplied pill
     *    text, e.g. "1+1 δώρο", "-30%", "ΠΡΟΣΦΟΡΑ"),
     *  - `original_price` numeric AND strictly > `price` (a real
     *    strikethrough — equal prices don't count).
     *
     * Defensive gate against catalogue-leak rows. Mirrors the per-brand
     * parser gates in `crawler/scraper/parsers/*.py`; documented in
     * backend/CLAUDE.md.
     */
    protected function offerCarriesPromoSignal(array $offer): bool
    {
        $discountPct = $offer['discount_pct'] ?? null;
        if (is_numeric($discountPct) && (int) $discountPct > 0) {
            return true;
        }

        $promoLabel = $offer['promo_label'] ?? null;
        if (is_string($promoLabel) && trim($promoLabel) !== '') {
            return true;
        }

        $price = $offer['price'] ?? null;
        $originalPrice = $offer['original_price'] ?? null;
        if (
            is_numeric($price)
            && is_numeric($originalPrice)
            && (float) $originalPrice > (float) $price
        ) {
            return true;
        }

        return false;
    }
}
