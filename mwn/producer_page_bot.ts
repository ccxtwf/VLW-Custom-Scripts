import "dotenv/config";
import minimist from "minimist";

var argv = minimist(process.argv.slice(2));

import { Mwn } from "mwn";
import type { ApiResponse, ApiPage, MwnOptions } from "mwn";
import http from "http";
import https from "https";
import axios from "axios";
import fs from "fs";

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

  const bot = new ProducerPageBot({
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
  await bot.run();
  bot.generateReport();
}

main();