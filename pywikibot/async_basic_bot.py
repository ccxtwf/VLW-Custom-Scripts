#!/usr/bin/env python3
"""An incomplete sample script.

This is not a complete bot; rather, it is a template from which simple
bots can be made. You can rename it to mybot.py, then edit it in
whatever way you want.
"""

import pywikibot
from pywikibot import pagegenerators
import asyncio

from typing import Callable, List, Tuple, Optional
from enum import Enum

from time import time

# MAXIMUM SIZE OF QUEUE OF TASKS
CONST_QUEUE_SIZE = 500
# NUMBER OF ASYNCHRONOUS THREADS RUNNING AT A SINGLE TIME (ONE THREAD PROCESSES AND SAVES EACH PAGE)
CONST_NUM_TASK_CONSUMERS = 50

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

class AsyncBot:
  site: pywikibot._BaseSite
  lock: asyncio.Lock
  edited_pages: List[str]
  error_pages: List[str]
  queue: asyncio.Queue

  CONST_EDIT_SUMMARY = "BOT: Save Summary"

  def __init__(self, generator: pagegenerators.Generator, **kwargs):
    self.generator = generator
    self.lock = asyncio.Lock()
    self.edited_pages = []
    self.error_pages = []
    self.queue = asyncio.Queue(CONST_QUEUE_SIZE)

  def log(self, message: str, status: ENUM_LOGGER_STATES = ENUM_LOGGER_STATES.log) -> None:
    if status == ENUM_LOGGER_STATES.log:
      print(message)
    elif status == ENUM_LOGGER_STATES.output:
      print(f"{ENUM_ANSI_COLOURS.green.value}{message}{ENUM_ANSI_COLOURS.default.value}")
    elif status == ENUM_LOGGER_STATES.warn:
      print(f"{ENUM_ANSI_COLOURS.yellow.value}{message}{ENUM_ANSI_COLOURS.default.value}")
    elif status == ENUM_LOGGER_STATES.error:
      print(f"{ENUM_ANSI_COLOURS.red.value}{message}{ENUM_ANSI_COLOURS.default.value}")
    else:
      print(message)

  async def treat_one_page(self, page: pywikibot.Page) -> Tuple[Optional[bool], Optional[str], Optional[str]]:
    if page is None: 
      return (None, None, None)
    is_edited = False
    err_message = None
    page_title = None
    try:
      page_title = page.title()
      if not page.exists():
        raise PageNotFoundException("Page doesn't exist")
      elif page.isRedirectPage():
        raise PageNotFoundException("Page is a redirect")
      page_contents = page.text

      #Process page contents/redirects/etc.
      
      is_edited = True
    except Exception as e:
      err_message = str(e)
      self.log(f"[{page_title}]\t{err_message}", ENUM_LOGGER_STATES.error)
    
    finally:
      if not is_edited:
        return (is_edited, page_title, err_message)
      page.text = page_contents
      page.save(
        summary=self.CONST_EDIT_SUMMARY, 
        watch="nochange", 
        minor=False, 
        botflag=False,
        asynchronous=True
      )
      return (True, page_title, err_message)
  
  async def run_task_producer(self):
    while True:
      try:
        cur = next(self.generator)
        await self.queue.put(cur)
      except StopIteration:
        break
  
  async def run_task_consumer(self):
    while True:
      page: pywikibot.Page
      page = await self.queue.get()
      results = await self.treat_one_page(page)
      is_edited, page_title, err_message = results
      if is_edited is not None:
        async with self.lock:
          if is_edited:
            self.edited_pages.append(page_title)
          if err_message is not None:
            self.error_pages.append((page_title, err_message))
      self.queue.task_done()

  async def run_async(self):
    producer = asyncio.create_task(self.run_task_producer())
    consumers = [asyncio.create_task(self.run_task_consumer()) for _ in range(CONST_NUM_TASK_CONSUMERS)]
    await producer
    await self.queue.join()
    for consumer in consumers:
      consumer.cancel()
    if (len(self.error_pages) > 0):
      self.log(f"The following pages need intervention", ENUM_LOGGER_STATES.error)
      self.log("\n".join(self.error_pages))
    if (len(self.edited_pages) > 0):
      self.log(f"{ENUM_ANSI_COLOURS.magenta.value}Finished editing the following pages:{ENUM_ANSI_COLOURS.default.value}")
      self.log("\n".join(self.edited_pages))

  @countElapsedTime
  def run(self):
    asyncio.run(self.run_async())

if __name__ == "__main__":
  options = {}
  # Process global arguments to determine desired site
  local_args = pywikibot.handle_args()

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
    if option in ('summary', 'text'):
      if not value:
        pywikibot.input('Please enter a value for ' + arg)
      options[option] = value
    # take the remaining options as booleans.
    # You will get a hint if they aren't pre-defined in your bot class
    else:
      options[option] = True

  # The preloading option is responsible for downloading multiple
  # pages from the wiki simultaneously.
  gen = gen_factory.getCombinedGenerator(preload=True)

  # check if further help is needed
  if not pywikibot.bot.suggest_help(missing_generator=not gen):
    # pass generator and private options to the bot
    bot = AsyncBot(generator=gen, **options)
    bot.run()  # guess what it does