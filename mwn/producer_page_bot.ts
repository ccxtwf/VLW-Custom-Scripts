/**
 * This is a bot script used to update producer page discography tables in the Vocaloid Lyrics Wiki
 *  
 * Prerequisites:
 *   - Add wiki credentials to credentials/profiles.json [with the profile name/key `live`], OR 
 *     add wiki credentials to environment variables
 *   - Set PROFILE= in the environment variables if using a profile other than `live`
 * 
 * Usage:
 *   node producer_page_bot.ts [--page <PAGE>] [--from <FROM>] [--dry-run]
 * Arguments:
 *   --page     Only update for this page
 *   --from     Update producer pages with titles starting from this string
 *   --dry-run  Simulated run, i.e. run the script without updating anything in the wiki 
 * 
 */
import "dotenv/config";
import minimist from "minimist";

const argv = minimist(process.argv.slice(2));

import { Mwn } from "mwn";
import type { ApiResponse, ApiPage, MwnOptions } from "mwn";
import http from "http";
import https from "https";
import axios from "axios";
import fs from "fs";
import { readWikiProfiles, integratedLogin, setLoggingConfig } from "./util.ts";
import type { WikiProfile } from './util.ts';

import { producerPageBotMixin } from "./producer_page_bot_utils.ts";
import type { IProducerPageBotMixin } from "./producer_page_bot_utils.ts";

const producersWithDiscographySubpages = JSON.parse(fs.readFileSync("./producers_with_split_discographies.json", { encoding: 'utf-8', flag: 'r' }));

const EDIT_SUMMARY = 'Bot: Updating producer page discography';

interface IProducerPageBotCliOptions {
  page?: string
  from?: string
  "dry-run"?: boolean
}

interface IProducerPagesWithDiscogSubpages {
  [producerPageTitle: string]: {
    subpages: string[]
  }
}

interface IProducerPageConfig {
  editSummary: string
  producerPagesWithDiscogSubpages : IProducerPagesWithDiscogSubpages
}

setLoggingConfig({ prefix: 'producer-bot', dualStream: true });

function parseArguments(): IProducerPageBotCliOptions {
  const options: IProducerPageBotCliOptions = {};
  if (!!argv['page']) options.page = argv['page'];
  if (!!argv['from']) options.from = argv['from'];
  if (!!argv['dry-run']) options["dry-run"] = true;
  return options;
}

class ProducerPageBot extends Mwn {
  editSummary: string
  producerPagesWithDiscogSubpages: any
  userOptions: IProducerPageBotCliOptions
  errorPages: [string, string][]

  constructor(options: MwnOptions, config: IProducerPageConfig, cliOptions: IProducerPageBotCliOptions) {
    super(options);
    this.editSummary = config.editSummary;
    this.producerPagesWithDiscogSubpages = config.producerPagesWithDiscogSubpages;
    this.userOptions = cliOptions;
    this.errorPages = [];
  }

  /* Implemented by producerPageBotMixin */
  getProducerCategory = (producerPageBotMixin as IProducerPageBotMixin).getProducerCategory.bind(this);
  filterPagesThatHaveBeenTranscludedUsingRedirects = (producerPageBotMixin as IProducerPageBotMixin).filterPagesThatHaveBeenTranscludedUsingRedirects.bind(this);
  getSongPagesNotOnPage = (producerPageBotMixin as IProducerPageBotMixin).getSongPagesNotOnPage.bind(this);
  getAlbumPagesNotOnPage = (producerPageBotMixin as IProducerPageBotMixin).getAlbumPagesNotOnPage.bind(this);
  updatePwt = (producerPageBotMixin as IProducerPageBotMixin).updatePwt.bind(this);
  updateAwt = (producerPageBotMixin as IProducerPageBotMixin).updateAwt.bind(this);

  async treatPage(this: ProducerPageBot, { title, revisions }: ApiPage): Promise<void> {
    try {
      if (title in producersWithDiscographySubpages) {
        // TODO
        Mwn.log(`[E] ${title}:\t\tSkipped editing the page`);
        this.errorPages.push([title, 'Skipped editing the page']);
        return;
      }

      const pageContents = revisions![0]!.slots!.main!.content!;

      const prodCat = this.getProducerCategory(pageContents);
      Mwn.log(`[I] ${title}: Querying from producer category ${prodCat}`);
      let newPageContents = pageContents;
      const songPagesNotInCategory = await this.getSongPagesNotOnPage(prodCat, title);
      const albumPagesNotInCategory = await this.getAlbumPagesNotOnPage(prodCat, title);
      let editsMade = false;
      if (songPagesNotInCategory.length > 0) {
        Mwn.log(`[I] ${title}: Found ${songPagesNotInCategory.length} song page(s): ${songPagesNotInCategory.join(', ')}`);
        newPageContents = this.updatePwt(newPageContents, songPagesNotInCategory);
        editsMade = true;
      }
      if (albumPagesNotInCategory.length > 0) {
        Mwn.log(`[I] ${title}: Found ${albumPagesNotInCategory.length} album page(s): ${albumPagesNotInCategory.map(([album, isCompilation]: [string, boolean]) => `${album}${isCompilation ? ' [COMPILATION]' : ''}`).join(', ')}`);
        newPageContents = this.updateAwt(newPageContents, albumPagesNotInCategory);
        editsMade = true;
      }
      if (editsMade) {
        if (!!argv['dry-run']) {
          Mwn.log(`[S] Saved page ${title} [DRY RUN - No changes are saved]`);
        } else {
          await this.save(title, newPageContents, EDIT_SUMMARY);
          Mwn.log(`[S] Saved page ${title}`);
        }
      }
    } catch (err) {
      Mwn.log(`[E] ${title}:\t\t${(err as any).error || err}`);
      this.errorPages.push([title, (err as any).error || err]);
    }
  }

  generateReport(this: ProducerPageBot): void {
    if (this.errorPages.length > 0) {
      Mwn.log(`[I] Encountered errors with the following pages:`);
      for (let [page, message] of this.errorPages) {
        Mwn.log(`[E] ${page}:\t\t${message}`);
      }
    }
    Mwn.log(`[S] Finished bot run`);
  }

  async run(this: ProducerPageBot): Promise<void> {
    if (this.userOptions["dry-run"]) {
      Mwn.log(`[I] Running the producer page bot as a simulation. No live changes will be made on the wiki.`);
    }
    if (this.userOptions.page !== undefined) {
      const title = argv['page'];
      this.read(title, { rvprop: ['content'] })
        .then((page: ApiPage) => this.treatPage(page))
        .catch((err: any) => {
          Mwn.log(`[E] ${title}:\t\t${err.error || err}`);
        });
    } else {
      const pagesInCategory = this.continuedQueryGen({
        action: 'query',
        format: 'json',
        generator: 'categorymembers',
        gcmtitle: 'Category:Producers',
        gcmnamespace: 0,
        gcmprop: 'ids|title|sortkeyprefix',
        gcmlimit: 50,
        gcmsort: 'sortkey',
        // @ts-ignore
        gcmstartsortkeyprefix: this.userOptions.from,
        prop: 'revisions',
        rvprop: 'content',
        rvslots: '*'
      });
      for await (let json of pagesInCategory as AsyncGenerator<ApiResponse>) {
        if (!json?.query?.pages) {
          Mwn.log(`[E] Got unexpected response from the API`);
          Mwn.log(json);
          continue;
        }
        for (const page of json.query!.pages) {
          await this.treatPage(page);
        }
      }
    }
  }
}

async function initBot() {
  const cliOptions = parseArguments();

  //@ts-ignore
  const wikiProfile: WikiProfile = (readWikiProfiles() || {})[process.env.PROFILE || 'live'] || {
    apiEntrypoint: process.env.WIKI_API_URL,
    botUsername: process.env.BOT_USERNAME,
    botPassword: process.env.BOT_PASSWORD,
    oauthToken: process.env.BOT_OAUTH_ACCESS_TOKEN,
    botUseragent: process.env.BOT_USERAGENT,
  };

  const bot = new ProducerPageBot({
    ...wikiProfile.miscConfig || {},
    apiUrl: wikiProfile.apiEntrypoint,
    username: wikiProfile.botUsername,
    password: wikiProfile.botPassword,
    OAuth2AccessToken: wikiProfile.oauthToken,
    userAgent: wikiProfile.botUseragent,
    silent: true,       // suppress messages (except error messages)
    retryPause: 5000,   // pause for 5000 milliseconds (5 seconds) on maxlag error.
    maxRetries: 5,      // attempt to retry a failing requests upto 3 times
  }, { 
    editSummary: EDIT_SUMMARY, 
    producerPagesWithDiscogSubpages: producersWithDiscographySubpages as IProducerPagesWithDiscogSubpages
  }, cliOptions);

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

async function main() {
  const bot = await initBot();
  await bot.run();
  bot.generateReport();
}

main();