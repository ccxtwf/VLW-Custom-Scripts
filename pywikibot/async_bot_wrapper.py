#!/usr/bin/env python3
import pywikibot
from pywikibot import pagegenerators
import asyncio

from typing import Callable, Tuple, List, Any, Optional
from enum import Enum

import abc
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

class AsyncBotWrapper:
  __metaclass__ = abc.ABCMeta

  lock: asyncio.Lock
  edited_pages: List[str]
  error_pages: List[Tuple[str, str]]
  collected_results_on_success: List[Tuple[str, Any]]
  collected_results_on_failure: List[Tuple[str, Any]]
  queue: asyncio.Queue
  num_consumers: int

  def __init__(self, generator: pagegenerators.Generator, queue_size: int | None, num_consumers: int = 50):
    self.generator = generator
    self.lock = asyncio.Lock()
    self.edited_pages = []
    self.error_pages = []
    self.collected_results_on_success = []
    self.collected_results_on_failure = []
    self.queue = asyncio.Queue(queue_size)
    self.num_consumers = num_consumers

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

  @abc.abstractmethod
  async def treat_one_page(self, page: pywikibot.Page) -> Tuple[Optional[bool], Optional[str], Optional[str], Optional[Any], Optional[Any]]:
    """
    Override this method to determine how to process each page. 
    
    Set the new page contents to page.text, then use page.save(summary) to save the changes.

    This method should return a tuple of five values: is_page_edited (bool), page_title (str), error_message (str), optional payload on success, optional payload on failure
    """
    return

  @abc.abstractmethod
  async def run_on_termination(self):
    """
    Override this method to set the callback to run just before bot termination.
    """
  
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
      is_edited, page_title, err_message, payload_on_success, payload_on_failure = results
      if is_edited is not None:
        async with self.lock:
          if is_edited:
            self.edited_pages.append(page_title)
          if err_message is not None:
            self.error_pages.append((page_title, err_message))
          if payload_on_success is not None:
            self.collected_results_on_success.append((page_title, payload_on_success))
          if payload_on_failure is not None:
            self.collected_results_on_failure.append((page_title, payload_on_failure))
      self.queue.task_done()

  async def run_async(self):
    producer = asyncio.create_task(self.run_task_producer())
    consumers = [asyncio.create_task(self.run_task_consumer()) for _ in range(self.num_consumers)]
    await producer
    await self.queue.join()
    for consumer in consumers:
      consumer.cancel()
    if (len(self.error_pages) > 0):
      self.log(f"The following pages need intervention", ENUM_LOGGER_STATES.error)
      self.log("\n".join(map(
        lambda tpl: f"{tpl[0]}\t{ENUM_ANSI_COLOURS.red.value}{tpl[1]}{ENUM_ANSI_COLOURS.default.value}", 
        self.error_pages)))
    if (len(self.edited_pages) > 0):
      self.log(f"{ENUM_ANSI_COLOURS.magenta.value}Finished editing the following pages:{ENUM_ANSI_COLOURS.default.value}")
      self.log("\n".join(self.edited_pages))
    await self.run_on_termination()

  @countElapsedTime
  def run(self):
    asyncio.run(self.run_async())