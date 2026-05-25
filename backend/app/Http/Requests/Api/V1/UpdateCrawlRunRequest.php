<?php

namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;

class UpdateCrawlRunRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'status' => ['required', 'string', 'in:success,failed,partial'],
            'offers_found' => ['required', 'integer', 'min:0'],
            'offers_persisted' => ['nullable', 'integer', 'min:0'],
            'error_message' => ['nullable', 'string', 'max:5000'],
        ];
    }
}
