/**
 * This is a bot script used to list pages existing in specified categories in the Vocaloid Lyrics Wiki
 * Functionally the same as listpages.py on pywikibot:
 * https://www.mediawiki.org/wiki/Manual:Pywikibot/listpages.py
 * 
 * Prerequisites:
 *   - Add wiki credentials to credentials/profiles.json [with the profile name/key `live`], OR 
 *     add wiki credentials to environment variables
 *   - Set PROFILE= in the environment variables if using a profile other than `live`
 * 
 * Usage:
 *   node listpages.ts "<list>" [--namespaces <list>] [--as-pageid]
 * Arguments:
 *   --namespaces   Comma-separated list of namespaces (numerical IDs) of pages to query
 *   --as-pageid    Only export page IDs (default: title)
 * 
 * Example:
 *   node listpages.ts "Songs featuring VOICEPEAK Female 2, Demonstrations"
 *      List songs in Category:Songs featuring VOICEPEAK Female 2 OR Category:Demonstrations
 *   node listpages.ts "Songs featuring VOICEPEAK Female 2, Demonstrations" --namespaces "0"
 *   node listpages.ts "Templates" --namespaces "10,828"
 */
import "dotenv/config";
import minimist from "minimist";

import { Mwn } from "mwn";
import type { ApiResponse } from "mwn";
import http from "http";
import https from "https";
import axios from "axios";
import { writeFile } from "fs/promises";
import { readWikiProfiles, integratedLogin } from "./util.ts";

interface IPageListerCliOptions {
  categories: string[]
  namespaces?: string[]
  asPageId: boolean
}

function parseArguments(): IPageListerCliOptions {
  const argv = minimist(process.argv.slice(2));
  const options: IPageListerCliOptions = { 
    categories: [],
    asPageId: false,
  };
  if (argv['_'][0]) {
    options['categories'] = argv['_'][0].trim().split(/\s*,\s*/);
  }
  if (argv['namespaces']) {
    options['namespaces'] = String(argv['namespaces'] as string)
      .trim()
      .split(/\s*,\s*/)
      .filter(i => !isNaN(+i));
  }
  if (argv['as-pageid']) {
    options['asPageId'] = true;
  }
  return options;
}

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
  const args = parseArguments();
  if (args.categories.length === 0) {
    Mwn.log('[E] At least one category must be listed!');
    return;
  }

  const bot = await initBot();

  const generators = args.categories.map(category => {
    const opts: Record<string, string> = {
      action: 'query',
      format: 'json',
      list: 'categorymembers',
      cmtitle: `Category:${category}`,
      cmprop: 'ids|title',
      cmlimit: 'max',
    };
    if (args.namespaces) {
      opts['cmnamespace'] = args.namespaces.join('|');
    }
    return bot.continuedQueryGen(opts);
  });

  const writeToFilename = `./list-pages.txt`;
  await writeFile(writeToFilename, '', { flag: 'w', encoding: 'utf-8' });

  const handle = async (json: ApiResponse) => {
    if (!json.query) {
      Mwn.log(`Error, got response: ${json}`);
      return;
    }
    let pageOutputs = json.query.categorymembers
      .map(({ pageid, title }: { pageid: number, ns: number, title: string }) => {
        return args.asPageId ? pageid : title;
      }).filter((s: string | null) => s !== null);
    Mwn.log(`Writing to ${writeToFilename}`);
    await writeFile(writeToFilename, pageOutputs.join('\n') + '\n', { flag: 'a+', encoding: 'utf-8' });
  }
  for (const generator of generators) {
    await (async () => {
      for await (let json of generator as AsyncGenerator<ApiResponse>) {
        await handle(json);
      }
    })();
  }
}

main();