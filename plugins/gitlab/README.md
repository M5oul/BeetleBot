## Configuration

File: `config/global/gitlab.ini`

```ini
[gitlab]
url = https://git.example.com/
key = AnAPIKeyThatHasAdminRights
hook_port = 4069
```

File: `config/discussion@muc.foo.bar`

```ini
[projects]
eijebong/toto = 
```

The bot will listen on 127.0.0.1:4069 for webhooks. Currently, only commit, MR,
issues and jobs webhooks are supported.

## Key management

To be able to open issues via the bot, one must send it an API key. To do that,
open a private conversation with the bot and send it `!gitlab_key yourKey`.
