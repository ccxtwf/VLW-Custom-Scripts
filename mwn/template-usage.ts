import "dotenv/config";

import { Mwn } from "mwn";
import http from "http";
import https from "https";
import axios from "axios";
import { writeFileSync } from "fs";
import { readWikiProfiles, integratedLogin } from "./util.ts";

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
    console.log("Setting HTTP Request Agent to not reject unauthorized requests. Do not do this on a production environment.");
    const httpAgent = new http.Agent({ keepAlive: true });
    const httpsAgent = new https.Agent({ keepAlive: true, rejectUnauthorized: false });
    axios.defaults.httpAgent = httpAgent;
    axios.defaults.httpsAgent = httpsAgent;
    bot.setRequestOptions({ httpAgent, httpsAgent });
  }

  await integratedLogin(bot);
  
  return bot;
}

interface TemplateUsage { 
  pageid: number
  ns: number
  title: string
  usage: number
}

async function main() {
  const bot = await initBot();
  const o: Record<number, TemplateUsage> = {};
  const templateTitles: string[] = (await bot.continuedQuery({
    action: 'query',
    format: 'json',
    list: 'allpages',
    // apnamespace: '10',
    apnamespace: '828',
    aplimit: '500',
  })).map(({ query: { allpages = [] } = {} }) => allpages.map(({ title }: { title: string }) => title)).flat();
  // console.log(templateTitles);
  console.log(`Got ${templateTitles.length} template titles`);

  await bot.batchOperation(
    templateTitles,
    async (page) => {
      const templateUsageGen = bot.continuedQueryGen({
        action: 'query',
        format: 'json',
        prop: 'transcludedin',
        tiprop: 'pageid', 
        tishow: '!redirect',
        tilimit: '500', 
        tinamespace: '0',
        titles: page,
      });
      for await (const templateUsage of templateUsageGen) {
        for (const page of templateUsage?.query?.pages || []) {
          const { pageid, ns, title, transcludedin = [] } = page as { pageid: number, ns: number, title: string, transcludedin?: { pageid: number }[] };
          if (o[pageid] === undefined) {
            o[pageid] = { pageid, ns, title, usage: 0 };
          }
          o[pageid].usage += transcludedin.length;
        }
      }
    },
    /* concurrency */ 5,
    /* retries */ 2
  );

  const res: TemplateUsage[] = Object.values(o).sort((a, b) => b.usage - a.usage);
  console.log(`Queried ${res.length} templates`);
  writeFileSync('./module-usage.log', JSON.stringify(res), { encoding: 'utf-8', flag: 'w' });
}

main();