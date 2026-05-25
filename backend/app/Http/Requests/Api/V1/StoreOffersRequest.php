<?php

namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;

class StoreOffersRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

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
            'offers.*.currency' => ['nullable', 'string', 'size:3'],
            'offers.*.valid_from' => ['nullable', 'date_format:Y-m-d'],
            'offers.*.valid_to' => ['nullable', 'date_format:Y-m-d'],
            'offers.*.scraped_at' => ['required', 'date'],
        ];
    }
}
