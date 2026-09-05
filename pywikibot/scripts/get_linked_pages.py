from __future__ import annotations
from typing import List, Tuple, Literal
import pywikibot as pwb
from pywikibot import pagegenerators
from pywikibot.bot import (
  suggest_help,
  ConfigParserBot,
  SingleSiteBot,
)
from pywikibot.site import BaseSite

class WhatLinksHereChecker(
  SingleSiteBot,
  ConfigParserBot, 
):
  linked_pages: List[Tuple[str, str, Literal["redirect", "link"]]]
  
  def __init__(self, site: BaseSite | bool | None = True, **kwargs) -> None:
    self.linked_pages = []
    super().__init__(site, **kwargs)
  
  def treat(self, page: pwb.Page) -> None:
    # page: pwb.Page = self.current_page
    linksto = page.title(with_ns=True)
    for link in page.backlinks(follow_redirects=True, filter_redirects=None):
      linksfrom = link.title(with_ns=True)  
      self.linked_pages.append((linksto, linksfrom, "redirect" if link.isRedirectPage() else "link"))

  def teardown(self) -> None:
    with open("linked-pages.txt", mode="w+", encoding="utf-8") as f:
      for linksto, linksfrom, pagetype in self.linked_pages:
        f.writelines([linksfrom, "\t", linksto, "\t", pagetype, "\n"])
    pwb.info("Saved linked-pages.txt")
    return super().teardown()

def main(*args: str) -> None:
  options = {}
  local_args = pwb.handle_args(args)
  gen_factory = pagegenerators.GeneratorFactory()
  local_args = gen_factory.handle_args(local_args)

  gen = gen_factory.getCombinedGenerator(preload=True)
  if not suggest_help(missing_generator=not gen):
    bot = WhatLinksHereChecker(generator=gen, **options)
    bot.run()

if __name__ == '__main__':
  main()