# Configuring mwn

## System Requirements
 - Node.js v14+
 - mwn v3.0+  [Link](https://www.npmjs.com/package/mwn)

## Installation & Configuration

### Node.js
 - Follow the steps detailed on [the official download page of Node.js](https://nodejs.org/en/download).
 - You can check if Node.js is installed correctly by running the following command:
 
 ```sh
 node -v
 ```

### mwn
 - Navigate to `mwn/` (or any other directory containing the mwn scripts and the file `package.json`). Run the command `npm install` to install the required Node.js packages.
 - Configure your wiki account's authentication details by following the steps on [#Setting credentials](#setting-credentials).
 - To run the mwn script, run the following command:
 
 ```sh
 node --env-file=.env <name of script>
 ```

### Setting credentials
Create a file `profiles.json` in the folder `credentials/`.
```json
{
  "live": {
    "apiEntrypoint": "https://vocaloidlyrics.miraheze.org/w/api.php",
    // if logging in using OAuth
    "oauthToken": "...",
    // if logging in using BotPasswords
    "botUsername": "<USER NAME>@<BOT NAME>",
    "botPassword": "...",
    // User-Agent
    "botUseragent": "..."
  }
}
```

Alternatively, set your credentials by creating the following .env file in the folder `mwn/`:
```sh
WIKI_API_URL=https://vocaloidlyrics.miraheze.org/w/api.php
# if logging in using OAuth
BOT_OAUTH_ACCESS_TOKEN=
# if logging in using BotPasswords
BOT_USERNAME=
BOT_PASSWORD=
# User-Agent
BOT_USERAGENT=
```

By default, the bot will try to login and make changes to the wiki with the profile name `live` on the file `profiles.json`. If such a profile is not found, it will login using credentials set in .env or in the environment variables. To get the bot to login to another wiki profile, set the environment variable `PROFILE`:
```sh
PROFILE=dev
```  

## List of scripts
### Producer Page Discography Auto-Updater

This script is used to update discography tables in the producer pages in the VOCALOID Lyrics Wiki in bulk (requires the file `mwn/producer_page_bot_utils.ts`).

To run:

```sh
# synonymous with node --env-file=.env producer_page_bot.ts
npm run producer

# Update single page
npm run producer -- --page="<PAGE>"

# Update pages alphabetically, starting from the given string
npm run producer -- --from="<STRING>"
```

### Song Pages Exporter

This script is used to export song pages from the Vocaloid Lyrics Wiki in the form of an XML dump. The resulting XML dump will be divided into several pages containing 5000 (for users with `bot` rights) or 500 (others) wikipages each.

Add the following environment variable in .env:
```sh
EXPORT_DUMP_TO_DIRECTORY=path/to/output/folder
``` 

Run the script
```sh
node --env-file=.env export-songs.ts
```

### Templates Syncer

You can use this to copy Template:, Module:, and MediaWiki: pages between two wikis.

Create a file profiles.json containing the authentication details of at least two wikis (see profiles.EXAMPLE.json).

Run the script
```sh
# Example: Copy Template:, Module:, MediaWiki: pages from the "live" profile to the "dev" profile.
node template-sync.ts live dev

# Example: Only copy Template: & Module: pages from the "live" profile to the "dev" profile.
node template-sync.ts live dev --namespaces="Template, Module"
```

### Template Usage Statistics Logger

This script is used to log template & module usage statistics across the Vocaloid Lyrics Wiki.

Run the script
```sh
node template-usage.ts
```