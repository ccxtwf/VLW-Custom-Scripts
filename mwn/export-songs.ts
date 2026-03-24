import "dotenv/config";

import { Mwn } from "mwn";
import type { ApiResponse } from "mwn";
import http from "http";
import https from "https";
import axios from "axios";
import { writeFile } from "fs/promises";
import { styleText } from "util";

const folderDir = process.env.EXPORT_DUMP_TO_DIRECTORY || __dirname;

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

async function main() {
  const bot = await initBot();
  const pagesInCategory = bot.continuedQueryGen({
    action: 'query',
    format: 'json',
    generator: 'categorymembers',
    gcmtitle: 'Category:Songs',
    gcmnamespace: 0,
    gcmprop: 'ids|title|sortkeyprefix',
    gcmlimit: 'max',
    gcmsort: 'timestamp',
    export: true
  });
  let numPages = 0;
  for await (let json of pagesInCategory as AsyncGenerator<ApiResponse>) {
    if (!json.query) {
      console.error(`Error, got response: ${json}`);
      return;
    }
    const xml = json.query.export;
    const writeToFilename = `${folderDir}/exported-vlw-songs-${++numPages}.xml`;
    console.log(styleText('magenta', `Writing ${writeToFilename}`));
    await writeFile(writeToFilename, xml, { flag: 'w', encoding: 'utf-8' });
  }
}

main();