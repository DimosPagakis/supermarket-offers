<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Str;

class CreateCrawlerTokenCommand extends Command
{
    protected $signature = 'crawler:token {name : A label for the token (e.g. local-dev, prod)}';

    protected $description = 'Issue a Sanctum personal access token for the crawler machine user (ability: crawler:write).';

    public const SYSTEM_EMAIL = 'crawler@system.local';

    public function handle(): int
    {
        $name = (string) $this->argument('name');

        $user = User::firstOrCreate(
            ['email' => self::SYSTEM_EMAIL],
            [
                'name' => 'Crawler System User',
                'password' => bcrypt(Str::random(64)),
            ],
        );

        $token = $user->createToken($name, ['crawler:write']);

        $this->info('Crawler token created. Store it safely — it will not be shown again.');
        $this->line('');
        $this->line($token->plainTextToken);

        return self::SUCCESS;
    }
}
