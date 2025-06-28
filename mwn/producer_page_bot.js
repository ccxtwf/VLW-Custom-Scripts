require('loadenv')();

const { Mwn } = require("mwn");
const http = require("http");
const https = require("https");
const axios = require("axios");

const { producerPageBotMixin } = require("./producer_page_bot_utils");

Object.assign(Mwn.prototype, producerPageBotMixin);

const EDIT_SUMMARY = 'Bot: Updating producer page discography';
const errorPages = [];

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

  if (process.env.ENV_REJECT_UNAUTHORIZED == 0) {
    console.log("Setting HTTP Request Agent to not reject unauthorized requests. Do not do this on production environments.");
    const httpAgent = new http.Agent({ keepAlive: true, rejectUnauthorized: false });
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

async function runBot(bot) {
  const pagesInCategory = bot.continuedQueryGen({
    action: 'query',
    format: 'json',
    generator: 'categorymembers',
    gcmtitle: 'Category:Producers',
    gcmnamespace: 0,
    gcmprop: 'ids|title|sortkeyprefix',
    gcmlimit: 50,
    gcmsort: 'sortkey',
    prop: 'revisions',
    rvprop: 'content',
    rvslots: '*'
  });
  // const pagesInCategory = bot.continuedQueryGen({
  //   action: 'query',
  //   format: 'json',
  //   prop: 'revisions',
  //   rvprop: 'content',
  //   rvslots: '*',
  //   titles: ["Y Y"]
  // });
  for await (let json of pagesInCategory) {
    for (const { pageid, ns, title, revisions } of json.query.pages) {
      const pageContents = revisions[0].slots.main.content;
      await treatPage(bot, { pageid, ns, title, pageContents });
    }
  }
}

async function treatPage(bot, { pageid, ns, title, pageContents }) {
  try {
    const prodCat = bot.getProducerCategory(pageContents);
    Mwn.log(`[I] ${title}: Querying from producer category ${prodCat}`);
    let newPageContents = pageContents;
    const songPagesNotInCategory = await bot.getSongPagesNotOnPage(prodCat, title);
    const albumPagesNotInCategory = await bot.getAlbumPagesNotOnPage(prodCat, title);
    let editsMade = false;
    if (songPagesNotInCategory.length > 0) {
      Mwn.log(`[I] ${title}: Found ${songPagesNotInCategory.length} song page(s): ${songPagesNotInCategory.join(', ')}`);
      newPageContents = bot.updatePwt(newPageContents, songPagesNotInCategory);
      editsMade = true;
    }
    if (albumPagesNotInCategory.length > 0) {
      Mwn.log(`[I] ${title}: Found ${albumPagesNotInCategory.length} album page(s): ${albumPagesNotInCategory.join(', ')}`);
      newPageContents = bot.updateAwt(newPageContents, albumPagesNotInCategory);
      editsMade = true;
    }
    if (editsMade) {
      await bot.save(title, newPageContents, EDIT_SUMMARY);
      Mwn.log(`[S] Saved page ${title}`);
    }
  } catch (err) {
    Mwn.log(`[E] ${title}:\t\t${err.error || err}`);
    errorPages.push([title, err.error || err]);
  }
}

function generateReport() {
  if (errorPages.length > 0) {
    Mwn.log(`[I] Encountered errors with the following pages:`);
    for (let [page, message] of errorPages) {
      Mwn.log(`[E] ${page}:\t\t${message}`);
    }
  }
  Mwn.log(`[S] Finished bot run`);
}

async function main() {
  const bot = await initBot();
  await runBot(bot);
  generateReport();
}

main();