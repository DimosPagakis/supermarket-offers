<?php

namespace App\Http\Requests\Api\V1;

use App\Models\CrawlRun;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StartCrawlRunRequest extends FormRequest
{
    /**
     * Authorization is enforced upstream by the `auth:sanctum` +
     * `ability:crawler:write` middleware on the route group. Any caller
     * who reaches a FormRequest already holds a token with the right
     * ability, so per-request authorization stays open.
     */
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Validation rules.
     *
     * Business invariants enforced here (vs. just shape checks):
     *  - brand_id must reference a brand that is currently active.
     *    Crawling an inactive brand wastes work and can stomp on a
     *    deliberate operator decision to pause that chain.
     */
    public function rules(): array
    {
        return [
            'brand_id' => [
                'required',
                'integer',
                Rule::exists('brands', 'id')->where('active', true),
            ],
            'triggered_by' => ['required', 'string', Rule::in(CrawlRun::TRIGGER_SOURCES)],
        ];
    }

    public function messages(): array
    {
        return [
            'brand_id.exists' => 'Selected brand does not exist or is not active.',
        ];
    }
}
