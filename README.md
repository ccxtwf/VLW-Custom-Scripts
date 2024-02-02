# Custom Bot Scripts for Vocaloid Lyrics Wiki

This is an assortment of bot scripts for bulk editing in the VOCALOID Lyrics Wiki.

## System Requirements
 - Python 3.10+
 - Pywikibot 8.1+
 - Installed python packages:
   - [pip install aiohttp](https://pypi.org/project/aiohttp/)
   - [pip install regex](https://pypi.org/project/regex/)

## Table of Contents
- [Custom Bot Scripts for Vocaloid Lyrics Wiki](#custom-bot-scripts-for-vocaloid-lyrics-wiki)
  - [System Requirements](#system-requirements)
  - [Table of Contents](#table-of-contents)
  - [Installation \& Configuration](#installation--configuration)
    - [Python](#python)
    - [Pywikibot](#pywikibot)
    - [Scripts](#scripts)
  - [Producer Page Editor Bot](#producer-page-editor-bot)
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

## Producer Page Editor Bot

The script vlw_producerpages.py is used to update discography tables in the producer pages in the VOCALOID Lyrics Wiki in bulk.

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

## Internal Wiki Link and Category Mover Bot

The script vlw_editlinks.py is used to update the internal wiki links and category tags in the VOCALOID Lyrics Wiki.

### Moving producer category

```bat
python pwb.py vlw_editlinks -moveprodcat -old:"foo" -new:"bar" [-changeprodredirect] [-keeplinkcap]
```

Edit the category tag of the producer, from [[Category:foo songs list]] -> [[Category:bar songs list]]

If this command is run with the optional flag `-changeprodredirect`, then the bot will also change the producer redirect links in the page.

    -old:"foo" -new:"bar":      [[foo]] -> [[bar]], [[Foo]] -> [[bar]]
    -old:"w1 w2" -new:"a1 a2":  [[w1 w2]] -> [[a1 a2]], [[w1_w2]] -> [[a1 a2]], [[W1 w2]] -> [[a1 a2]]

If this command is also run with the optional flag `-keeplinkcap`, then the bot will keep the old name as the link text.

    -old:"foo" -new:"bar":      [[foo]] -> [[foo|bar]]

General tips:
 - If you only want to change the producer category tags, and want to keep the wiki links as they are, run...
  
        python pwb.py vlw_editlinks -moveprodcat -old:"..." -new:"..."

 - If you want to change the producer category tags and also change the producer links (usually to prevent double redirects), run...
    
        python pwb.py vlw_editlinks -moveprodcat -old:"MATERU" -new:"MARETU" -changeprodredirect
        python pwb.py vlw_editlinks -moveprodcat -old:"Hachi" -new:"Kenshi Yonezu" -changeprodredirect -keeplinkcap

 - Usually `-changeprodredirect` is used to correct a mistyped producer's name and `-changeprodredirect -keeplinkcap` is used when the producer is undergoing a name change.

### Moving singer category

Edit the category tag of the singer/vocal synth, from [[Category:Songs featuring foo]] -> [[Category:Songs featuring bar]]

    python pwb.py vlw_editlinks -movesingercat -old:"foo" -new:"bar"

### Moving internal wiki links

Edit internal wiki links that link to the page "foo" so that they will be linked to the page "bar" 

If linkcap is specified then the new wikilink will have the specified parameter as the link caption
    
    python pwb.py vlw_editlinks -old:"foo" -new:"bar" -linkcap:"text" -[page|category|file]:...

    
