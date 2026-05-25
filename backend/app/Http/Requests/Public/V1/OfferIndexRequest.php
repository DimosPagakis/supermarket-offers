<?php

namespace App\Http\Requests\Public\V1;

use App\Http\Requests\Concerns\RejectsUnknownQueryParams;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/**
 * Shape rules for GET /api/public/v1/offers (and the brand-sugar and
 * /search aliases that reuse the same query string).
 *
 * Unknown query parameters are explicitly rejected so third-party
 * clients catch typos early instead of silently getting unfiltered
 * results.
 */
class OfferIndexRequest extends FormRequest
{
    use RejectsUnknownQueryParams;

    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'brand' => ['sometimes', 'string', 'max:255'],
            'category' => ['sometimes', 'string', 'max:255'],
            'min_discount' => ['sometimes', 'integer', 'min:0', 'max:100'],
            // Accept the loose set of truthy/falsy query-string values
            // a third-party caller might pass; we coerce via filter_var
            // downstream. Laravel's `boolean` rule rejects 'true'/'false'
            // strings which are common in URLs.
            'has_discount' => ['sometimes', 'in:0,1,true,false,TRUE,FALSE,yes,no'],
            'valid_on' => ['sometimes', 'date_format:Y-m-d'],
            'q' => ['sometimes', 'string', 'max:255'],
            'sort' => ['sometimes', Rule::in(['discount_pct', 'price', 'scraped_at'])],
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
