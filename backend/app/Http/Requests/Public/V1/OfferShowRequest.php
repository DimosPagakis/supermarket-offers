<?php

namespace App\Http\Requests\Public\V1;

use Illuminate\Foundation\Http\FormRequest;

class OfferShowRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'include_history' => ['sometimes', 'in:0,1,true,false,TRUE,FALSE,yes,no'],
        ];
    }
}
