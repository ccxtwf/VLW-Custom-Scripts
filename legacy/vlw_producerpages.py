#!/usr/bin/python3
"""

This is a custom bot for bulk updating of producer pages in the Vocaloid Lyrics Wiki.

Requires Python 3.10+
Requires the file async_bot_wrapper.py to be saved in the same folder as this script

It uses the pywikibot wrapper to query the contents of the producer pages in batches, then proceeds to 
asynchronously edit each producer page. As a result, total execution time is in a few minutes rather than hours.

Usage:

python pwb.py vlw_producerpages
  To edit all pages in the category "Producers"

python pwb.py vlw_producerpages -from:<page_title>
  To edit all pages in the category "Producers", starting from the given page title

python pwb.py vlw_producerpages -page:<page_title>
  To edit only the given page.

python pwb.py vlw_producerpages [options] -simulate
  For testing of the bot. -simulate blocks all changes from being saved to the real wiki.

"""

import pywikibot
from pywikibot import pagegenerators
from async_bot_wrapper import AsyncBotWrapper, ENUM_LOGGER_STATES, ENUM_ANSI_COLOURS
import asyncio
import aiohttp
import urllib.parse
import regex as re

from typing import List, Tuple, Set, Any, Optional

from datetime import datetime

import pywikibot.pagegenerators

# If using your own bot, edit this to save the report to another page
CONST_WIKI_REPORT_BLOG = "User:CcxBot/Missing PWT Entries"

# This will prolly not change in the future
CONST_WIKI_API_ENTRYPOINT = "https://vocaloidlyrics.fandom.com/api.php"

# MAXIMUM SIZE OF QUEUE OF TASKS
CONST_QUEUE_SIZE = 500
# NUMBER OF ASYNCHRONOUS THREADS RUNNING AT A SINGLE TIME (ONE THREAD PROCESSES AND SAVES EACH PAGE)
CONST_NUM_TASK_CONSUMERS = 100

class PageNotFoundException(Exception):
  pass
class FailedToUpdatePwtTables(Exception):
  pass
class FailedToUpdateAwtTables(Exception):
  pass

class ProducerPageEditor(AsyncBotWrapper):
  CONST_EDIT_SUMMARY = "Bot: Auto-adding songs and albums to the producer page tables"
  mode_onepageonly: bool

  __rxProdCat = re.compile(r"\{\{\s*[Pp]rodLinks\s*\|([^\}\|]*)")
  __rxProdCatParam = re.compile(r"\s*\b(catname|1)\b\s*=\s*")
  __rxPwtTable = re.compile(r"""(?#
      )(?P<head>{\|\s*class=[\"']sortable\s+producer-table[\"']\s*\n(?#
      )\|-[^\{\}\n]*?\n(?#
      )!\s*\{\{\s*[Pp]wt[ _]head\s*\}\}\s*\n)(?#
      )(.*?(?!\|\}\}))\|\}""", re.S)
  __rxAwtTable = re.compile(r"""(?#
      )(?P<head>{\|\s*class=[\"']sortable\s+producer-table[\"']\s*\n(?#
      )\|-[^\{\}\n]*?\n(?#
      )!\s*\{\{\s*[Aa]wt[ _]head\s*\}\}\s*\n)(?#
      )(.*?(?!\|\}\}))\|\}""", re.S)
  __rxPwtRowTemplate = re.compile(r"""(?#
      individual pwt row header
      )(?:\|-[^\n]*\n[\s\u200B]*\|[\s\u200B]*)(?#
      individual pwt/pht row template
      )\{\{\s*[Pp][wh]t[ _]row\s*\|([^\n]*)\}\}(?#
      followed by new row
      )(?=[\s\u200B]*\n)""", re.S)
  __rxAwtRowTemplate = re.compile(r"""(?#
      individual awt row header
      )(?:\|-[^\n]*\n[\s\u200B]*\|[\s\u200B]*)(?#
      individual awt row template
      )\{\{\s*[Aa]wt[ _]row\s*\|([^\n]*)\}\}(?#
      followed by new row
      )(?=[\s\u200B]*\n)""", re.S)

  def __init__(self, from_page: Optional[str] = None, only_page: Optional[str] = None):    
    self.mode_onepageonly = only_page is not None
    if self.mode_onepageonly:
      # producer_page = pywikibot.Page(self.site, only_page)
      gen = pagegenerators.PagesFromTitlesGenerator([only_page], pywikibot.Site())
    else:
      producer_category = pywikibot.Category(pywikibot.Site(), 'Category:Producers')
      gen = pagegenerators.CategorizedPageGenerator(
        producer_category, 
        content=True,
        start=from_page,
        recurse=False, namespaces=0
      )
      gen = pagegenerators.PreloadingGenerator(gen, groupsize=50)
    super().__init__(
      generator=gen, 
      queue_size=CONST_QUEUE_SIZE, 
      num_consumers=CONST_NUM_TASK_CONSUMERS
    )

  async def treat_one_page(self, page: pywikibot.Page) -> Tuple[Optional[bool], Optional[str], Optional[str], Optional[Any], Optional[Any]]:
    is_edited = False
    failed_to_add = None
    err_message = None
    page_title = None
    if page is None:
      return (None, None, None, None, None)
    try:
      page_title = page.title()
      if not page.exists():
        raise PageNotFoundException("Page doesn't exist")
      elif page.isRedirectPage():
        raise PageNotFoundException("Page is a redirect")
      
      page_contents = page.text
      prod_category = self.__get_producer_category(page_contents)
      
      #self.log(f"[{page_title}]\t{ENUM_ANSI_COLOURS.magenta.value}Main category page is: {prod_category} songs list{ENUM_ANSI_COLOURS.default.value}")

      (song_pages_in_category, album_pages_in_category, (song_pages_in_table, album_pages_in_table)) = await asyncio.gather(
        self.__get_song_pages_in_producer_category(prod_category),
        self.__get_album_pages_in_producer_category(prod_category),
        self.__get_linked_pages_in_templates(page_title)
      )

      # song_pages_in_category, album_pages_in_category = await self.__get_pages_in_producer_category(prod_category)
      # song_pages_in_table, album_pages_in_table = await self.__get_linked_pages_in_templates(page_title)

      missing_song_pages = list(song_pages_in_category.difference(song_pages_in_table))
      missing_album_pages = []
      for album_page, is_compilation_album in album_pages_in_category:
        if album_page not in album_pages_in_table:
          missing_album_pages.append((album_page, is_compilation_album))

      if self.mode_onepageonly:
        self.log(f"{page_title}:\nPage Length\t: {len(page_contents)} chars\nFound song pages in category\t: {len(song_pages_in_category)}\nFound album pages in category\t: {len(album_pages_in_category)}\nFound song links in table\t: {len(song_pages_in_table)}\nFound album links in table\t: {len(album_pages_in_table)}\nMissing song pages\t: {missing_song_pages}\nMissing album pages\t: {missing_album_pages}")

      num_missing_songs = len(missing_song_pages)
      num_missing_albums = len(missing_album_pages)

      if num_missing_songs == 0 and num_missing_albums == 0:
        self.log(f"[{page_title}]\tAll songs and albums accounted for", ENUM_LOGGER_STATES.output)
        return
      
      if num_missing_songs > 0:
        self.log(f"[{page_title}]\t{ENUM_ANSI_COLOURS.magenta.value}Found {num_missing_songs} missing songs:{
          ENUM_ANSI_COLOURS.default.value
        } {', '.join(missing_song_pages)}")
        page_contents = self.__update_pwt(page_contents, missing_song_pages)
        is_edited = True
      if num_missing_albums > 0:
        self.log(f"[{page_title}]\t{ENUM_ANSI_COLOURS.magenta.value}Found {num_missing_albums} missing albums:{
          ENUM_ANSI_COLOURS.default.value
        } {
          ', '.join([page for page, _ in missing_album_pages])
        }")
        page_contents = self.__update_awt(page_contents, missing_album_pages)
        is_edited = True

    except FailedToUpdatePwtTables as e:
      err_message = str(e)
      self.log(f"[{page_title}]\t{err_message}", ENUM_LOGGER_STATES.error)
      failed_to_add = [*missing_song_pages, *missing_album_pages]
    except FailedToUpdateAwtTables as e:
      err_message = str(e)
      self.log(f"[{page_title}]\t{err_message}", ENUM_LOGGER_STATES.error)
      failed_to_add = missing_album_pages
    except Exception as e:
      err_message = str(e)
      self.log(f"[{page_title}]\t{err_message}", ENUM_LOGGER_STATES.error)
    
    finally:
      if not is_edited:
        return (is_edited, page_title, err_message, None, failed_to_add)
      page.text = page_contents
      page.save(
        summary=self.CONST_EDIT_SUMMARY, 
        watch="nochange", 
        minor=False, 
        bot=False,
        asynchronous=True
      )
      return (True, page_title, err_message, None, failed_to_add)
    
  def __get_producer_category(self, page_contents: str) -> str:
    prod_category = self.__rxProdCat.search(page_contents, re.S)
    if prod_category is None:
      raise Exception("Cannot find {{t|ProdLinks}}")
    prod_category = prod_category.group(1).strip()
    prod_category = self.__rxProdCatParam.sub("", prod_category)
    return prod_category
  
  async def run_on_termination(self) -> None:
    if self.mode_onepageonly:
      return
    
    cur_time = datetime.now().strftime("%B %d, %Y")
    edit_report = "Report generated " + cur_time
    edit_report += "\n\n'''''This is a bot-generated report, iterating through the producer pages in [[:Category:Producers]]'''''\n\n''Pages with errors:''\n<categorytree namespaces=0 hideroot=on>Error/Producer pages/PWT</categorytree>\n\n\n"

    if len(self.error_pages) > 0:
      edit_report += "'''''The bot was not able to update the producer works tables for the following pages''''':\n\n"
      for page_title, error_message in self.error_pages:
        edit_report += f"*[[{page_title}]], {error_message}\n"

    if len(self.collected_results_on_failure) > 0:
      edit_report += "\n\n''The following producer pages are missing these song/album pages:''\n\n"
      for page_title, missing_entries in self.collected_results_on_failure:
        edit_report += f"=='''[[{page_title}]]'''==\n"
        edit_report += "\n".join(
          map(lambda page: f"*[[{page}]]", missing_entries)
        )
        edit_report += "\n\n"
    else:
      edit_report += "\n\n''All song/album pages in the respective producer categories have been included in the producer pages.''"
    
    edit_report += "\n[[Category:Error/Producer pages/PWT|!]]"

    report_wikipage = pywikibot.Page(pywikibot.Site(), CONST_WIKI_REPORT_BLOG)
    report_wikipage.text = edit_report
    report_wikipage.save("PWT Report", watch="nochange", minor=False, bot=False)

  async def __get_song_pages_in_producer_category(self, prod_category: str) -> Set[str]:
    async def fetch_from_category(category: str, get_subcats: bool = False):
      all_data = []
      async with aiohttp.ClientSession() as session:
        continue_id = None
        params = {
          "action": "query",
          "format": "json",
          "list": "categorymembers",
          "cmtitle": category,
          "cmprop": "title",
          "cmnamespace": 14 if get_subcats else 0,
          "cmlimit": 500,
          "cmsort": "sortkey",
          "cmdir": "ascending",
          "origin": "*"
        }
        while True:
          if continue_id is not None:
            params["cmcontinue"] = continue_id
          async with session.get(CONST_WIKI_API_ENTRYPOINT, params=params) as response:
            data = await response.json()
            all_data.extend(data["query"]["categorymembers"])
            if "continue" in data:
              continue_id = data["continue"]["cmcontinue"]
            else:
              break
      return all_data
    prod_category = f"Category:{prod_category}_songs_list"
    subcategories = await fetch_from_category(prod_category, True)
    song_subcategories = [subcat["title"] for subcat in subcategories if not subcat["title"].endswith("/Albums")]
    songs = await asyncio.gather(
      fetch_from_category(prod_category),
      *map(lambda subcat: fetch_from_category(subcat), song_subcategories)
    )
    distinct_songs = set()
    for arr in songs:
      for song in arr:
        distinct_songs.add(song["title"])
    #print("In category:", len(distinct_songs))
    return distinct_songs

  async def __get_album_pages_in_producer_category(self, prod_category: str) -> List[Tuple[str, bool]]:
    albums = []
    async with aiohttp.ClientSession() as session:
      continue_id = None
      params = {
        "action": "query",
        "format": "json",
        "generator": "categorymembers",
        "gcmtitle": f"Category:{prod_category}_songs_list/Albums",
        "prop": "categories",
        "gcmlimit": 500,
        "cllimit": 500,
        "clcategories": "Category:Compilation_albums",
        "gcmnamespace": 0,
        "gcmsort": "sortkey",
        "gcmdir": "ascending",
        "origin": "*"
      }
      while True:
        if continue_id is not None:
          params["gcmcontinue"] = continue_id
        async with session.get(CONST_WIKI_API_ENTRYPOINT, params=params) as response:
          data = await response.json()
          if not "query" in data:
            break
          for page in data["query"]["pages"].values():
            albums.append((page["title"], "categories" in page))
          if "continue" in data:
            continue_id = data["continue"]["gcmcontinue"]
          else:
            break
    return albums

  async def __get_linked_pages_in_templates(self, page_title: str) -> Tuple[Set[str], Set[str]]:
    async def fetch_from_url(page_title: str):
      all_data = []
      params = {
        "action": "query",
        "format": "json", 
        "indexpageids": "true",
        "prop": "templates",
        "titles": page_title,
        "tlnamespace": 0,
        "tllimit": 500,
        "tldir": "ascending",
        "origin": "*",
      }
      async with aiohttp.ClientSession() as session:
        continue_id = None
        while True:
          if continue_id is not None:
            params["tlcontinue"] = continue_id
          async with session.get(CONST_WIKI_API_ENTRYPOINT, params=params) as response:
            data = await response.json()
            all_data.extend(data["query"]["pages"][str(data["query"]["pageids"][0])]["templates"])
            if "continue" in data:
              continue_id = data["continue"]["tlcontinue"]
            else:
              break
      return all_data
    pages = await fetch_from_url(page_title)
    set_linked_songs = set()
    set_linked_albums = set()
    for page in pages:
      if page["ns"] != 0:
        continue
      if re.search(r" \((album|E\.?P\.?)\)$", page["title"]) is not None:
        set_linked_albums.add(page["title"])
      else:
        set_linked_songs.add(page["title"])
    #print("In links:", len(set_linked_songs), len(set_linked_albums))
    return (set_linked_songs, set_linked_albums)

  def __getSortValue(self, pwt_template_input: str) -> str:
    def detone_pinyin(text, showUmlaut):
      text = re.sub("[āáǎà]", "a", text)
      text = re.sub("[ĀÁǍÀ]", "A", text)
      text = re.sub("[īíǐì]", "i", text)
      text = re.sub("[ĪÍǏÌ]", "I", text)
      text = re.sub("[ūúǔù]", "u", text)
      text = re.sub("[ŪÚǓÙ]", "U", text)
      text = re.sub("[ēéěè]", "e", text)
      text = re.sub("[ĒÉĚÈ]", "E", text)
      text = re.sub("[ōóǒò]", "o", text)
      text = re.sub("[ŌÓǑÒ]", "O", text)
      if showUmlaut:
        text = re.sub("[ǖǘǚǜ]", "ü", text)
        text = re.sub("[ǕǗǙǛ]", "Ü", text)
      else:
        text = re.sub("[ǖǘǚǜ]", "v", text)
        text = re.sub("[ǕǗǙǛ]", "V", text)
      return text
        
    def get_romaji(wikipage_name):
      extracted_romaji = wikipage_name
      try_original_title = ""
      try_find_regex = []
      extracted_romaji = re.sub(r" \(album\)$", "", extracted_romaji)
      extracted_romaji = re.sub(r"(?<=\))\/.*$", "", extracted_romaji)
      try_find_regex = re.findall(r"(?<=\s\()[ -~ĀÁǍÀĒÉĚÈŌÓǑÒ].*(?=\)$)", extracted_romaji)
      if not len(try_find_regex):
        return wikipage_name
        return "CASE: No match found"
      extracted_romaji = try_find_regex[0]
      while (re.search(r"^[^\(]*\)[^\(]*\(", extracted_romaji) is not None):
        extracted_romaji = re.sub(r"^[^\(]*\)[^\(]*\(", "", extracted_romaji)
      try_original_title = wikipage_name.replace(" (" + extracted_romaji + ")", "")
      try_find_regex = re.search(r"[^ -~]", try_original_title)
      if try_find_regex is None:
        return wikipage_name
        return "CASE: Title is already in English"
      #Finally return the altered extractedRomaji
      return extracted_romaji
    
    page_title = re.search(r"^[^\|]*", pwt_template_input).group(0)
    page_title = re.sub(r"\{\{=\}\}", "=", re.sub(r"^\s*1\s*=\s*", "", page_title))

    rom_title = get_romaji(page_title)

    misc_params = pwt_template_input.replace(page_title, "")

    #Deduce manual romanization
    manual_kanji = re.search(r"\|kanji\s*=\s*([^\|]*)", misc_params)
    manual_kanji = re.search(r"\|(?<!\s*\w+\s*=\s*)([^\|]*)", misc_params) if manual_kanji is None else manual_kanji
    manual_kanji = manual_kanji.group(1) if not manual_kanji is None else ""
    manual_rom = re.search(r"\|rom\s*=\s*([^\|]*)", misc_params)
    manual_rom = manual_rom.group(1) if not manual_rom is None else ""
    rom_title = manual_rom if manual_rom != "" else rom_title

    #Finishing operations
    rom_title = detone_pinyin(rom_title, False).lower()
    rom_title = re.sub(r"[\[\(\)\]\"'¿\?『』「」:’]", "", rom_title)
    rom_title += misc_params

    return rom_title

  def __update_pwt(self, page_contents: str, missing_songs: List[str]) -> str:
    pwt_tables = list(self.__rxPwtTable.finditer(page_contents))
    if len(pwt_tables) > 1:
      raise FailedToUpdatePwtTables("More than one pwt row table found.")
    if len(pwt_tables) == 0:
      raise FailedToUpdatePwtTables("Cannot find pwt row table.")
    pwt_table_wikitext = pwt_tables[0].group(0)

    extract_match_properties = lambda m: dict(fullmatch=m.group(0), input=m.group(1), sort_value=self.__getSortValue(m.group(1)))
    pwt_songs = list(map(extract_match_properties, self.__rxPwtRowTemplate.finditer(pwt_table_wikitext)))
    for missing_song in missing_songs:
        sort_value = self.__getSortValue(missing_song)
        pwt_template = "|-\n| {{pwt row|" + missing_song + "}}"
        add_to_index = 0
        while add_to_index < len(pwt_songs):
          if (pwt_songs[add_to_index]["sort_value"] > sort_value):
            break
          add_to_index += 1
        pwt_songs.insert(add_to_index, dict(fullmatch=pwt_template, input=missing_song, sort_value=sort_value))
    
    new_pwt_table_wikitext = pwt_tables[0].group("head") + "\n".join(map(lambda m: m["fullmatch"], pwt_songs)) + "\n|}"
    return page_contents.replace(pwt_table_wikitext, new_pwt_table_wikitext)

  def __update_awt(self, page_contents: str, missing_albums: List[Tuple[str, bool]]) -> str:
    if len(missing_albums) == 0: 
      return page_contents
    awt_tables = awt_tables = list(self.__rxAwtTable.finditer(page_contents))
    extract_match_properties = lambda m: dict(fullmatch=m.group(0), input=m.group(1), sort_value=self.__getSortValue(m.group(1)))
    if len(awt_tables) > 1:
      awt_table_wikitext, awt_table_wikitext_compilations = awt_tables[0].group(0), awt_tables[1].group(0)

      awt_albums = list(map(extract_match_properties, self.__rxAwtRowTemplate.finditer( awt_table_wikitext )))
      awt_albums_compilations = list(map(extract_match_properties, self.__rxAwtRowTemplate.finditer( awt_table_wikitext_compilations )))
      for missing_album, is_compilation_album in missing_albums:
        sort_value = self.__getSortValue(missing_album)
        awt_template = "|-\n| {{awt row|" + missing_album + "}}"
        add_to_index = 0
        search_in_table = awt_albums_compilations if is_compilation_album else awt_albums
        while add_to_index < len(search_in_table):
          if (search_in_table[add_to_index]["sort_value"] > sort_value):
            break
          add_to_index += 1
        search_in_table.insert(add_to_index, dict(fullmatch=awt_template, input=missing_album, sort_value=sort_value))
        
      new_awt_table_wikitext = awt_tables[0].group("head") + "\n".join(map(lambda m: m["fullmatch"], awt_albums)) + "\n|}"
      new_awt_table_wikitext_compilations = awt_tables[1].group("head") + "\n".join(map(lambda m: m["fullmatch"], awt_albums_compilations)) + "\n|}"
      page_contents = page_contents.replace(awt_table_wikitext, new_awt_table_wikitext)
      page_contents = page_contents.replace(awt_table_wikitext_compilations, new_awt_table_wikitext_compilations)
      return page_contents
    
    if len(awt_tables) == 1:
      awt_table_wikitext = awt_tables[0].group(0)

      awt_albums = list(map(extract_match_properties, self.__rxAwtRowTemplate.finditer( awt_table_wikitext)))
      for missing_album, _ in missing_albums:
        sort_value = self.__getSortValue(missing_album)
        awt_template = "|-\n| {{awt row|" + missing_album + "}}"
        add_to_index = 0
        while add_to_index < len(awt_albums):
          if (awt_albums[add_to_index]["sort_value"] > sort_value):
            break
          add_to_index += 1
        awt_albums.insert(add_to_index, dict(fullmatch=awt_template, input=missing_album, sort_value=sort_value))
        
      new_awt_table_wikitext = awt_tables[0].group("head") + "\n".join(map(lambda m: m["fullmatch"], awt_albums)) + "\n|}"
      return page_contents.replace(awt_table_wikitext, new_awt_table_wikitext)

    else:
      missing_albums = [page for page, _ in missing_albums]
      missing_albums = sorted(missing_albums, key=self.__getSortValue)
      new_awt_table_wikitext = "==Discography==\n{| class=\"sortable producer-table\"\n|- class=\"vcolor-default\"\n! {{awt head}}\n"
      new_awt_table_wikitext += "\n".join(map(lambda str: "|-\n| {{awt row|" + str + "}}", missing_albums)) + "\n|}\n\n__NOTOC__"
      return page_contents.replace("__NOTOC__", new_awt_table_wikitext)

if __name__ == "__main__":
  options = {}
  local_args = pywikibot.handle_args()
  for arg in local_args:
    arg, _, value = arg.partition(':')
    options[arg] = value
  fromPage = options.get("-from", None)
  onlyPage = options.get("-page", None)
  bot = ProducerPageEditor(fromPage, onlyPage)
  bot.run()