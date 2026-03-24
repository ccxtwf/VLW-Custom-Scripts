import "dotenv/config";

import { Mwn } from "mwn";
import type { ApiResponse } from "mwn";
import http from "http";
import https from "https";
import axios from "axios";
import { writeFile } from "fs/promises";
import { styleText } from "util";
// import { styleText } from "util";

const folderDir = process.env.EXPORT_DUMP_TO_DIRECTORY || __dirname;

const EDIT_RATE_PER_MILLISECONDS = 1000;

async function initBot() {
  const bot = new Mwn({
    apiUrl: process.env.WIKI_API_URL,
    username: process.env.BOT_USERNAME,
    password: process.env.BOT_PASSWORD,
    userAgent: process.env.BOT_USERAGENT,
    silent: true,       // suppress messages (except error messages)
    retryPause: 5000,   // pause for 5000 milliseconds (5 seconds) on maxlag error.
    maxRetries: 5,      // attempt to retry a failing requests upto 3 times
    defaultParams: {
      assert: 'bot',    // assert logged in as bot
    }
  });

  if (process.env.ENV_REJECT_UNAUTHORIZED === '0') {
    console.log("Setting HTTP Request Agent to not reject unauthorized requests. Do not do this on a production environment.");
    const httpAgent = new http.Agent({ keepAlive: true });
    const httpsAgent = new https.Agent({ keepAlive: true, rejectUnauthorized: false });
    axios.defaults.httpAgent = httpAgent;
    axios.defaults.httpsAgent = httpsAgent;
    bot.setRequestOptions({ httpAgent, httpsAgent });
  }

  console.log(`Logging into ${process.env.WIKI_API_URL} as ${process.env.BOT_USERNAME}`);
  await bot.login({
    apiUrl: process.env.WIKI_API_URL,
    username: process.env.BOT_USERNAME,
    password: process.env.BOT_PASSWORD,
  });
  return bot;
}

async function nullEditSinglePage(bot: Mwn, pageid: number, title: string) {
  try {
    const token = await bot.getCsrfToken();
    await bot.request({
      action: 'edit',
      summary: 'Null edit (this edit should not be visible)',
      pageid,
      notminor: true,
      prependtext: '',
      nocreate: true,
      token,
      assert: 'bot',
    });
    console.log(`Successfully saved "${title}"`);
  } catch (err) {
    const errorCode = err?.response?.data?.error?.code; 
    if (errorCode === 'ratelimited') {
      console.log(styleText('magenta', 'Rate limited. Sleeping for 5000 ms...'));
      await bot.sleep(5000);
      await nullEditSinglePage(bot, pageid, title);
    } else if (errorCode === 'protectedpage') {
      console.log(styleText('red', `"${title}" is protected.`));
    } else {
      console.log(styleText('red', `Unable to edit "${title}"`));
      console.error(err);
    }
  }
}

async function getApiLimits(bot: Mwn) {
  const ratelimits = await bot.request({
    action: 'query',
    meta: 'userinfo',
    uiprop: 'ratelimits'
  });
  console.log(`Logged in as: ${ratelimits.query!.userinfo!.name}`);
  console.log(ratelimits.query!.userinfo!.ratelimits);
}

async function main() {
  const bot = await initBot();
  
  await getApiLimits(bot);

  const pagesInCategory = bot.continuedQueryGen({
    action: 'query',
    format: 'json',
    list: 'allrevisions',
    arvlimit: 'max',
    arvdir: 'newer',
    // arvstart: '2026-02-15T00:00:00Z',
    // arvend: '2026-02-17T00:00:00Z',
  });

  const writeToFilename = `${folderDir}/list-null-edit.log`;
  await writeFile(writeToFilename, '', { flag: 'w', encoding: 'utf-8' });

  for await (let json of pagesInCategory as AsyncGenerator<ApiResponse>) {
    if (!json.query) {
      console.error(`Error, got response: ${json}`);
      return;
    }
    const pages = json.query.allrevisions;
    const saveTitles = [];
    for (const { pageid, title } of pages) {
      await nullEditSinglePage(bot, pageid, title);
      await bot.sleep(EDIT_RATE_PER_MILLISECONDS);
      saveTitles.push(title);
    }
    await writeFile(writeToFilename, saveTitles.join('\n') + '\n', { flag: 'a', encoding: 'utf-8' });
  }
}

main();