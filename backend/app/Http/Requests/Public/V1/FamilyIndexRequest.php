<?php

namespace App\Http\Requests\Public\V1;

use App\Http\Requests\Concerns\RejectsUnknownQueryParams;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/**
 * Shape rules for GET /api/public/v1/families.
 *
 * `min_variants` defaults to 2 because a "family" with a single member
 * SKU is the same answer as the standard `/offers` feed — the family
 * surface only earns its keep when there's something to browse. Callers
 * can opt back into singletons with `min_variants=1`.
 *
 * `sort` accepts the family-specific dimensions (variants_count,
 * brands_count) plus the price dimensions for "show me the cheapest
 * family on offer" style queries.
 */
class FamilyIndexRequest extends FormRequest
{
    use RejectsUnknownQueryParams;

    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'q' => ['sometimes', 'string', 'max:255'],
            'brand' => ['sometimes', 'string', 'max:255'],
            'manufacturer' => ['sometimes', 'string', 'max:255'],
            'category' => ['sometimes', 'string', 'max:255'],
            'min_variants' => ['sometimes', 'integer', 'min:1', 'max:200'],
            'min_brands' => ['sometimes', 'integer', 'min:1', 'max:10'],
            'sort' => ['sometimes', Rule::in(['variants_count', 'brands_count', 'min_price', 'avg_price'])],
            'dir' => ['sometimes', Rule::in(['asc', 'desc'])],
            'page' => ['sometimes', 'integer', 'min:1'],
            'per_page' => ['sometimes', 'integer', 'min:1', 'max:100'],
        ];
    }

    public function withValidator(Validator $validator): void
    {
        $this->rejectUnknownQueryParams($validator);
    }
}
