## Configuration

## Generate a key
https://git.example.com/profile/personal_access_tokens
Create a key with `sudo` and `api` scopes.

- File: `config/global/gitlab.ini`:

```ini
[gitlab]
url = https://git.example.com/
key = AnAPIKeyThatHasAdminRights
hook_port = 4069
```

- File: `config/discussion@muc.foo.bar/gitlab.ini`:

```ini
[projects]
eijebong/toto = 
```

The bot will listen on `127.0.0.1:4069` for webhooks. Currently, only commit, MR,
issues and jobs webhooks are supported.


## Webhook creation
Webhooks are automatically created on the configuration of each repositories.

## Allow outbound requests
In https://git.example.com/admin/application_settings allow:

`Allow requests to the local network from hooks and services`

## Key management

To be able to open issues via the bot, one must send it an API key. To do that,
open a private conversation MUC-PM with the bot and send it `!gitlab_key yourKey`.
