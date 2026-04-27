# Custom Bot Scripts for Vocaloid Lyrics Wiki

This is an assortment of bot scripts for bulk editing in the VOCALOID Lyrics Wiki.

## System Requirements
### mwn scripts
 - Node.js v14+
 - mwn v3.0+  [Link](https://www.npmjs.com/package/mwn)
### pywikibot scripts (legacy, unmaintained)
 - Python 3.10+
 - Pywikibot 8.1+ [Link](https://www.mediawiki.org/wiki/Manual:Pywikibot)
 - Installed python packages:
   - [pip install aiohttp](https://pypi.org/project/aiohttp/)
   - [pip install regex](https://pypi.org/project/regex/)
   - [pip install mwparserfromhell](https://pypi.org/project/mwparserfromhell/)

## Installation & Configuration

### Node.js
 - Follow the steps detailed on [the official download page of Node.js](https://nodejs.org/en/download).
 - You can check if Node.js is installed correctly by running the following command:
 
 ```sh
 node -v
 ```

### mwn
 - Navigate to `mwn/` (or any other directory containing the mwn scripts and the file `package.json`). Run the command `npm install` to install the required Node.js packages.
 - Configure your wiki account's authentication details by copying `.env.EXAMPLE` into `.env` and filling in the bot username & password.
 - To run the mwn script, run the following command:
 
 ```sh
 node --env-file=.env <name of script>
 ```

### Python
 - Install the latest Python distributable from [www.python.org](https://www.python.org/downloads/).
 - When installing, be sure to check the Add Python to PATH option.
 - Otherwise you can manually add the Python distributable by following the steps detailed [here](https://www.javatpoint.com/how-to-set-python-path).
 - You can check if Python has been properly installed by opening the command prompt and running the following command:

  ```sh
  python --version
  ```

 - Install the required Python packages:
  
  ```sh
  pip install aiohttp
  pip install regex
  pip install mwparserfromhell
  ```

### Pywikibot
 - Download the latest stable version of Pywikibot from [Toolforge](https://pywikibot.toolforge.org).
 - Unzip the downloaded files to a folder of your own choosing. Open the command prompt and navigate to this folder.
 - Follow the steps detailed [on this page](https://www.mediawiki.org/wiki/Manual:Pywikibot/Installation#Configure_Pywikibot).
 - Finally run the following command to log in to your wiki:

  ```sh
  python pwb.py login
  ```
 
 - To use the scripts:
   - Download the scripts in this repository.
   - Copy the Python files into the /scripts/userscripts sub-folder in your Pywikibot folder.
   - To use each script, navigate to your Pywikibot directory and run the following command:

    ```sh
    python pwb.py <name of script>
    ```

## List of scripts

 - Producer Page Discography Auto-Updater (`mwn/producer_page_bot.ts`)
 - Song pages dump exporter (`mwn/export-songs.ts`)
 - Script to sync templates between wikis (`mwn/template-sync.ts`)
 - Basic script to list pages (`mwn/listpages.ts`)
 - Internal Wiki Link & Category Mover (`/pywikibot/vlw_editlinks.py`, legacy/unmaintained)

## Producer Page Discography Auto-Updater

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

## Song Pages Exporter

This script is used to export song pages from the Vocaloid Lyrics Wiki in the form of an XML dump. The resulting XML dump will be divided into several pages containing 5000 (for users with `bot` rights) or 500 (others) wikipages each.

Add the following environment variable in .env:
```sh
EXPORT_DUMP_TO_DIRECTORY=path/to/output/folder
``` 

Run the script
```sh
node --env-file=.env export-songs.ts
```

## Templates Syncer

You can use this to copy Template:, Module:, and MediaWiki: pages between two wikis.

Create a file profiles.json containing the authentication details of at least two wikis (see profiles.EXAMPLE.json).

Run the script
```sh
# Example: Copy Template:, Module:, MediaWiki: pages from the "live" profile to the "dev" profile.
node template-sync.ts live dev

# Example: Only copy Template: & Module: pages from the "live" profile to the "dev" profile.
node template-sync.ts live dev --namespaces="Template, Module"
```

## Internal Wiki Link and Category Mover Bot

The pwikibot script `vlw_editlinks.py` is used to update the internal wiki links and category tags in the VOCALOID Lyrics Wiki. This script is generally not used in lieu of Extension:ReplaceText.

### Moving producer category

```sh
python pwb.py vlw_editlinks -moveprodcat -old:"foo" -new:"bar" [-changelink] [-preserveoldname]
```

Edit the category tag of the producer, from [[Category:foo songs list]] -> [[Category:bar songs list]]

If this command is run with the optional flag `-changelink`, then the bot will also change the producer redirect links in the page.

    -old:"foo" -new:"bar":      [[foo]] -> [[bar]], [[Foo]] -> [[bar]]
    -old:"w1 w2" -new:"a1 a2":  [[w1 w2]] -> [[a1 a2]], [[w1_w2]] -> [[a1 a2]], [[W1 w2]] -> [[a1 a2]]

If this command is also run with the optional flag `-preserveoldname`, then the bot will keep the old name as the link text.

    -old:"foo" -new:"bar":      [[foo]] -> [[bar|foo]]

General tips:
 - If you only want to change the producer category tags, and want to keep the wiki links as they are, run...
  
        python pwb.py vlw_editlinks -moveprodcat -old:"..." -new:"..."

 - If you want to change the producer category tags and also change the producer links (usually to prevent double redirects), run...
    
        python pwb.py vlw_editlinks -moveprodcat -old:"MATERU" -new:"MARETU" -changelink
        python pwb.py vlw_editlinks -moveprodcat -old:"Hachi" -new:"Kenshi Yonezu" -changelink -preserveoldname

 - Usually `-changelink` is used to correct a mistyped producer's name and `-changelink -preserveoldname` is used when the producer is undergoing a name change.

### Moving singer category

Edit the category tag of the singer/vocal synth, from [[Category:Songs featuring foo]] -> [[Category:Songs featuring bar]]

    python pwb.py vlw_editlinks -movesingercat -old:"foo" -new:"bar"

### Moving internal wiki links

Edit internal wiki links that link to the page "foo" so that they will be linked to the page "bar" 

If linkcap is specified then the new wikilink will have the specified parameter as the link caption
    
    python pwb.py vlw_editlinks -old:"foo" -new:"bar" -linkcap:"text" -[page|category|file]:...
    
