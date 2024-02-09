#!/usr/bin/python3
"""

This is a custom bot for bulk updating of producer pages in the Vocaloid Lyrics Wiki.

Requires Python 3.10+

It uses the pywikibot wrapper to query the contents of the producer pages in batches, then proceeds to 
asynchronously edit each producer page. As a result, total execution time is in a few minutes rather than hours.

Usage:

python pwb.py vlw_producerpageslinks
  To edit all pages in the category "Producers"

python pwb.py vlw_producerpageslinks -from:<page_title>
  To edit all pages in the category "Producers", starting from the given page title

python pwb.py vlw_producerpageslinks [options] -simulate
  For testing of the bot. -simulate blocks all changes from being saved to the real wiki.

"""

import pywikibot
from pywikibot import pagegenerators
import asyncio
import mwparserfromhell
import regex as re

from typing import Callable, Tuple, Iterator, List, Dict
from enum import Enum

from time import time

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
class ProducerCategoryException(Exception):
  pass

class ProducerPageEditor:

  def __init__(self, fromPage: str = None):
    self.site = pywikibot.Site()
    self.CONST_EDIT_SUMMARY = "Bot: Updating producer page links"
    producercategory = pywikibot.Category(self.site, 'Category:Producers')
    gen = pagegenerators.CategorizedPageGenerator(
      producercategory, 
      content=True,
      start=fromPage,
      recurse=False, namespaces=0
    )
    gen = pagegenerators.PreloadingGenerator(gen, groupsize=60)
    self.producerPages = gen
    self.editedPages = []
    self.errorPages = []
   
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

  async def mapProducerCategoryToProducerPage(self, page: pywikibot.Page) -> Tuple[str, str]:
    if page is None:
      return (None, None)
    pageContents = page.text
    prodcat = re.search(r"\{\{\s*[Pp]rodLinks\s*\|([^\}\|]*)", pageContents, re.S)
    if prodcat is None:
      # raise Exception("Cannot find {{ProdLinks}}")
      return (page.title(), None)
    prodcat = prodcat.group(1).strip()
    prodcat = re.sub(r"\s*\bcatname\b\s*=\s*", "", prodcat)
    return (page.title(), prodcat)

  def parseTemplate(self, prodTemplate: mwparserfromhell.wikicode.Template) -> Tuple[Dict, bool]:
    producerTemplateParams = {}
    idx = 0
    usesNumberedParams = False
    for param in prodTemplate.params:
      k, v = "", ""
      arr = param.split("=")
      if len(arr) == 1:
        idx += 1
        k = idx
        v = arr[0]
      else:
        k, *v = arr
        if len(v) > 1:
          usesNumberedParams = True
        v = "=".join(v)
      producerTemplateParams[str(k)] = v
    return producerTemplateParams, usesNumberedParams

  def compareWikitext(self, comparedLink: str, comparedPageTitle: str) -> bool:
    comparedLink = re.sub(r"([\.\+\*\?\^\$\(\)\[\]\{\}\\])", r"\\\1", comparedLink)
    comparedLink = re.sub(r"[ _]", "[ _]", comparedLink)
    comparedLink = re.sub(r"^(\w)", 
      lambda x: "[" + x.group(1).capitalize() + x.group(1).lower() + "]", 
      comparedLink)
    rx = re.compile(comparedLink)
    return rx.match(comparedPageTitle) is not None

  async def checkRedirectsToProducerCategory(self, prodcat: pywikibot.Page, prodpageName: str):
    redirects = list(prodcat.redirects(namespaces=[0]))
    if len(redirects) == 0:
      return
    for redirectPage in redirects:
      if redirectPage.title().startswith("Category:"):
        continue
      redirectPage.text = f"#REDIRECT[[{prodpageName}]]"
      redirectPage.save(
        summary=f"{self.CONST_EDIT_SUMMARY}: Redirecting to {prodpageName}",
        watch="nochange", 
        minor=True, 
        botflag=True,
        asynchronous=True
      )

  async def treatOnePage(self, prodcat: pywikibot.Page, prodpageName: str):
    try:
      isEdited = False
      if prodcat is None:
        return
      if not prodcat.exists() or prodcat.isRedirectPage():
        raise ProducerCategoryException("Producer category page is not found")
      
      # Extract {{Producer}} template
      templates = mwparserfromhell.parse(prodcat.text).filter_templates()
      findProducerTemplate = list(filter(
        lambda template: template.name.matches("Producer"),
        templates
      ))
      if len(findProducerTemplate) == 0:
        raise ProducerCategoryException("Producer category does not contain {{Producer}} template")
      elif len(findProducerTemplate) > 1:
        raise ProducerCategoryException("Producer category has more than one {{Producer}} template")
      
      # Edit pages that redirect to any producer category
      await self.checkRedirectsToProducerCategory(prodcat, prodpageName)

      # Parse template parameters
      oldProdTemplate = str(findProducerTemplate[0])
      producerTemplateParams, usesNumberedParams = self.parseTemplate(findProducerTemplate[0])
      findProdPageLink = producerTemplateParams.get("2", None)
      if findProdPageLink is None:
        producerTemplateParams["2"] = prodpageName
      elif not self.compareWikitext(findProdPageLink, prodpageName):
        producerTemplateParams["2"] = prodpageName
      else:
        return
      
      # Edit 
      newProdTemplate = "{{Producer"
      idx = 0
      for k,v in producerTemplateParams.items():
        if not usesNumberedParams and str(k).isnumeric():
          idx += 1
          while idx < int(k):
            newProdTemplate += "|"
            idx += 1
          newProdTemplate += f"|{v}"
        else:
          newProdTemplate += f"|{k}={v}"
      newProdTemplate += "}}"
      prodcat.text = prodcat.text.replace(oldProdTemplate, newProdTemplate, 1)
      # print(prodcat.text)
      
      isEdited = True
        
    except Exception as e:
      errMessage = str(e)
      self.log(f"[{prodpageName}]\t{errMessage}", ENUM_LOGGER_STATES.error.value)
      self.errorPages.append(prodpageName, errMessage)

    finally:
      if not isEdited:
        return
      self.editedPages.append(prodpageName)
      prodcat.save(
        summary=self.CONST_EDIT_SUMMARY, 
        watch="nochange", 
        minor=True, 
        botflag=True,
        asynchronous=True
      )

  async def treatPages(self):

    def unpackPageGenerator(gen: Iterator, size: int = 20) -> Tuple[List[pywikibot.Page], bool]:
      pages = []
      cur = None
      for i in range(size):
        cur = next(gen, None)
        pages.append(cur)
      return (pages, (cur is None))
    
    def filterMappedProdcats(mappedProdCats: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], List[str]]:
      errorPages = []
      res = []
      for prodpageName, prodcatName in mappedProdCats:
        if prodpageName is None:
          continue
        elif prodcatName is None:
          errorPages.append(prodpageName)
        else:
          res.append((prodpageName, prodcatName))
      return (res, errorPages)

    while True:
      pages, reachedEndOfGenerator = unpackPageGenerator(self.producerPages)
      mappedProdCats = await asyncio.gather(*(self.mapProducerCategoryToProducerPage(page) for page in pages))
      mappedProdCats, detectedErrors = filterMappedProdcats(mappedProdCats)
      if len(detectedErrors) > 0:
        self.errorPages.extend([(page, "Cannot map to producer category") for page in detectedErrors])
      prodcats = pagegenerators.PagesFromTitlesGenerator(
        [f"Category:{el[1]} songs list" for el in mappedProdCats]
      )
      prodcats = pagegenerators.PreloadingGenerator(prodcats, groupsize=20)
      prodcats, _ = unpackPageGenerator(prodcats)
      await asyncio.gather(*(self.treatOnePage(page, mappedProdCats[idx][0]) for idx, page in enumerate(prodcats) if page is not None))
      if reachedEndOfGenerator:
        break
  
  @countElapsedTime
  def run(self):
    asyncio.run(self.treatPages())
    if len(self.editedPages) > 0:
      self.log("Edited the following pages:")
      self.log("\n".join(self.editedPages))
    if len(self.errorPages) > 0:
      self.log("Could not edit the following pages:")
      self.log("\n".join([f"{page}:\t{msg}" for page, msg in self.errorPages]))

def main(*args: str) -> None:
  options = {}
  local_args = pywikibot.handle_args(args)
  for arg in local_args:
    arg, _, value = arg.partition(':')
    options[arg] = value
  fromPage = options.get("-from", None)
  bot = ProducerPageEditor(fromPage)
  bot.run()

if __name__ == "__main__":
  main()