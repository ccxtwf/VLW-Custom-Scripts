import "dotenv/config";

import { Mwn } from "mwn";
import type { ApiResponse } from "mwn";
import http from "http";
import https from "https";
import axios from "axios";
import { writeFile } from "fs/promises";
import { integratedLogin } from "./util.ts";

async function initBot() {

  //@ts-ignore
  const wikiProfile: WikiProfile = (readWikiProfiles() || {})[process.env.PROFILE || 'live'] || {
    apiEntrypoint: process.env.WIKI_API_URL,
    botUsername: process.env.BOT_USERNAME,
    botPassword: process.env.BOT_PASSWORD,
    oauthToken: process.env.BOT_OAUTH_ACCESS_TOKEN,
    botUseragent: process.env.BOT_USERAGENT,
  };

  const bot = new Mwn({
    ...wikiProfile.miscConfig || {},
    apiUrl: wikiProfile.apiEntrypoint,
    username: wikiProfile.botUsername,
    password: wikiProfile.botPassword,
    OAuth2AccessToken: wikiProfile.oauthToken,
    userAgent: wikiProfile.userAgent,
    silent: true,       // suppress messages (except error messages)
    retryPause: 5000,   // pause for 5000 milliseconds (5 seconds) on maxlag error.
    maxRetries: 5,      // attempt to retry a failing requests upto 3 times
  });

  if (process.env.ENV_REJECT_UNAUTHORIZED === '0') {
    Mwn.log("Setting HTTP Request Agent to not reject unauthorized requests. Do not do this on a production environment.");
    const httpAgent = new http.Agent({ keepAlive: true });
    const httpsAgent = new https.Agent({ keepAlive: true, rejectUnauthorized: false });
    axios.defaults.httpAgent = httpAgent;
    axios.defaults.httpsAgent = httpsAgent;
    bot.setRequestOptions({ httpAgent, httpsAgent });
  }

  await integratedLogin(bot);
  
  return bot;
}

async function main() {
  const bot = await initBot();
  const demoPagesInCategory = bot.continuedQueryGen({
    action: 'query',
    format: 'json',
    list: 'categorymembers',
    cmtitle: 'Category:Demonstrations',
    cmnamespace: 0,
    cmprop: 'ids|title',
    cmlimit: 'max',
  });
  const abPagesInCategory = bot.continuedQueryGen({
    action: 'query',
    format: 'json',
    list: 'categorymembers',
    cmtitle: 'Category:Album Only songs',
    cmnamespace: 0,
    cmprop: 'ids|title',
    cmlimit: 'max',
  });

  const excludeTheseIds = new Set<number>();
  
  const writeToFilename = `${__dirname}/list-pages.txt`;
  await writeFile(writeToFilename, '', { flag: 'w', encoding: 'utf-8' });

  const handle = async (json: ApiResponse, excludeTheseIds: Set<number>, writeToSet: boolean) => {
    if (!json.query) {
      Mwn.log(`Error, got response: ${json}`);
      return;
    }
    let pageIds = json.query.categorymembers
      .map(({ pageid, title }: { pageid: number, ns: number, title: string }) => {
        if (excludeTheseIds.has(pageid)) {
          Mwn.log(`Excluding ${title}`);
          return null;
        }
        if (writeToSet) {
          excludeTheseIds.add(pageid);
        }
        // return `[[${title}]]`;
        return pageid;
      }).filter((s: string | null) => s !== null);
    Mwn.log(`Writing to ${writeToFilename}`);
    await writeFile(writeToFilename, pageIds.join('\n') + '\n', { flag: 'a+', encoding: 'utf-8' });
  }
  for await (let json of demoPagesInCategory as AsyncGenerator<ApiResponse>) {
    await handle(json, excludeTheseIds, true);
  }
  for await (let json of abPagesInCategory as AsyncGenerator<ApiResponse>) {
    await handle(json, excludeTheseIds, false);
  }
}

main();