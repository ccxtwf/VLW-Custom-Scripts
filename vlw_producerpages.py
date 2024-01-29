#!/usr/bin/python3
"""

This is a custom bot for bulk updating of producer pages in the Vocaloid Lyrics Wiki.

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
import asyncio
import aiohttp
import urllib.parse
import regex as re

from typing import Callable, List, Tuple, Set
from enum import Enum

from datetime import datetime
from time import time

# If using your own bot, edit this to save the report to another page
CONST_WIKI_REPORT_BLOG = "User:CcxBot/Missing PWT Entries"

# This will prolly not change in the future
CONST_WIKI_API_ENTRYPOINT = "https://vocaloidlyrics.fandom.com/api.php"

def countElapsedTime(func: Callable) -> Callable:
  def wrapped(*args, **kwargs):
    funcName = func.__name__
    startTime = time()
    res = func(*args, **kwargs)
    endTime = time()
    print(f"{funcName} executed in {endTime-startTime} s")
    return res
  return wrapped

class ENUM_LOGGER_STATES(Enum):
  log = 1
  output = 2
  warn = 3
  error = 4

class ENUM_ANSI_COLOURS(Enum):
  yellow = "\033[33m"
  red = "\033[31m"
  green = "\033[32m"
  magenta = "\033[95m"
  bold = "\033[1m"
  default = "\033[0m"

class PageNotFoundException(Exception):
  pass
class FailedToUpdatePwtTables(Exception):
  pass
class FailedToUpdateAwtTables(Exception):
  pass

class AsyncSession:
  def __init__(self, url):
    self._url = url
  async def __aenter__(self):
    self.session = aiohttp.ClientSession()
    response = await self.session.get(self._url)
    return response
  async def __aexit__(self, exc_type, exc_value, exc_tb):
    await self.session.close()

class ProducerPageUtil:

  def __init__(self, site: pywikibot.Site = None, logger: Callable = None):
    self.site = site
    self.logger = logger
  
  def getProducerCategory(self, pageContents: str) -> str:
    prodcat = re.search(r"\{\{\s*[Pp]rodLinks\s*\|([^\}\|]*)", pageContents, re.S)
    if prodcat is None:
      raise Exception("Cannot find {{ProdLinks}}")
    prodcat = prodcat.group(1).strip()
    prodcat = re.sub(r"\s*\bcatname\b\s*=\s*", "", prodcat)
    return prodcat
  
  async def getPagesInProducerCategory(self, prodcat: str) -> Tuple[Set[str], Set[str]]:
    async def fetchFromUrl(url: str):
      async with aiohttp.ClientSession() as session:
        allData = []
        reachedEnd = False
        continueid = None
        while not reachedEnd:
          async with session.get(f"{url}{'' if continueid is None else f'&cmcontinue={continueid}'}") as response:
            data = await response.json()
            allData.extend(data["query"]["categorymembers"])
            reachedEnd = not "continue" in data
            if not reachedEnd:
              continueid = data["continue"]["cmcontinue"]
      await session.close()
      return allData
    def getUrl(category: str, getSubcats: bool = False):
      return f"{CONST_WIKI_API_ENTRYPOINT}?action=query&format=json&list=categorymembers&cmtitle={category}&cmprop=title&cmnamespace={14 if getSubcats else 0}&cmlimit=500&cmsort=sortkey&cmdir=ascending&origin=*"
    prodcat = f"Category:{urllib.parse.quote(prodcat)}_songs_list"
    listSubcats = await fetchFromUrl(getUrl(prodcat, True))
    listSubcatsSongs = [item["title"] for item in listSubcats if not item["title"].endswith("/Albums")]
    listSongs = await asyncio.gather(
      fetchFromUrl(getUrl(prodcat)),
      *map(lambda subcat: fetchFromUrl(getUrl(subcat)), listSubcatsSongs)
    )
    listAlbums = []
    if len(listSubcatsSongs) != len(listSubcats):
      listAlbums = await fetchFromUrl(getUrl(f"{prodcat}/Albums"))
    setSongs = set()
    for arr in listSongs:
      for song in arr:
        setSongs.add(song["title"])
    setAlbums = set([obj["title"] for obj in listAlbums])
    #print("In category:", len(setSongs), len(setAlbums))
    return (setSongs, setAlbums)

  async def getLinkedPagesInTemplates(self, pageTitle: str) -> Tuple[Set[str], Set[str]]:
    async def fetchFromUrl(url: str):
      async with aiohttp.ClientSession() as session:
        allData = []
        reachedEnd = False
        continueid = None
        while not reachedEnd:
          async with session.get(f"{url}{'' if continueid is None else f'&tlcontinue={continueid}'}") as response:
            data = await response.json()
            allData.extend(data["query"]["pages"][str(data["query"]["pageids"][0])]["templates"])
            reachedEnd = not "continue" in data
            if not reachedEnd:
              continueid = data["continue"]["tlcontinue"]
      await session.close()
      return allData
    url = f"{CONST_WIKI_API_ENTRYPOINT}?action=query&format=json&indexpageids=true&prop=templates&titles={urllib.parse.quote(pageTitle)}&tlnamespace=0&tllimit=500&tldir=ascending&origin=*"
    listPages = await fetchFromUrl(url)
    setPwtLinked = set()
    setAwtLinked = set()
    for page in listPages:
      if page["ns"] != 0:
        continue
      if re.search(r" \((album|E\.?P\.?)\)$", page["title"], re.I) is not None:
        setAwtLinked.add(page["title"])
      else:
        setPwtLinked.add(page["title"])
    #print("In links:", len(setPwtLinked), len(setAwtLinked))
    return (setPwtLinked, setAwtLinked)

  """
  DEPRECATED: Not recommended because of use of synchronous code
  async def getPagesInProducerCategory(self, prodcat: str) -> Tuple[Set[str], Set[str]]:
    cat = pywikibot.Category(self.site, f"Category:{prodcat} songs list")
    listPages = cat.members(member_type='page', recurse=1)
    setAlbumPages = set()
    setSongPages = set()
    for page in listPages:
      page = page.title()
      if page.endswith(' (album)'):
        setAlbumPages.add(page)
      else:
        setSongPages.add(page)
    return (setSongPages, setAlbumPages)
  """

  """
  DEPRECATED: Not recommended because of use of synchronous code
  async def getLinkedPagesInTemplates(self, page: pywikibot.Page) -> Tuple[Set[str], Set[str]]:
    listTemplates = page.templates(content=False)
    setPwtLinked = set()
    setAwtLinked = set()
    for templ in listTemplates:
      linkedPage = templ.title()
      if linkedPage.startswith('Template:') or linkedPage.startswith('Module:'):
        continue
      if linkedPage.endswith(' (album)'):
        setAwtLinked.add(linkedPage)
      else:
        setPwtLinked.add(linkedPage)
    return (setPwtLinked, setAwtLinked)
  """
  
  def _extractPwtTables(self, pageContents: str) -> List[re.Match]:
    regexPwt = re.compile(r"(?P<head>{\|\s*class=[\"']sortable\s+producer-table[\"']\s*\n\|-[^\{\}\n]*?\n!\s*\{\{\s*[Pp]wt[ _]head\s*\}\}\s*\n)(.*?(?!\|\}\}))\|\}", re.S)
    listMatchPwt = list(re.finditer(regexPwt, pageContents))
    return listMatchPwt
  
  def _extractAwtTables(self, pageContents: str) -> List[re.Match]:
    regexAwt = re.compile(r"(?P<head>{\|\s*class=[\"']sortable\s+producer-table[\"']\s*\n\|-[^\{\}\n]*?\n!\s*\{\{\s*[Aa]wt[ _]head\s*\}\}\s*\n)(.*?(?!\|\}\}))\|\}", re.S)
    listMatchAwt = list(re.finditer(regexAwt, pageContents))
    return listMatchAwt

  def _getSortValue(self, pwtTemplateInput: str) -> str:

    def detonepinyin(text, showUmlaut):
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
        
    def getRomaji(strWikiPageName):
      extractedRomaji = strWikiPageName
      tryOriginalTitle = ""
      tryRegex = []
      extractedRomaji = re.sub(r" \(album\)$", "", extractedRomaji)
      extractedRomaji = re.sub(r"(?<=\))\/.*$", "", extractedRomaji)
      tryRegex = re.findall(r"(?<=\s\()[ -~ĀÁǍÀĒÉĚÈŌÓǑÒ].*(?=\)$)", extractedRomaji)
      if not len(tryRegex):
        return strWikiPageName
        return "CASE: No match found"
      extractedRomaji = tryRegex[0]
      while (re.search(r"^[^\(]*\)[^\(]*\(", extractedRomaji) is not None):
        extractedRomaji = re.sub(r"^[^\(]*\)[^\(]*\(", "", extractedRomaji)
      tryOriginalTitle = strWikiPageName.replace(" (" + extractedRomaji + ")", "")
      tryRegex = re.search(r"[^ -~]", tryOriginalTitle)
      if tryRegex is None:
        return strWikiPageName
        return "CASE: Title is already in English"
      #Finally return the altered extractedRomaji
      return extractedRomaji
    
    pagetitle = re.search(r"^[^\|]*", pwtTemplateInput).group(0)
    pagetitle = re.sub(r"\{\{=\}\}", "=", re.sub(r"^\s*1\s*=\s*", "", pagetitle))

    romtitle = getRomaji(pagetitle)

    miscparams = pwtTemplateInput.replace(pagetitle, "")

    #Deduce manual romanization
    manual_kanji = re.search(r"\|kanji\s*=\s*([^\|]*)", miscparams)
    manual_kanji = re.search(r"\|(?<!\s*\w+\s*=\s*)([^\|]*)", miscparams) if manual_kanji is None else manual_kanji
    manual_kanji = manual_kanji.group(1) if not manual_kanji is None else ""
    manual_rom = re.search(r"\|rom\s*=\s*([^\|]*)", miscparams)
    manual_rom = manual_rom.group(1) if not manual_rom is None else ""
    romtitle = manual_rom if manual_rom != "" else romtitle

    #Finishing operations
    romtitle = detonepinyin(romtitle, False).lower()
    romtitle = re.sub(r"[\[\(\)\]\"'¿\?『』「」:’]", "", romtitle)
    romtitle += miscparams

    return romtitle

  def updatePwt(self, pageContents: str, listMissingSongs: List[str]) -> str:

    listMatchPwt = self._extractPwtTables(pageContents)
    if len(listMatchPwt) > 1:
      raise Exception("More than one pwt row table found.")
    if len(listMatchPwt) == 0:
      raise Exception("Cannot find pwt row table.")
    
    pwtTableWikitext = listMatchPwt[0].group(0)

    regexPwtRowTemplate = re.compile(r"""(?#
      individual pwt row header
      )(?:\|-[^\n]*\n[\s\u200B]*\|[\s\u200B]*)(?#
      individual pwt/pht row template
      )\{\{\s*[Pp][wh]t[ _]row\s*\|([^\n]*)\}\}(?#
      followed by new row
      )(?=[\s\u200B]*\n)""", re.S)
    
    extractMatchProperties = lambda m: dict(fullmatch=m.group(0), input=m.group(1), sort_value=self._getSortValue(m.group(1)))
    listPwtSongs = list(map(extractMatchProperties, re.finditer(regexPwtRowTemplate, pwtTableWikitext)))
    for item in listMissingSongs:
        sortValue = self._getSortValue(item)
        pwtTemplate = "|-\n| {{pwt row|" + item + "}}"
        addToIndex = 0
        while addToIndex < len(listPwtSongs):
          if (listPwtSongs[addToIndex]["sort_value"] > sortValue):
            break
          addToIndex += 1
        listPwtSongs.insert(addToIndex, dict(fullmatch=pwtTemplate, input=item, sort_value=sortValue))
    
    newPwtTableWikitext = listMatchPwt[0].group("head") + "\n".join(map(lambda m: m["fullmatch"], listPwtSongs)) + "\n|}"
    return pageContents.replace(pwtTableWikitext, newPwtTableWikitext)

  def updateAwt(self, pageContents: str, listMissingAlbums: List[str]) -> str:
    
    if len(listMissingAlbums) == 0:
      return pageContents
    
    listMatchAwt = self._extractAwtTables(pageContents)
    if len(listMatchAwt) > 1:
      raise Exception("More than one awt row table found.")            
    
    if len(listMatchAwt) == 1:
      awtTableWikitext = listMatchAwt[0].group(0)

      regexAwtRowTemplate = re.compile(r"""(?#
        individual awt row header
        )(?:\|-[^\n]*\n[\s\u200B]*\|[\s\u200B]*)(?#
        individual awt row template
        )\{\{\s*[Aa]wt[ _]row\s*\|([^\n]*)\}\}(?#
        followed by new row
        )(?=[\s\u200B]*\n)""", re.S)
      
      extractMatchProperties = lambda m: dict(fullmatch=m.group(0), input=m.group(1), sort_value=self._getSortValue(m.group(1)))
      listPwtAlbums = list(map(extractMatchProperties, re.finditer(regexAwtRowTemplate, awtTableWikitext)))
      for item in listMissingAlbums:
        sortValue = self._getSortValue(item)
        awtTemplate = "|-\n| {{awt row|" + item + "}}"
        addToIndex = 0
        while addToIndex < len(listPwtAlbums):
          if (listPwtAlbums[addToIndex]["sort_value"] > sortValue):
            break
          addToIndex += 1
        listPwtAlbums.insert(addToIndex, dict(fullmatch=awtTemplate, input=item, sort_value=sortValue))
        
      newAwtTableWikitext = listMatchAwt[0].group("head") + "\n".join(map(lambda m: m["fullmatch"], listPwtAlbums)) + "\n|}"
      return pageContents.replace(awtTableWikitext, newAwtTableWikitext)

    else:
      listMissingAlbums = sorted(listMissingAlbums, key=self._getSortValue)
      newAwtTableWikitext = "==Discography==\n{| class=\"sortable producer-table\"\n|- class=\"vcolor-default\"\n! {{awt head}}\n"
      newAwtTableWikitext += "\n".join(map(lambda str: "|-\n| {{awt row|" + str + "}}", listMissingAlbums)) + "\n|}\n\n__NOTOC__"
      return pageContents.replace("__NOTOC__", newAwtTableWikitext)
 

class ProducerPageEditor:

  def __init__(self, fromPage: str = None, onlyPage: str = None):
    self.site = pywikibot.Site()
    self.CONST_EDIT_SUMMARY = "Bot: Auto-adding songs and albums to the producer page tables"
    self.utils = ProducerPageUtil(self.site, self.log)
    self.finalWikiReportPageTitle = CONST_WIKI_REPORT_BLOG
    self.mode_onepageonly = onlyPage is not None
    if self.mode_onepageonly:
      gen = pywikibot.Page(self.site, onlyPage)
    else:
      producercategory = pywikibot.Category(self.site, 'Category:Producers')
      gen = pagegenerators.CategorizedPageGenerator(
        producercategory, 
        content=True,
        start=fromPage,
        recurse=False, namespaces=0
      )
      gen = pagegenerators.PreloadingGenerator(gen, groupsize=60)
    self.producerPages = gen
    self.errorPages = []
    self.failedToAdd = {}
   
  def log(self, message: str, status: ENUM_LOGGER_STATES = ENUM_LOGGER_STATES.log.value) -> None:
    if status == ENUM_LOGGER_STATES.log.value:
      print(message)
    elif status == ENUM_LOGGER_STATES.output.value:
      print(f"{ENUM_ANSI_COLOURS.green.value}{message}{ENUM_ANSI_COLOURS.default.value}")
    elif status == ENUM_LOGGER_STATES.warn.value:
      print(f"{ENUM_ANSI_COLOURS.yellow.value}{message}{ENUM_ANSI_COLOURS.default.value}")
    elif status == ENUM_LOGGER_STATES.error.value:
      print(f"{ENUM_ANSI_COLOURS.red.value}{message}{ENUM_ANSI_COLOURS.default.value}")
    else:
      print(message)

  def createFinalReport(self) -> None:
    curTime = datetime.now().strftime("%B %d, %Y")
    editReport = "Report generated " + curTime
    editReport += "\n\n'''''This is a bot-generated report, iterating through the producer pages in [[:Category:Producers]]'''''\n\n''Pages with errors:''\n<categorytree namespaces=0 hideroot=on>Error/Producer pages/PWT</categorytree>\n\n\n"

    if len(self.errorPages):
      self.log("The following pages need intervention:", ENUM_LOGGER_STATES.error.value)
      editReport += "'''''The bot was not able to update the producer works tables for the following pages''''':\n\n"
      for item in self.errorPages:
        self.log(f"{item[0]}\t{item[1]}")
        editReport += f"*[[{item[0]}]], {item[1]}\n"

    if len(self.failedToAdd.keys()):
      editReport += "\n\n''The following producer pages are missing these song/album pages:''\n\n"
      for item, missingPages in self.failedToAdd.items():
        editReport += f"=='''[[{item}]]'''==\n"
        editReport += "\n".join(
          map(lambda page: f"*[[{page}]]", missingPages)
        )
        editReport += "\n\n"
    else:
      editReport += "\n\n''All song/album pages in the respective producer categories have been included in the producer pages.''"
    
    editReport += "\n[[Category:Error/Producer pages/PWT|!]]"

    reportwikipage = pywikibot.Page(self.site, self.finalWikiReportPageTitle)
    reportwikipage.text = editReport
    reportwikipage.save("PWT Report", watch="nochange", minor=False, botflag=False)

    return

  async def treatOnePage(self, page: pywikibot.Page):
    try:

      isEdited = False
      pageTitle = page.title()
      if page is None:
        return
      elif not page.exists():
        raise PageNotFoundException("Page doesn't exist")
      elif page.isRedirectPage():
        raise PageNotFoundException("Page is a redirect")

      pageContents = page.text
      
      prodcat = self.utils.getProducerCategory(pageContents)
      self.log(f"[{pageTitle}]\t{ENUM_ANSI_COLOURS.magenta.value}Main category page is: {prodcat} songs list{ENUM_ANSI_COLOURS.default.value}")

      ((songPagesInCategory, albumPagesInCategory), (songPagesInTable, albumPagesInTable)) = await asyncio.gather(
        self.utils.getPagesInProducerCategory(prodcat),
        self.utils.getLinkedPagesInTemplates(pageTitle)
      )
      
      # songPagesInCategory, albumPagesInCategory = await self.utils.getPagesInProducerCategory(prodcat)
      # songPagesInTable, albumPagesInTable = await self.utils.getLinkedPagesInTemplates(pageTitle)

      missingSongPages = list(songPagesInCategory.difference(songPagesInTable))
      missingAlbumPages = list(albumPagesInCategory.difference(albumPagesInTable))

      if self.mode_onepageonly:
        self.log(f"{pageTitle}:\nPage Length\t: {len(pageContents)} chars\nFound song pages in category\t: {len(songPagesInCategory)}\nFound album pages in category\t: {len(albumPagesInCategory)}\nFound song links in table\t: {len(songPagesInTable)}\nFound album links in table\t: {len(albumPagesInTable)}\nMissing song pages\t: {missingSongPages}\nMissing album pages\t: {missingAlbumPages}")

      numMissingSongs = len(missingSongPages)
      numMissingAlbums = len(missingAlbumPages)

      if numMissingSongs == 0 and numMissingAlbums == 0:
        self.log(f"[{pageTitle}]\tAll songs and albums accounted for", ENUM_LOGGER_STATES.output.value)
        return
      
      if numMissingSongs > 0:
        self.log(f"[{pageTitle}]\t{ENUM_ANSI_COLOURS.magenta.value}Found {numMissingSongs} missing songs:{ENUM_ANSI_COLOURS.default.value} {', '.join(missingSongPages)}")
        pageContents = self.utils.updatePwt(pageContents, missingSongPages)
        isEdited = True
      if numMissingAlbums > 0:
        self.log(f"[{pageTitle}]\t{ENUM_ANSI_COLOURS.magenta.value}Found {numMissingAlbums} missing albums:{ENUM_ANSI_COLOURS.default.value} {', '.join(missingAlbumPages)}")
        pageContents = self.utils.updateAwt(pageContents, missingAlbumPages)
        isEdited = True

    except PageNotFoundException as e:
      errMessage = str(e)
      self.log(f"[{pageTitle}]\t{errMessage}", ENUM_LOGGER_STATES.error.value)
      self.errorPages.append(pageTitle, errMessage)
    except FailedToUpdatePwtTables as e:
      errMessage = str(e)
      self.log(f"[{pageTitle}]\t{errMessage}", ENUM_LOGGER_STATES.error.value)
      self.errorPages.append(pageTitle, errMessage)
      self.failedToAdd[pageTitle] = [*missingSongPages, *missingAlbumPages]
    except FailedToUpdateAwtTables as e:
      errMessage = str(e)
      self.log(f"[{pageTitle}]\t{errMessage}", ENUM_LOGGER_STATES.error.value)
      self.errorPages.append(pageTitle, errMessage)
      self.failedToAdd[pageTitle] = missingAlbumPages
    except Exception as e:
      errMessage = str(e)
      self.log(f"[{pageTitle}]\t{errMessage}", ENUM_LOGGER_STATES.error.value)
      self.errorPages.append(pageTitle, errMessage)
    
    finally:
      if not isEdited:
        return
      #self.log(f"SIMULATING: Saving {pageTitle}")
      page.text = pageContents
      page.save(
        summary=self.CONST_EDIT_SUMMARY, 
        watch="nochange", 
        minor=False, 
        botflag=False,
        asynchronous=True
      )

  async def treatPages(self):
    while True:
      pages = []
      cur = None
      for i in range(20):
        cur = next(self.producerPages, None)
        pages.append(cur)
      await asyncio.gather(*(self.treatOnePage(page) for page in pages))
      if cur is None:
        break
  
  @countElapsedTime
  def run(self):
    if self.mode_onepageonly:
      asyncio.run(self.treatOnePage(self.producerPages))
    else:
      asyncio.run(self.treatPages())
      self.createFinalReport()

def main(*args: str) -> None:
  options = {}
  local_args = pywikibot.handle_args(args)
  for arg in local_args:
    arg, _, value = arg.partition(':')
    options[arg] = value
  fromPage = options.get("-from", None)
  onlyPage = options.get("-page", None)
  bot = ProducerPageEditor(fromPage, onlyPage)
  bot.run()

if __name__ == "__main__":
  main()