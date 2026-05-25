<?php

namespace App\Http\Requests\Public\V1;

use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/**
 * Shape rules for GET /api/public/v1/canonical-products.
 *
 * Default `min_brands=2` filters out single-chain canonicals — the
 * comparison surface only makes sense when there's something to compare.
 * Callers can pass `min_brands=1` to opt back in (e.g. an admin view
 * inspecting un-merged candidates).
 */
class CanonicalProductIndexRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'q' => ['sometimes', 'string', 'max:255'],
            'brand' => ['sometimes', 'string', 'max:255'],
            'category' => ['sometimes', 'string', 'max:255'],
            'min_brands' => ['sometimes', 'integer', 'min:1', 'max:10'],
            'sort' => ['sometimes', Rule::in(['members_count', 'brands_count', 'display_name'])],
            'dir' => ['sometimes', Rule::in(['asc', 'desc'])],
            'page' => ['sometimes', 'integer', 'min:1'],
            'per_page' => ['sometimes', 'integer', 'min:1', 'max:100'],
        ];
    }

    public function withValidator(Validator $validator): void
    {
        $validator->after(function (Validator $v): void {
            $allowed = array_keys($this->rules());
            $extra = array_diff(array_keys($this->query()), $allowed);
            foreach ($extra as $key) {
                $v->errors()->add($key, "Unknown query parameter '{$key}'.");
            }
        });
    }
}
