<?php

namespace App\Http\Requests\Concerns;

use Illuminate\Contracts\Validation\Validator;

/**
 * Reject query-string keys that aren't whitelisted by rules().
 *
 * The public read API surfaces a fixed set of filters per endpoint; a
 * caller passing an unknown key is either a typo on their side or a
 * deprecated parameter on ours. Failing fast with a 422 catches both
 * cases before they silently degrade to "no filter applied".
 *
 * Hosting FormRequests must wire this trait into withValidator():
 *
 *   public function withValidator(Validator $validator): void
 *   {
 *       $this->rejectUnknownQueryParams($validator);
 *   }
 */
trait RejectsUnknownQueryParams
{
    protected function rejectUnknownQueryParams(Validator $validator): void
    {
        $validator->after(function (Validator $v): void {
            $allowed = array_keys($this->rules());
            foreach (array_diff(array_keys($this->query()), $allowed) as $key) {
                $v->errors()->add($key, "Unknown query parameter '{$key}'.");
            }
        });
    }
}
