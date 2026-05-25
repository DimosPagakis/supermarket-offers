<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Mailgun, Postmark, AWS and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Crawler (Scrapy) subprocess
    |--------------------------------------------------------------------------
    |
    | Configuration for the Python crawler that the `crawler:dispatch` command
    | shells out to. Paths default relative to the backend's base path so a
    | fresh clone "just works" with the sibling `crawler/` checkout.
    |
    */
    'crawler' => [
        // Filesystem path to the crawler project (where `scrapy.cfg` lives).
        'path' => env('CRAWLER_PATH', base_path('../crawler')),
        // Python interpreter to use — typically the project venv.
        'python' => env('CRAWLER_PYTHON', '.venv/bin/python'),
        // URL the crawler should POST/PATCH back to.
        'backend_url' => env('CRAWLER_BACKEND_URL', 'http://127.0.0.1:8001'),
        // Sanctum bearer token with `crawler:write` ability.
        'backend_token' => env('CRAWLER_BACKEND_TOKEN'),
    ],

];
