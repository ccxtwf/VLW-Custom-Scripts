"""

This is a custom bot to rename a root engine category, e.g. 
[[Category:ACE Virtual Singer song categories]] ->
[[Category:ACE Studio song categories]]

Usage:

python vlw_move_engine.py <OLD ENGINE NAME> <NEW ENGINE NAME> [-simulate]

  e.g. python vlw_move_engine.py "ACE Virtual Singer" "ACE Studio"

  Pass -simulate to get pywikibot to run the bot as a dry-run (i.e. no 
  edits will be made on the live wiki).
"""
import pywikibot as pwb
from pywikibot import pagegenerators
from pywikibot.bot import (
  ConfigParserBot,
  ExistingPageBot,
  SingleSiteBot,
)
import re
import os, sys
from typing import Any, Generator, Set, Dict, List

from pywikibot.site import BaseSite

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
  '&params;': pagegenerators.parameterHelp
}  # noqa: N816

class EngineMoverBot(
  SingleSiteBot,          # A bot only working on one site
  ConfigParserBot,        # A bot which reads options from scripts.ini setting file
  ExistingPageBot,        # CurrentPageBot which only treats existing pages
):
  old_engine: str
  new_engine: str

  successful_edits: Set[str]
  successful_moves: List[str]
  failed_pages: List[str]
  failed_moves: List[str]

  def __init__(self, old_engine: str, new_engine: str, site: BaseSite | bool | None = True, **kwargs: Any) -> None:
    super().__init__(site, **kwargs)
    self.old_engine = old_engine
    self.new_engine = new_engine
    self.successful_edits = set()
    self.successful_moves = []
    self.failed_pages = []
    self.failed_moves = []

  def get_default_summary(self) -> str:
    """
      Get bot's default summary for editing
    """
    return f"Moved root engine category \"{self.old_engine}\" -> \"{self.new_engine}\""

  def _get_ancestor_root_category(self, engine: str) -> pwb.Category:
    """
      Get root category: [[Category:{engine} song categories]]
    """
    root_category_title = f"Category:{engine} song categories"
    category = pwb.Category(source=pwb.Site(), title=root_category_title)
    return category

  def _get_synth_root_category(self, engine: str) -> pwb.Category:
    """
      Get root category: [[Category:{engine} songs]]
    """
    root_category_title = f"Category:{engine} songs"
    category = pwb.Category(source=pwb.Site(), title=root_category_title)
    return category

  def _get_album_root_category(self, engine: str) -> pwb.Category:
    """
      Get root album category: [[Category:Albums featuring {engine}]]
    """
    root_category_title = f"Category:Albums featuring {engine}"
    category = pwb.Category(source=pwb.Site(), title=root_category_title)
    return category
  
  def _get_producer_root_category(self, engine: str) -> pwb.Category:
    """
      Get root album category: [[Category:Producers using {engine}]]
    """
    root_category_title = f"Category:Producers using {engine}"
    category = pwb.Category(source=pwb.Site(), title=root_category_title)
    return category 

  def _get_synth_song_category(self, synth: str) -> pwb.Category:
    """
      Get song sub-category: [[Category:Songs featuring {synth}]]
    """
    category_title = f"Category:Songs featuring {synth}"
    category = pwb.Category(source=pwb.Site(), title=category_title)
    return category

  def _get_synth_album_category(self, synth: str) -> pwb.Category:
    """
      Get album sub-category: [[Category:Albums featuring {synth}]]
    """
    category_title = f"Category:Albums featuring {synth}"
    category = pwb.Category(source=pwb.Site(), title=category_title)
    return category    

  def get_synth_category_pages(self, engine: str) -> Generator[pwb.Page]:
    """
      Get the synth song category pages, e.g. 
      [[Category:Songs featuring Luo Tianyi (ACE Virtual Singer)]],
      that are listed under 
      [[Category:ACE Virtual Singer song categories]]
    """
    for member in self._get_ancestor_root_category(engine).members(member_type='subcat'):
      subcat_title = member.title(with_ns=False)
      if subcat_title.startswith('Songs featuring '):
        yield member

  def get_synth_album_category_pages(self, engine: str) -> Generator[pwb.Page]:
    """
      Get the synth album category pages, e.g. 
      [[Category:Albums featuring Luo Tianyi (ACE Virtual Singer)]],
      that are listed under 
      [[Category:Albums featuring ACE Virtual Singer]]
    """
    for member in self._get_album_root_category(engine).members(member_type='subcat'):
      subcat_title = member.title(with_ns=False)
      if subcat_title.startswith('Albums featuring '):
        yield member

  def get_song_pages_ft_synth(self, synth: str) -> Generator[pwb.Page]:
    """
      Get the song pages that feature the given synth.
    """
    for member in self._get_synth_song_category(synth).members(member_type='page', namespaces=[0]):
      yield member

  def get_producer_pages_ft_engine(self, engine: str) -> Generator[pwb.Page]:
    """
      Get the producer pages that use the given synth.
    """
    for member in self._get_producer_root_category(engine).members(member_type='page', namespaces=[0]):
      yield member

  def prepare_regex_pattern(self, text: str, match_underscore: bool = False, case_insensitive_first_char: bool = False) -> re.Pattern:
    """
      Prepare a regex pattern based on a given string
      
      `match_underscore = True` treats whitespace characters and underscore 
      characters as identical.
      
      `case_insensitive_first_char = True` matches regardless whether the first 
      character is in lower or upper case, but the other characters must be 
      matched with case sensitivity.
    """
    comp = ""
    if len(text) == 0:
      raise ValueError("text is empty!")
    first_char, text = text[0], text[1:]

    if case_insensitive_first_char and first_char.isalpha():
      comp += f"[{first_char.lower()}{first_char.upper()}]"
    else:
      comp += re.escape(first_char)

    whitespace_separator = r" +"
    if match_underscore:
      whitespace_separator = r"[ _]+"
    comp += whitespace_separator.join([re.escape(s) for s in re.split(whitespace_separator, text)])
    
    return re.compile(comp)

  def edit_synth_song_page_category(self, page_contents: str, old_engine: str, new_engine: str) -> str:
    """
      When editing a synth song page category, 
      e.g. [[Category:Songs featuring Luo Tianyi (ACE Virtual Singer)]],
      edit the `voicesynth = ACE Virtual Singer` parameter in the 
      {{SynthCategory}} template.
    """
    search_pattern = f"voicesynth *= *{self.prepare_regex_pattern(old_engine, match_underscore=True).pattern}"
    search_pattern = re.compile(search_pattern)
    page_contents = search_pattern.sub(
      repl=f"voicesynth = {new_engine}", 
      string=page_contents
    )
    return page_contents

  def edit_synth_album_page_category(self, page_contents: str, old_engine: str, new_engine: str) -> str:
    """
      When editing a synth album page category, 
      e.g. [[Category:Albums featuring Luo Tianyi (ACE Virtual Singer)]],
      edit the second unnamed parameter (root synth name) in the 
      `{{AlbumCat}}` template.
    """
    search_pattern = self.prepare_regex_pattern(old_engine, match_underscore=True)
    page_contents = search_pattern.sub(
      repl=new_engine, 
      string=page_contents
    )
    return page_contents

  def _edit_internal_links_of_synth(self, page_contents: str, old_engine: str, new_engine: str, disambiguated_synths: Set[str]) -> str:
    """
      e.g. [[Luo Tianyi (ACE Virtual Singer)]] -> [[Luo Tianyi (ACE Studio)]]
      e.g. [[Luo Tianyi (ACE Virtual Singer)|Luo Heng]] -> [[Luo Tianyi (ACE Studio)|Luo Heng]]
    """
    search_pattern = f"\\[\\[[ _]*(?P<basename>[^\\]]+)[ _]+\\({self.prepare_regex_pattern(old_engine, match_underscore=True).pattern}\\)[ _]*\\|?(?P<caption>(?<=\\|).*?|)[ _]*\\]\\]"
    search_pattern = re.compile(search_pattern)
    matches = [
      (m, re.sub(r"[ _]+", " ", m.group("basename"))) 
      for m in search_pattern.finditer(page_contents) 
    ]
    matches = [
      (m, bn)
      for m, bn in matches 
      if bn in disambiguated_synths
    ]
    for m, bn in matches:
      new_link = f"[[{bn} ({new_engine}){f"|{m.group("caption")}" if m.group("caption") else ""}]]"
      page_contents = page_contents.replace(m.group(0), new_link, count=1)

    return page_contents

  def edit_song_page(self, page_contents: str, old_engine: str, new_engine: str, disambiguated_synths: Set[str]) -> str:
    """
      When editing a song page featuring the synths of that engine, 
      edit any internal links pointing to any synth of that engine 
      that requires disambiguating, e.g. [[Luo Tianyi (ACE Virtual Singer)]]
    """
    return self._edit_internal_links_of_synth(page_contents, old_engine, new_engine, disambiguated_synths)

  def edit_album_page(self, page_contents: str, old_engine: str, new_engine: str, disambiguated_synths: Set[str]) -> str:
    """
      When editing an album page featuring the synths of that engine, 
      edit any internal links pointing to any synth of that engine 
      that requires disambiguating, e.g. [[Luo Tianyi (ACE Virtual Singer)]],
      along with any category tag, e.g. [[Category:Albums featuring Luo Tianyi (ACE Virtual Singer)]]
    """
    # internal links
    page_contents = self._edit_internal_links_of_synth(page_contents, old_engine, new_engine, disambiguated_synths)

    # root engine category tag
    search_pattern = f"\\[\\[[Cc]ategory[ _]*:[ _]*[Aa]lbums[ _]+featuring[ _]+{self.prepare_regex_pattern(old_engine, match_underscore=True, case_insensitive_first_char=False).pattern}[ _]*\\|?(?P<caption>(?<=\\|).*?|)[ _]*\\]\\]"
    search_pattern = re.compile(search_pattern)
    page_contents = search_pattern.sub(f"[[Category:Albums featuring {new_engine}]]", page_contents)

    # synth category tags
    search_pattern = f"\\[\\[[Cc]ategory[ _]*:[ _]*[Aa]lbums[ _]+featuring[ _]+(?P<basename>[^\\]]+)[ _]+\\({self.prepare_regex_pattern(old_engine, match_underscore=True, case_insensitive_first_char=False).pattern}\\)[ _]*\\|?(?P<caption>(?<=\\|).*?|)[ _]*\\]\\]"
    search_pattern = re.compile(search_pattern)
    matches = [m for m in search_pattern.finditer(page_contents) if m.group("basename") in disambiguated_synths]
    for m in matches:
      page_contents = page_contents.replace(
        m.group(0), 
        f"[[Category:Albums featuring {m.group(1)} ({new_engine})]]", 
        count=1
      )   

    return page_contents

  def edit_producer_page(self, page_contents: str, old_engine: str, new_engine: str, disambiguated_synths: Set[str]) -> str:
    """
      When editing a producer page featuring the synths of that engine, 
      edit any internal links pointing to any synth of that engine 
      that requires disambiguating, e.g. [[Luo Tianyi (ACE Virtual Singer)]],
      then edit any category tag pointing to the engine
    """
    page_contents = self._edit_internal_links_of_synth(page_contents, old_engine, new_engine, disambiguated_synths)

    # category tags
    search_pattern = f"\\[\\[[Cc]ategory[ _]*:[ _]*[Pp]roducers[ _]+using[ _]+{self.prepare_regex_pattern(old_engine, match_underscore=True, case_insensitive_first_char=False).pattern}[ _]*\\|?(?P<caption>(?<=\\|).*?|)[ _]*\\]\\]"
    search_pattern = re.compile(search_pattern)
    page_contents = search_pattern.sub(
      repl=f"[[Category:Producers using {new_engine}]]", 
      string=page_contents
    )

    return page_contents

  def wrapped_user_put(self, page: pwb.Page, newtext: str, **kwargs) -> None:
    is_success = self.userPut(
      page=page,
      oldtext=page.text,
      newtext=newtext,
      summary=self.get_default_summary(),
      ignore_save_related_errors=False,
      ignore_server_errors=False,
      **kwargs,
    )
    if not is_success:
      self.failed_pages.append(page.title(with_ns=True))
    else:
      self.successful_edits.add(page.title(with_ns=True))

  def wrapped_move(self, page: pwb.Page, newtitle: str, noredirects: bool = True) -> None:
    oldtitle = page.title(with_ns=True)
    pwb.info(f"Moving [[{oldtitle}]] -> [[{newtitle}]]")
    if not self.user_confirm("Are you sure you want to move this page?"):
      return
    try: 
      page.move(
        newtitle, 
        reason=self.get_default_summary(),
        movetalk=True,
        noredirect=noredirects,
      )
      self.successful_moves.append(oldtitle)
    except Exception as e:
      pwb.error(e)
      self.failed_moves.append(oldtitle)

  def run(self):
    """
      General plan:
       
      General plan:
       1)  Yield synth categories ([[Category:Songs featuring ...]]) by calling 
           `get_synth_category_pages()`.
       2)  For each synth category, apply the edits by calling 
           `edit_synth_song_page_category()`.
       3)  Get the list of synths with disambiguated titles that need moving.
       4)  For each disambiguated synth category that needs to be moved as well, 
           get the song pages by calling `get_song_pages_ft_synth()`.
       5)  For each song page that needs editing, call `edit_song_page()`.
       6)  When all edits are done, move the categories that need disambiguating. Also move the redirect, e.g. [[Luo Tianyi (ACE Virtual Singer)]].
       7)  Finally move the root song category ([[Category:<ENGINE> songs]]).
       
       8)  Yield album categories ([[Category:Albums featuring ...]]) by calling 
           `get_synth_album_category_pages()`.
       9)  For each album category, apply the edits by calling 
           `edit_synth_album_page_category()`.
       10) Iterate through the albums in each sub-category by calling `get_album_pages_ft_synth()`.
       11) For each album page that needs editing, call `edit_album_page()`.
       12) When all edits are done, move the categories that need disambiguating.
       13) Finally move the root album category ([[Category:Albums featuring <ENGINE>]]).

       14) Yield producer pages using the engine by calling 
           `get_producer_pages_ft_engine()`.
       15) For each producer page, apply the edits by calling `edit_producer_page()`.
       16) Finally move the root producer category ([[Category:Producers using <ENGINE>]]).

       17) When all is done move the root category ([[Category:<ENGINE> song categories]]).
    """
    synths_with_disambiguated_titles: list[re.Match] = []
    
    rx_disambig = self.prepare_regex_pattern(
      self.old_engine, 
      match_underscore=True, 
      case_insensitive_first_char=False
    )
    rx_disambig = re.compile(f"Category:(?:[Ss]ongs|[Aa]lbums) +featuring +(?P<qualifier>(?P<basename>.*?) +\\({rx_disambig.pattern}\\))$")

    pwb.info(f"Taking care of all \"Songs featuring X\" category pages")
    for synth in self.get_synth_category_pages(self.old_engine):
      # [[Category:Songs featuring Luo Tianyi (ACE Virtual Singer)]]
      self.wrapped_user_put(
        page=synth,
        newtext=self.edit_synth_song_page_category(
          synth.text, 
          self.old_engine, 
          self.new_engine
        ),
      )

      # Collate pagetitles that needed moving
      subcat_title = synth.title(with_ns=True)
      if m := re.search(rx_disambig, subcat_title):
        synths_with_disambiguated_titles.append(m)

    pwb.info(f"Taking care of all \"Songs featuring X\" category pages that needed disambiguation")
    disambiguated_synths = set([m.group("basename") for m in synths_with_disambiguated_titles])
    for m in synths_with_disambiguated_titles:
      synth = m.group("qualifier")
      new_synth_category_title = f"Category:Songs featuring {m.group("basename")} ({self.new_engine})"

      # Fetch list of pages before moving
      song_pages_gen = [page.title(with_ns=False) for page in self.get_song_pages_ft_synth(synth)]

      # Move category page [[Category:Songs featuring Luo Tianyi (ACE Virtual Singer)]]
      category_page = self._get_synth_song_category(synth)
      self.wrapped_move(
        page=category_page, 
        newtitle=new_synth_category_title
      )

      # Move main redirect
      pwb.info(f"Taking care of main redirects to [[Category:Songs featuring {synth}]]")
      # Redirect page e.g. [[Luo Tianyi (ACE Virtual Singer)]]
      category_redirect = pwb.Page(source=pwb.Site(), title=synth)
      if not category_redirect.exists() or not category_redirect.isRedirectPage():
        self.failed_pages.append(synth)
      else:
        self.wrapped_user_put(
          page=category_redirect,
          newtext=f"#REDIRECT[[{new_synth_category_title}]]",
          asynchronous=False, # must wait
        )
        self.wrapped_move(
          page=category_redirect, 
          newtitle=f"{m.group("basename")} ({self.new_engine})",
        )

      for pagetitle in song_pages_gen:
        if pagetitle in self.successful_edits:
          print(f"Skipping editing {pagetitle} (already edited)")
          continue
        # Pages in [[Category:Songs featuring Luo Tianyi (ACE Virtual Singer)]]
        page = pwb.Page(source=pwb.Site(), title=pagetitle)
        self.wrapped_user_put(
          page=page,
          newtext=self.edit_song_page(
            page_contents=page.text, 
            old_engine=self.old_engine, 
            new_engine=self.new_engine,
            disambiguated_synths=disambiguated_synths,
          )
        )

    # Move root song category [[Category:ACE Virtual Singer songs]]
    pwb.info(f"Moving root song category")
    root_engine_song_category = self._get_synth_root_category(self.old_engine)
    self.wrapped_move(
      page=root_engine_song_category,
      newtitle=f"Category:{self.new_engine} songs"
    )

    pwb.info(f"Taking care of all \"Albums featuring X\" category pages")
    for synth in self.get_synth_album_category_pages(self.old_engine):
      # [[Category:Albums featuring Luo Tianyi (ACE Virtual Singer)]]
      self.wrapped_user_put(
        page=synth,
        newtext=self.edit_synth_album_page_category(
          synth.text,
          self.old_engine,
          self.new_engine,
        ),
        asynchronous=False # must wait
      )

      c = pwb.Category(source=pwb.Site(), title=synth.title(with_ns=True))
      for page in c.members(member_type='page', namespaces=[0]):
        if page in self.successful_edits:
          continue  # already edited
        # Pages in [[Category:Albums featuring Luo Tianyi (ACE Virtual Singer)]]
        self.wrapped_user_put(
          page=page,
          newtext=self.edit_album_page(
            page_contents=page.text, 
            old_engine=self.old_engine, 
            new_engine=self.new_engine, 
            disambiguated_synths=disambiguated_synths,
          ),
        )

      if m := re.search(rx_disambig, synth.title(with_ns=True)):
        # Move category page [[Category:Albums featuring Luo Tianyi (ACE Virtual Singer)]]
        self.wrapped_move(
          page=synth, 
          newtitle=f"Category:Albums featuring {m.group("basename")} ({self.new_engine})"
        )

    # Move root engine album category [[Category:Albums featuring ACE Virtual Singer]]
    pwb.info(f"Moving root album category")
    root_engine_album_category = self._get_album_root_category(self.old_engine)
    self.wrapped_move(
      page=root_engine_album_category, 
      newtitle=f"Category:Albums featuring {self.new_engine}",
    )

    pwb.info(f"Taking care of the \"Producers using X\" category")
    for producer_page in self.get_producer_pages_ft_engine(self.old_engine):
      # Pages in [[Category:Producers using ACE Virtual Singer]]
      self.wrapped_user_put(
        page=producer_page,
        newtext=self.edit_producer_page(
          page_contents=producer_page.text,
          old_engine=self.old_engine,
          new_engine=self.new_engine,
          disambiguated_synths=disambiguated_synths
        )
      )
    # Move root engine producer category [[Category:Producers using ACE Virtual Singer]]
    root_engine_producer_category = self._get_producer_root_category(self.old_engine)
    self.wrapped_move(
      page=root_engine_producer_category, 
      newtitle=f"Category:Producers using {self.new_engine}",
    )

    # Move root engine category [[Category:ACE Virtual Singer song categories]]
    root_engine_song_category = self._get_ancestor_root_category(self.old_engine)
    self.wrapped_move(
      page=root_engine_song_category, 
      newtitle=f"Category:{self.new_engine} song categories",
    )

  def teardown(self) -> None:
    with open("move-log.txt", mode="w+", encoding="utf-8") as f:
      f.write("=== Successfully edited ===\n")
      f.writelines(map(lambda p: p+"\n", self.successful_edits))
      f.write("\n")

      f.write("=== Tried to move ===\n")
      f.writelines(map(lambda p: p+"\n", self.successful_moves))
      f.write("\n")

      f.write("=== Failed to edit ===\n")
      f.writelines(map(lambda p: p+"\n", self.failed_pages))
      f.write("\n")

      f.write("=== Failed to move ===\n")
      f.writelines(map(lambda p: p+"\n", self.failed_moves))
      f.write("\n")

    pwb.info("Saved move-log.txt")
    return super().teardown()

def main(*args: str) -> None:
  local_args = pwb.handle_args(args)
  local_args = [arg for arg in local_args if not arg.startswith('-')]
  options: Dict[str, str | None] = {
    "old": local_args[0] if len(local_args) > 0 else None,
    "new": local_args[1] if len(local_args) > 1 else None,
  }

  for option in ('old', 'new'):
    if not options[option]:
      options[option] = pwb.input(f"Please enter a value for needed argument {option}")
  if options["old"] == options["new"]:
    pwb.error("Old engine name cannot be the same as new engine name!")
    return

  assert(options["old"])
  assert(options["new"])
  bot = EngineMoverBot(old_engine=options["old"], new_engine=options["new"])
  pwb.info(f"Preparing to move [[Category:{bot.old_engine} song categories]] -> [[Category:{bot.new_engine} song categories]]...")
  bot.run()
  bot.exit()

if __name__ == "__main__":
  main(*sys.argv[1:])