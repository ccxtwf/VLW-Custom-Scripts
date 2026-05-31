/**
 * This is a bot script used to null edit pages in the Vocaloid Lyrics Wiki
 * Functionally the same as touch.py on pywikibot:
 * https://www.mediawiki.org/wiki/Manual:Pywikibot/touch.py
 * 
 * Prerequisites:
 *   - Add wiki credentials to credentials/profiles.json [with the profile name/key `live`], OR 
 *     add wiki credentials to environment variables
 *   - Set PROFILE= in the environment variables if using a profile other than `live`
 * 
 * Usage:
 *   node null-edit.ts [--from <timestamp>] [--to <timestamp>] [--namespaces <list>]
 * Arguments:
 *   --from         ISO Timestamp of pages to edit
 *   --to         
 *   --namespaces   Comma-separated list of namespaces (numerical IDs) of pages to query
 * 
 * Example:
 *   node null-edit.ts --from 2026-05-29T00:00:00Z --to 2026-05-29T04:00:00Z
 */
import "dotenv/config";
import minimist from "minimist";

import { Mwn } from "mwn";
import type { ApiResponse } from "mwn";
import http from "http";
import https from "https";
import axios from "axios";
import { readWikiProfiles, integratedLogin } from "./util.ts";

interface INullEditBotCliArguments {
  from?: string
  to?: string
  namespaces?: string[]
  hasArgs: boolean
}

function parseArguments(): INullEditBotCliArguments {
  const argv = minimist(process.argv.slice(2));
  const options: INullEditBotCliArguments = { 
    hasArgs: false
  };
  ['from', 'to', 'namespaces'].forEach((k) => {
    if (argv[k]) {
      if (k === 'namespaces') {
        options[k] = String(argv[k]).trim().split(/\s*,\s*/);
      } else {
        options[k as 'from' | 'to'] = argv[k];
      }
      options.hasArgs = true;
    }
  });
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
    Mwn.log("[W] Setting HTTP Request Agent to not reject unauthorized requests. Do not do this on a production environment.");
    const httpAgent = new http.Agent({ keepAlive: true });
    const httpsAgent = new https.Agent({ keepAlive: true, rejectUnauthorized: false });
    axios.defaults.httpAgent = httpAgent;
    axios.defaults.httpsAgent = httpsAgent;
    bot.setRequestOptions({ httpAgent, httpsAgent });
  }

  await integratedLogin(bot);
  
  return bot;
}

async function nullEditSinglePage(bot: Mwn, title: string) {
  try {
    const token = await bot.getCsrfToken();
    await bot.request({
      action: 'edit',
      summary: 'Null edit (this edit should not be visible)',
      title,
      notminor: true,
      prependtext: '',
      nocreate: true,
      token,
      assert: 'bot',
    });
    Mwn.log(`[S] Successfully null edited "${title}"`);
  } catch (err) {
    const errorCode = err?.response?.data?.error?.code; 
    if (errorCode === 'ratelimited') {
      Mwn.log('[E] Rate limited. Sleeping for 5000 s...');
      await bot.sleep(5000);
      throw err;
    } else if (errorCode === 'protectedpage') {
      Mwn.log(`[E] "${title}" is protected.`);
    } else {
      Mwn.log(`[E] Unable to edit "${title}"`);
      Mwn.log(err);
    }
  }
}

async function main() {
  const args = parseArguments();
  const bot = await initBot();

  if (!args.hasArgs) {
    Mwn.log(`[E] Must specify 'from', 'to', or 'namespaces' of pages to edit`);
    return;
  }

  const generator = (() => {
    const opts: Record<string, string> = {
      action: 'query',
      format: 'json',
      list: 'allrevisions',
      arvlimit: 'max',
      arvdir: 'newer',
    };
    if (args.from) {
      opts['arvstart'] = args.from;
    }
    if (args.to) {
      opts['arvend'] = args.to;
    }
    if (args.namespaces) {
      opts['arvnamespace'] = args.namespaces.join('|'); 
    }
    return bot.continuedQueryGen(opts);
  })();

  for await (let json of generator as AsyncGenerator<ApiResponse>) {
    if (!json.query) {
      console.error(`Error, got response: ${json}`);
      return;
    }
    const pages = json.query.allrevisions;
    const titles = pages.map(({ title }: { title: string }) => title);
    
    await bot.batchOperation(
      titles,
      async (title: string) => {
        try {
          await nullEditSinglePage(bot, title);
          await bot.sleep(1500);
        } catch (err) {
          Mwn.log(err);
        }
      },
      /* concurrency */ 1,
      /* retries */ 3
    );
  }
}

main();