import "dotenv/config";
import minimist from "minimist";
import deepmerge from "deepmerge";
import { createInterface } from "readline";

const argv = minimist(process.argv.slice(2));

import { Mwn } from "mwn";
import type { ApiResponse } from "mwn";
import { styleText } from "util";

import { readWikiProfiles } from "./util.ts";
import type { WikiProfile } from "./util.ts";

interface ITemplateSyncerCliOptions {
  namespaces: ('Template' | 'Module' | 'MediaWiki')[]
  list?: string[]
  from: string
  to: string
  comment?: string
}

function parseArguments(): ITemplateSyncerCliOptions {
  const options: ITemplateSyncerCliOptions = { 
    namespaces: ['Template', 'Module', 'MediaWiki'],
    from: argv['_'][0],
    to: argv['_'][1],
  };
  if (!!argv['namespaces']) {
    options.namespaces = (argv['namespaces'] as string)
      .split(/\s*,\s*/)
      .filter(item => item.match(/[Tt]emplate|[Mm]odule|[M]edia[Ww]iki/) !== null)
      .map(item => ({ 'template': 'Template', 'module': 'Module', 'mediawiki': 'MediaWiki' }[item.toLowerCase()]) as 'Template' | 'Module' | 'MediaWiki');
  }
  if (!!argv['list']) {
    options.list = (argv['list'] as string)
      .split(/[ \r\t]*\n+[ \r\t]*/)
      .map(s => s.trim())
      .filter(s => s !== '');
  }
  options.comment = argv['comment'];
  return options;
}

async function initBot(profile: WikiProfile, asSource: boolean) {
  const mwnConfig = deepmerge({
    apiUrl: profile.apiEntrypoint,
    username: profile.botUsername,
    password: profile.botPassword,
    userAgent: profile.botUseragent,
    silent: true,       // suppress messages (except error messages)
    retryPause: 5000,   // pause for 5000 milliseconds (5 seconds) on maxlag error.
    maxRetries: 5,      // attempt to retry a failing requests upto 3 times
  }, profile.miscConfig || {});
  const bot = new Mwn(mwnConfig);
  Mwn.log(`Logging into ${profile.apiEntrypoint} as ${profile.botUsername} [AS ${asSource ? 'SOURCE' : 'TARGET'}]`);
  await bot.login({
    apiUrl: profile.apiEntrypoint,
    username: profile.botUsername,
    password: profile.botPassword,
  });
  return bot;
}

interface PageObject {
  pageid: number
  ns: number
  title: string
  revisions: {
    contentformat: string
    contentmodel: string
    comment: string
    tags: string[]
    content: string
  }[]
}

async function run(copyFromWikiBot: Mwn, copyToWikiBot: Mwn, args: ITemplateSyncerCliOptions) {
  const generators: AsyncGenerator<ApiResponse>[] = [];
  const _defMwApiParams = {
    action: 'query',
    format: 'json',
    prop: 'revisions', 
    rvprop: 'tags|content|comment',
  };
  if (args.list) {
    generators.push(copyFromWikiBot.continuedQueryGen({
      ..._defMwApiParams,
      titles: args.list.join('|'),
    }));
  } else {
    const _nsMap = { Template: 10, Module: 828, MediaWiki: 8, };
    for (const ns of args.namespaces) {
      generators.push(copyFromWikiBot.continuedQueryGen({
        ..._defMwApiParams,
        generator: 'allpages',
        gapnamespace: _nsMap[ns],
        gaplimit: 50, 
      }));
    }
  }

  const handleQuery = async (res: ApiResponse) => {
    if (!res.query || !res.query.pages) {
      Mwn.log(`Error, got response: ${res}`);
      return;
    }

    const [pagelist, pagecache] = (() => {
      const pages = Object.values(res.query.pages);
      const pagelist = pages.map(({ title }: PageObject) => title);
      const cache = pages.reduce((acc: Record<string, PageObject>, page: PageObject) => {
        acc[page.title] = page;
        return acc;
      }, {} as Record<string, PageObject>) as Record<string, PageObject>;
      return [pagelist, cache];
    })();
    
    copyToWikiBot.batchOperation(
      pagelist,
      async (title) => {
        const { revisions } = pagecache[title] as PageObject;
        const { content } = revisions[0];
        Mwn.log(`Editing '${title}'...`);
        await copyToWikiBot.save(title, content, args.comment || 'Copying templates', { minor: false });
        Mwn.log(`Saved '${title}'`);
        // await copyToWikiBot.sleep(THROTTLE);
      },
      /* concurrency */ 3,
      /* retries */ 2
    );
  }

  for (const gen of generators) {
    for await (let json of gen) {
      await handleQuery(json);
    }
  }
}

async function main() {
  const wikiProfiles = readWikiProfiles();
  if (wikiProfiles === null) {
    console.log(styleText('red', 'Failed to read profiles.json in the working directory!'));
    return;
  }
  const args = parseArguments();
  if (!wikiProfiles[args.from] || !wikiProfiles[args.to]) {
    console.log(styleText('red', ''));
    return;
  }

  const copyFromWikiBot = await initBot(wikiProfiles[args.from], true);
  const copyToWikiBot = await initBot(wikiProfiles[args.to], false);

  const prompt = createInterface({ 
    input: process.stdin, 
    output: process.stdout 
  });
  prompt.question(styleText('magenta', `You are about to copy pages from '${args.from}' (${wikiProfiles[args.from].apiEntrypoint}) to '${args.to}' (${wikiProfiles[args.to].apiEntrypoint}). Are you sure you want to continue? [y/n] `), async (answer) => {
    if (answer.toLowerCase().trim() === 'y') {
      await run(copyFromWikiBot, copyToWikiBot, args);
    }
    prompt.close();
  });
}

main();