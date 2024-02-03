#!/usr/bin/python3
"""

This is a custom bot for bulk editing of links in the Vocaloid Lyrics Wiki.

By default the pywikibot wrapper will prompt the user to confirm the changes unless the global flag -always is used.

Usage:

python pwb.py vlw_editlinks -moveprodcat -old:"foo" -new:"bar" [-changeprodredirect] [-keeplinkcap]

  Edit the category tag of the producer, from [[Category:foo songs list]] -> [[Category:bar songs list]]

  If this command is run with the optional flag -changeprodredirect, then the bot will also change the producer redirect links in the page.
    -old:"foo" -new:"bar":      [[foo]] -> [[bar]], [[Foo]] -> [[bar]]
    -old:"w1 w2" -new:"a1 a2":  [[w1 w2]] -> [[a1 a2]], [[w1_w2]] -> [[a1 a2]], [[W1 w2]] -> [[a1 a2]]

  If this command is also run with the optional flag -keeplinkcap, then the bot will keep the old name as the link text.
    -old:"foo" -new:"bar":      [[foo]] -> [[bar|foo]]

  General tips:
    If you only want to change the producer category tags, and want to keep the normal links as they are, run...
      python pwb.py vlw_editlinks -moveprodcat -old:"..." -new:"..."
    If you want to change the producer category tags and also change the producer links (usually to prevent double redirects), run...
      python pwb.py vlw_editlinks -moveprodcat -old:"MATERU" -new:"MARETU" -changeprodredirect
      python pwb.py vlw_editlinks -moveprodcat -old:"Hachi" -new:"Kenshi Yonezu" -changeprodredirect -keeplinkcap
    Usually -changeprodredirect is used to correct a mistyped producer's name and -changeprodredirect -keeplinkcap is used when the producer is undergoing a name change.

python pwb.py vlw_editlinks -movesingercat -old:"foo" -new:"bar"

  Edit the category tag of the singer/vocal synth, from [[Category:Songs featuring foo]] -> [[Category:Songs featuring bar]]

python pwb.py vlw_editlinks -old:"foo" -new:"bar" -linkcap:"text" -[page|category|file]:...

  Edit internal wiki links that link to the page "foo" so that they will be linked to the page "bar" 
  If linkcap is specified then the new wikilink will have the specified parameter as the link caption

python pwb.py vlw_editlinks -chardisambig -basevb:"Hatsune Miku" -synth:"VOCALOID"

  Edit internal wiki link of singers/synths that link to character disambiguation pages
  Automatic check based on the categories already (manually) tagged in

"""
import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import (
  AutomaticTWSummaryBot,
  ConfigParserBot,
  ExistingPageBot,
  SingleSiteBot,
)
import re

#Pywikibot Log/Output
prLog = pywikibot.bot.log
prOutput = pywikibot.bot.output
prWarning = pywikibot.bot.warning
prError = pywikibot.bot.error

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
  '&params;': pagegenerators.parameterHelp
}  # noqa: N816

class LinkEditorBot(
  # Refer pywikobot.bot for generic bot classes
  SingleSiteBot,          # A bot only working on one site
  ConfigParserBot,        # A bot which reads options from scripts.ini setting file
  ExistingPageBot,        # CurrentPageBot which only treats existing pages
  AutomaticTWSummaryBot,  # Automatically defines summary; needs summary_key
):

  site = pywikibot.Site()

  use_redirects = False  # treats non-redirects only
  summary_key = 'basic-changing'

  update_options = {

    # User options for editing internal wiki links 
    'old': '', 
    'new': '', 
    'linkcap': '',

    # User options for editing vocal synth links (in the case when they are linked to char disambiguation pages) 
    'chardisambig': False, 
    'basevb': '', 
    'synth': '',

    # User options for moving producer categories
    'moveprodcat': False,
    'changeprodredirect': False,
    'keeplinkcap': False,

    # User options for moving singer categories
    'movesingercat': False
  }
  
  """Change the internal link in the page"""
  def change_internal_link_address(self, str_page, orig_internal_link, new_internal_link, new_link_text):
    orig_internal_link = re.sub(r"([\.\+\*\?\^\$\(\)\[\]\{\}\\])", r"\\\1", orig_internal_link)
    orig_internal_link = re.sub(r"[ _]", "[ _]", orig_internal_link)
    orig_internal_link = re.sub(r"^(\w)", 
      lambda x: "[" + x.group(1).capitalize() + x.group(1).lower() + "]", 
      orig_internal_link)
    search_regex_1 = re.compile(f"\[\[\s*?{orig_internal_link}\s*\]\]")
    search_regex_2 = re.compile(f"\[\[\s*?{orig_internal_link}\s*\|(.+?)\]\]")
    #replace_regex_1 = re.compile("[[" + new_internal_link + "]]")
    #replace_regex_2 = re.compile("[[" + new_internal_link + "|\1]]")
    str_page = search_regex_1.sub(
      "[[" + new_internal_link + "]]" if new_link_text.strip() == "" else 
      "[[" + new_internal_link + "|" + new_link_text + "]]", 
      str_page)
    str_page = search_regex_2.sub(
      lambda x: f"[[{new_internal_link}|{x.group(1)}]]" 
      if new_link_text.strip() == "" else 
      f"[[{new_internal_link}|{new_link_text}]]",
      str_page)
    return str_page
  
  """Change the internal link to a vocal synth in the case when that link is connected to a character disambiguation page"""
  def change_vocalist_disambig(self, str_page, list_categories, base_voicebank, synth_family):
    orig_internal_link = base_voicebank
    new_internal_link = f"{base_voicebank} ({synth_family})"
    str_find_category = f"Songs featuring {new_internal_link}"
    if str_find_category in list_categories:
      #str_page = self.change_internal_link_address(str_page, base_voicebank, base_voicebank + " (" + synth_family + ")", base_voicebank)
      orig_internal_link = re.sub(r"([\.\+\*\?\^\$\(\)\[\]\{\}\\])", r"\\\1", orig_internal_link)
      orig_internal_link = re.sub(r"[ _]", "[ _]", orig_internal_link)
      orig_internal_link = re.sub(r"^(\w)", 
        lambda x: f"[{x.group(1).capitalize()}{x.group(1).lower()}]", 
        orig_internal_link)
      search_regex_1 = re.compile(f"\[\[\s*?{orig_internal_link}\s*\]\]")
      search_regex_2 = re.compile(f"\[\[\s*?{orig_internal_link}\s*\|(.+?)\]\]")
      str_page = search_regex_1.sub(
        f"{{{{Singer|{new_internal_link}}}}}", 
        str_page)
      str_page = search_regex_2.sub(
        lambda x: f"{{{{Singer|{new_internal_link}|{x.group(1)}}}}}", 
        str_page)
    return str_page

  """Change the internal link to a producer"""
  def move_producer_category(self, str_page, old_producer_alias, new_producer_alias, bool_changeredirect, bool_showoldlinkcap):

    old_maincat = f"{old_producer_alias} songs list"
    new_maincat = f"{new_producer_alias} songs list"
    
    #Compile regex
    regex_pattern = re.sub(r"([\.\+\*\?\^\$\(\)\[\]\{\}\\])", r"\\\1", old_maincat)
    regex_pattern = re.sub(r"[ _]", "[ _]", regex_pattern)
    regex_pattern = re.sub(r"^(\w)", 
      lambda x: "[" + x.group(1).capitalize() + x.group(1).lower() + "]", 
      regex_pattern)
    regex_pattern = f"\[\[Category:{regex_pattern}([^\[\]]*)\]\]"
    search_regex = re.compile(regex_pattern, re.DOTALL)
        
    #Replace category
    str_page = search_regex.sub(lambda match: "[[Category:" + new_maincat + match.group(1) + "]]", str_page)
    #Replace producer redirect if specified
    if bool_changeredirect:
      str_page = self.change_internal_link_address(
        str_page, old_producer_alias, new_producer_alias, 
        old_producer_alias if bool_showoldlinkcap else "")
      str_page = self.change_internal_link_address(
        str_page, f":Category:{old_maincat}", new_producer_alias, 
        old_producer_alias if bool_showoldlinkcap else "")
        
    return str_page
  
  """Change the internal link to a vocal synth"""
  def move_singer_category(self, str_page, old_singer_cat, new_singer_cat):
      
    # Compile regex
    regex_pattern = re.sub(r"([\.\+\*\?\^\$\(\)\[\]\{\}\\])", r"\\\1", f"featuring {old_singer_cat}")
    regex_pattern = re.sub(r"[ _]", "[ _]", regex_pattern)
    regex_pattern = re.sub(r"^(\w)", 
      lambda x: f"[{x.group(1).capitalize()}{x.group(1).lower()}]", 
      regex_pattern)
    regex_pattern = f"\[\[Category:(Songs|Albums)[ _]{regex_pattern}([^\[\]]*)\]\]"
    search_regex = re.compile(regex_pattern, re.DOTALL)
        
    # Replace category
    str_page = search_regex.sub(lambda match: f"[[Category:{match.group(1)} featuring {new_singer_cat}{match.group(2)}]]", str_page)

    # Replace singer redirect
    regex_pattern = re.sub(r"([\.\+\*\?\^\$\(\)\[\]\{\}\\])", r"\\\1", old_singer_cat)
    regex_pattern = re.sub(r"[ _]", "[ _]", regex_pattern)
    regex_pattern = re.sub(r"^(\w)", 
      lambda x: f"[{x.group(1).capitalize()}{x.group(1).lower()}]", 
      regex_pattern)
    regex_pattern = f"\[\[{regex_pattern}\s*\]\]"
    search_regex = re.compile(regex_pattern, re.DOTALL)
    singer_disambig_redirect = re.match(r"^(.*) \((.*?)\)$", new_singer_cat)
    repl = f"[[{new_singer_cat}]]" if singer_disambig_redirect is None else f"[[{new_singer_cat}|{singer_disambig_redirect.group(1)}]]"
    str_page = search_regex.sub(repl, str_page)
        
    return str_page

  def treat_page(self) -> None:

    curpage = self.current_page
    str_page = curpage.text
    title = curpage.title()

    default_summary_text = ""

    if self.opt.chardisambig:

      list_categories = list(map(lambda catobj: re.sub(r"^Category:", "", catobj.title()), curpage.categories()))

      base_voicebank = self.opt.basevb
      synth_family = self.opt.synth

      default_summary_text = f"Changed link [[{base_voicebank}]] -> [[{base_voicebank} ({synth_family})]]"

      str_page = self.change_vocalist_disambig(str_page, list_categories, base_voicebank, synth_family)
    
    elif self.opt.moveprodcat:

      old_producer_alias = self.opt.old
      new_producer_alias = self.opt.new
      bool_changeredirect = self.opt.changeprodredirect
      bool_showoldlinkcap = self.opt.keeplinkcap

      default_summary_text = f"Changed category [[Category:{old_producer_alias} songs list]] -> [[Category:{new_producer_alias} songs list]]"
      str_page = self.move_producer_category(str_page, old_producer_alias, new_producer_alias, bool_changeredirect, bool_showoldlinkcap)
    
    elif self.opt.movesingercat:

      old_singer = self.opt.old
      new_singer = self.opt.new
      #bool_album_mode = self.opt.album
      is_album = title.endswith("(album)")
      default_summary_text = f"Changed category [[Category:{'Albums' if is_album else 'Songs'} featuring {old_singer}]] -> [[Category:{'Albums' if is_album else 'Songs'} featuring {new_singer}]]"
      str_page = self.move_singer_category(str_page, old_singer, new_singer)

    else:

      orig_internal_link = self.opt.old
      new_internal_link = self.opt.new
      new_link_text = self.opt.linkcap

      default_summary_text = f"Changed link [[{orig_internal_link}]] -> [[{new_internal_link}]]"

      str_page = self.change_internal_link_address(str_page, orig_internal_link, new_internal_link, new_link_text)

    self.put_current(str_page, summary=default_summary_text)
    return 


def main(*args: str) -> None:
  """
  Process command line arguments and invoke bot.

  If args is an empty list, sys.argv is used.

  :param args: command line arguments
  """
  options = {}
  # Process global arguments to determine desired site
  local_args = pywikibot.handle_args(args)

  # This factory is responsible for processing command line arguments
  # that are also used by other scripts and that determine on which pages
  # to work on.
  gen_factory = pagegenerators.GeneratorFactory()

  # Process pagegenerators arguments
  local_args = gen_factory.handle_args(local_args)

  # Parse your own command line arguments
  for arg in local_args:
    arg, _, value = arg.partition(':')
    option = arg[1:]

    # User options for bot
    if option in ('chardisambig', 'basevb', 'synth', 'old', 'new', 'linkcap', 'moveprodcat', 'changeprodredirect', 'keeplinkcap', 'movesingercat', 'album'):
      if option in ('chardisambig', 'moveprodcat', 'changeprodredirect', 'keeplinkcap', 'movesingercat', 'album'):
        options[option] = True
      elif not value:
        pywikibot.input(f"Please enter a value for {arg}")
      else:
        options[option] = value

    # take the remaining options as booleans.
    # You will get a hint if they aren't pre-defined in your bot class
    else:
      options[option] = True

  main_command = ''
  for key in ['chardisambig', 'moveprodcat', 'movesingercat']:
    if key in options.keys():
      main_command = key
      break

  if main_command == 'moveprodcat':
    if (options['old'] == "" or options['new'] == ""):
      prError("<<red>>PLEASE ADD PARAMETERS -OLD AND -NEW<<default>>")
      return
    #Get list of pages to process
    gen_factory = pagegenerators.GeneratorFactory()
    gen_factory.handle_arg(f"-cat:{options['old']} songs list")
    for item in ["/Albums", "/Lyrics", "/Arrangement", "/Tuning", "/Visuals", "/Other"]:
      gen_factory.handle_arg(f"-cat:{options['old']} songs list{item}")

  elif main_command == 'movesingercat':
    if (options['old'] == "" or options['new'] == ""):
      prError("<<red>>PLEASE ADD PARAMETERS -OLD AND -NEW<<default>>")
      return
    #Get list of pages to process
    gen_factory = pagegenerators.GeneratorFactory()
    gen_factory.handle_arg(f"-cat:Songs featuring {options['old']}")
    gen_factory.handle_arg(f"-cat:Albums featuring {options['old']}")

  elif main_command == 'chardisambig':
    #Get list of pages to process
    gen_factory = pagegenerators.GeneratorFactory()
    gen_factory.handle_arg(f"-cat:Songs featuring {options['basevb']} ({options['synth']})")
    gen_factory.handle_arg(f"-cat:Albums featuring {options['basevb']} ({options['synth']})")

  # The preloading option is responsible for downloading multiple
  # pages from the wiki simultaneously.
  gen = gen_factory.getCombinedGenerator(preload=True)

  # check if further help is needed
  if not pywikibot.bot.suggest_help(missing_generator=not gen):
    # pass generator and private options to the bot
    bot = LinkEditorBot(generator=gen, **options)
    if not bot.opt.chardisambig and (bot.opt.old == "" or bot.opt.new == ""):
      prError("<<red>>PLEASE ADD PARAMETERS -OLD AND -NEW<<default>>")
      return
    elif bot.opt.chardisambig and (bot.opt.basevb == "" or bot.opt.synth == ""):
      prError("<<red>>PLEASE ADD PARAMETERS -BASEVB AND -SYNTH<<default>>")
      return
    bot.run()


if __name__ == '__main__':
  main()
