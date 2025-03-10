# Custom Bot Scripts for Vocaloid Lyrics Wiki

This is an assortment of bot scripts for bulk editing in the VOCALOID Lyrics Wiki.

## System Requirements
 - Python 3.10+
 - Pywikibot 8.1+
 - Installed python packages:
   - [pip install aiohttp](https://pypi.org/project/aiohttp/)
   - [pip install regex](https://pypi.org/project/regex/)
   - [pip install mwparserfromhell](https://pypi.org/project/mwparserfromhell/)

## Table of Contents
- [Custom Bot Scripts for Vocaloid Lyrics Wiki](#custom-bot-scripts-for-vocaloid-lyrics-wiki)
  - [System Requirements](#system-requirements)
  - [Table of Contents](#table-of-contents)
  - [Installation \& Configuration](#installation--configuration)
    - [Python](#python)
    - [Pywikibot](#pywikibot)
    - [Scripts](#scripts)
  - [Producer Page Discography Auto-Updater](#producer-page-discography-auto-updater)
  - [Producer Page Link Checker](#producer-page-link-checker)
  - [Internal Wiki Link and Category Mover Bot](#internal-wiki-link-and-category-mover-bot)
    - [Moving producer category](#moving-producer-category)
    - [Moving singer category](#moving-singer-category)
    - [Moving internal wiki links](#moving-internal-wiki-links)



## Installation & Configuration

### Python
 - Install the latest Python distributable from [www.python.org](https://www.python.org/downloads/).
 - When installing, be sure to check the Add Python to PATH option.
 - Otherwise you can manually add the Python distributable by following the steps detailed [here](https://www.javatpoint.com/how-to-set-python-path).
 - You can check if Python has been properly installed by opening the command prompt and running the following command:

  ```bat
  python --version
  ```

 - Install the required Python packages:
  
  ```bat
  pip install aiohttp
  pip install regex
  pip install mwparserfromhell
  ```

### Pywikibot
 - Download the latest stable version of Pywikibot from [Toolforge](https://pywikibot.toolforge.org).
 - Unzip the downloaded files to a folder of your own choosing. Open the command prompt and navigate to this folder.
 - Follow the steps detailed [here](https://www.mediawiki.org/wiki/Manual:Pywikibot/Installation#Configure_Pywikibot).
 - Finally run the following command to log in to your wiki:

  ```bat
  python pwb.py login
  ```

### Scripts
 - Download the scripts in this repository.
 - Copy the Python files into the /scripts/userscripts sub-folder in your Pywikibot folder.
 - To use each script, navigate to your Pywikibot directory and run the following command:

  ```bat
  python pwb.py <name of script>
  ```

## Producer Page Discography Auto-Updater

The script vlw_producerpages.py is used to update discography tables in the producer pages in the VOCALOID Lyrics Wiki in bulk.

**Requires the file async_bot_wrapper.py to be placed in the same directory**

<h4>Usage</h4>

To update all pages in the category "Producers":

```bat
python pwb.py vlw_producerpages
```

To update all pages in the category "Producers", starting from the given page title:

```bat
python pwb.py vlw_producerpages -from:<page_title>
```

To update only the given page:

```bat
python pwb.py vlw_producerpages -page:<page_title>
```

For testing of the bot. The global flag `-simulate` blocks all changes from being saved to the real wiki:

```bat
python pwb.py vlw_producerpages [options] -simulate
```

## Producer Page Link Checker

The script vlw_producerpageslinks.py is used:
 - To check whether a link to each existing producer page has been added to their respective producer category pages.
  
   e.g. If the page `Category:Hachi songs list` does not yet link to the producer page `Hachi` (meaning that the `{{Producer}}` template in the category page does not yet contain a link to the producer page), then this bot will edit the `{{Producer}}` template to add this link.

 - To edit pages that redirect to the producer categories so they redirect to the producer pages instead.
  
   e.g. If a page is found that redirects to the category page `Category:Hachi songs list`, then this bot will edit the page so it redirects to the producer page `Hachi` instead.

<h4>Usage</h4>

To update all pages in the category "Producers":

```bat
python pwb.py vlw_producerpageslinks
```

To update all pages in the category "Producers", starting from the given page title:

```bat
python pwb.py vlw_producerpageslinks -from:<page_title>
```

## Internal Wiki Link and Category Mover Bot

The script vlw_editlinks.py is used to update the internal wiki links and category tags in the VOCALOID Lyrics Wiki.

### Moving producer category

```bat
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
    
