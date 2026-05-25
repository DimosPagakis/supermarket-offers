<?php

/*
|--------------------------------------------------------------------------
| Cross-Origin Resource Sharing (CORS) Configuration
|--------------------------------------------------------------------------
|
| The public read-API at /api/public/* must be reachable from arbitrary
| origins: our own Next.js frontend (different port locally), third-party
| developers, and ad-hoc curl clients. Allow all origins; the surface is
| read-only and throttled by IP.
|
| `sanctum/csrf-cookie` stays in the list so the internal /api/v1/* PAT
| flow keeps working unchanged (Sanctum SPA flow is unused today but the
| route is registered by the package).
|
*/

return [

    'paths' => ['api/*', 'api/public/*', 'sanctum/csrf-cookie'],

    'allowed_methods' => ['*'],

    'allowed_origins' => ['*'],

    'allowed_origins_patterns' => [],

    'allowed_headers' => ['*'],

    'exposed_headers' => [],

    'max_age' => 0,

    'supports_credentials' => false,

];
