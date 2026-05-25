<?php

namespace App\Http\Requests\Api\V1;

use App\Domain\Canonical\MatchMethod;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/**
 * Shape rules for POST /api/v1/canonical-products/bulk-upsert.
 *
 * Each grouping is one canonical product + the products that belong to
 * it. The endpoint is idempotent — the controller upserts by
 * `canonical_key` and skips lower-confidence overwrites of existing
 * product assignments.
 *
 * Per-grouping member limit (200) is generous enough that even a chain
 * with multiple sizes-per-SKU listed under one canonical lands fine, and
 * tight enough that a runaway payload from the canonicaliser can't blow
 * up a single transaction.
 */
class BulkUpsertCanonicalProductsRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'groupings' => ['required', 'array', 'min:1', 'max:500'],
            'groupings.*.canonical_key' => ['required', 'string', 'max:255'],
            'groupings.*.manufacturer_brand' => ['required', 'string', 'max:255'],
            'groupings.*.size_value' => ['nullable', 'numeric', 'min:0'],
            'groupings.*.size_unit' => ['nullable', 'string', 'max:16'],
            'groupings.*.pack_count' => ['nullable', 'integer', 'min:1', 'max:1000'],
            'groupings.*.variant_descriptor' => ['nullable', 'string', 'max:255'],
            'groupings.*.display_name' => ['required', 'string', 'max:500'],
            'groupings.*.category' => ['nullable', 'string', 'max:255'],
            'groupings.*.image_url' => ['nullable', 'string', 'max:2048'],

            'groupings.*.members' => ['required', 'array', 'min:1', 'max:200'],
            'groupings.*.members.*.product_id' => ['required', 'integer', 'min:1'],
            'groupings.*.members.*.confidence' => ['required', 'numeric', 'min:0', 'max:1'],
            'groupings.*.members.*.match_method' => [
                'required',
                Rule::enum(MatchMethod::class),
            ],
        ];
    }
}
