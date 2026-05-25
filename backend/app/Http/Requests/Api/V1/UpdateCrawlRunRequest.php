<?php

namespace App\Http\Requests\Api\V1;

use App\Models\CrawlRun;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateCrawlRunRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /**
     * Shape rules for marking a run finished.
     *
     * Business invariants enforced via withValidator() below:
     *  - The run being patched must currently be in `running` state.
     *    Once a run reaches a terminal status (success/failed/partial)
     *    it's immutable — preserves an honest audit trail.
     *  - offers_persisted (when present) must not exceed offers_found.
     *    A crawler can persist fewer than it found (network errors,
     *    backend 4xx on individual batches), but never more.
     */
    public function rules(): array
    {
        return [
            'status' => ['required', 'string', Rule::in(CrawlRun::TERMINAL_STATUSES)],
            'offers_found' => ['required', 'integer', 'min:0'],
            'offers_persisted' => ['nullable', 'integer', 'min:0'],
            'error_message' => ['nullable', 'string', 'max:5000'],
        ];
    }

    public function withValidator(Validator $validator): void
    {
        $validator->after(function (Validator $v): void {
            $run = $this->route('run');

            if ($run instanceof CrawlRun && $run->status !== CrawlRun::STATUS_RUNNING) {
                $v->errors()->add(
                    'run',
                    "Cannot update a crawl run in terminal status '{$run->status}'. Runs are immutable once finished.",
                );
            }

            $found = $this->input('offers_found');
            $persisted = $this->input('offers_persisted');
            if (is_numeric($found) && is_numeric($persisted) && (int) $persisted > (int) $found) {
                $v->errors()->add(
                    'offers_persisted',
                    'offers_persisted cannot exceed offers_found.',
                );
            }
        });
    }
}
