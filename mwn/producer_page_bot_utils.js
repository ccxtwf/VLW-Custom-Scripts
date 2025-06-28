const { JSDOM } = require("jsdom");

const __rxProdCat = /\{\{\s*[Pp]rodLinks\s*\|([^\}\|]*)/;
const __rxProdCatParam = /\s*\b(catname|1)\b\s*=\s*/;
const __rxPwtTable = /(?<head>{\|\s*class=[\"']sortable\s+producer-table[\"']\s*\n\|-[^\{\}\n]*?\n!\s*\{\{\s*[Pp]wt[ _]head\s*\}\}\s*\n)(.*?(?!\|\}\}))\|\}/gs;
const __rxAwtTable = /(?<head>{\|\s*class=[\"']sortable\s+producer-table[\"']\s*\n\|-[^\{\}\n]*?\n!\s*\{\{\s*[Aa]wt[ _]head\s*\}\}\s*\n)(.*?(?!\|\}\}))\|\}/gs;
const __rxPwtRowTemplate = /(?:\|-[^\n]*\n[\s\u200B]*\|[\s\u200B]*)\{\{\s*[Pp][wh]t[ _]row\s*\|([^\n]*)\}\}(?=[\s\u200B]*\n)/gs;
const __rxAwtRowTemplate = /(?:\|-[^\n]*\n[\s\u200B]*\|[\s\u200B]*)\{\{\s*[Aa]wt[ _]row\s*\|([^\n]*)\}\}(?=[\s\u200B]*\n)/gs;

function parseDplOutputToList(output) {
  const dom = new JSDOM(output);
  const res = ((dom.window.document.querySelector('div.mw-parser-output > p') || {}).innerHTML || '').trim();
  if (res === '') return [];
  const pages = res.split("||");
  pages.pop();
  return pages;
}
function detonePinyin(text) {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}
function parseRomajiPortion(title, forAlbum) {
  let extractedRomaji = title;
  if (forAlbum) {
    extractedRomaji = extractedRomaji.replace(/ \(album\)$/, '');
  }
  extractedRomaji = extractedRomaji.replace(/(?<=\))\/.*$/, '');
  let m = extractedRomaji.match(/(?<=\s\()[ -~ĀÁǍÀĒÉĚÈŌÓǑÒ].*(?=\)$)/);
  if (m === null) {
    return title;   // No match found
  }
  extractedRomaji = m[0];
  while (extractedRomaji.match(/^[^\(]*\)[^\(]*\(/) !== null) {
    extractedRomaji = extractedRomaji.replace(/^[^\(]*\)[^\(]*\(/, '');
  }
  
  const checkOriginalPortion = title.replace(` (${extractedRomaji})`, '');
  if (checkOriginalPortion.match(/[^ -~]/) === null) {
    return title;   // Page is already in English
  }
  return extractedRomaji;
}
function getSortedValue(pwt_template_input, forAlbum = false) {
  let pageTitle = pwt_template_input.match(/^[^\|]*/)[0];
  pageTitle = pageTitle.replace(/^\s*1\s*=\s*/, '').replaceAll(/\{\{=\}\}/g, '=');
  let romTitle = parseRomajiPortion(pageTitle, forAlbum);
  let miscParams = pwt_template_input.replace(pageTitle, "");

  // Deduce manual romanization
  let manualKanji = miscParams.match(/\|kanji\s*=\s*([^\|]*)/);
  if (manualKanji === null) {
    manualKanji = miscParams.match(/\|(?<!\s*\w+\s*=\s*)([^\|]*)/);
  }
  manualKanji = manualKanji === null ? '' : manualKanji[1];
  let manualRom = miscParams.match(/\|rom\s*=\s*([^\|]*)/);
  manualRom = manualRom === null ? '' : manualRom[1];
  if (manualRom !== '') { romTitle = manualRom; }

  //Finishing operations
  romTitle = detonePinyin(romTitle).toLowerCase();
  romTitle = romTitle.replaceAll(/[\[\(\)\]\"'¿\?『』「」:’]/g, '');
  romTitle += miscParams;

  return romTitle;
}

const producerPageBotMixin = {
  getProducerCategory(pageContents) {
    const m = pageContents.match(__rxProdCat);
    if (m === null) throw { error: "Cannot find {{ProdLinks}}" };
    return m[1].trim().replace(__rxProdCatParam, '');
  },
  async filterPagesThatHaveBeenTranscludedUsingRedirects(pages, prodPageTitle, forAlbums = false) {
    if (pages.length === 0) {
      return pages;   // nothing to filter
    }
    const res = [];
    const q = await this.continuedQuery({
      action: 'query',
      format: 'json',
      prop: forAlbums ? 'transcludedin|categories' : 'transcludedin',
      titles: pages, 
      tinamespace: 0,
      tilimit: 500,
      clcategories: forAlbums ? 'Category:Compilation albums' : undefined
    });
    for await (let json of q) {
      const untranscludedPages = json.query.pages.filter((page) => {
        return (page.transcludedin || []).every(({title}) => title !== prodPageTitle);
      }).map(({ title, categories = [] }) => {
        if (forAlbums) {
          return [ title, categories.length > 0 ];
        } else {
          return title;
        }
      });
      res.push(...untranscludedPages);
    }
    return res;
  },
  async getSongPagesNotOnPage(prodCat, prodPageTitle) {
    const q = `{{#dpl:|categorymatch=${prodCat.replaceAll(/%/g, '\\%').replaceAll(/_/g, '\\_')} songs list%|notcategory=${prodCat} songs list/Albums|notlinksfrom=${prodPageTitle}|namespace=|format=,%TITLE%,{{!}}{{!}},}}`;
    const res = await this.parseWikitext(q);
    const pages = await this.filterPagesThatHaveBeenTranscludedUsingRedirects(
      parseDplOutputToList(res), prodPageTitle
    )
    return pages;
  },
  async getAlbumPagesNotOnPage(prodCat, prodPageTitle) {
    const q = `{{#dpl:|category=${prodCat} songs list/Albums|notlinksfrom=${prodPageTitle}|namespace=|format=,%TITLE%,{{!}}{{!}},}}`;
    const res = await this.parseWikitext(q);
    const pages = await this.filterPagesThatHaveBeenTranscludedUsingRedirects(
      parseDplOutputToList(res), prodPageTitle, true
    )
    return pages;
  },

  updatePwt(pageContents, missingSongs) {
    if (missingSongs.length === 0) {
      return pageContents;
    }
    const pwtTables = Array.from(pageContents.matchAll(__rxPwtTable));
    if (pwtTables.length > 1) {
      throw { error: "More than one pwt row table found" }
    }
    if (pwtTables.length === 0) {
      throw { error: "Cannot find pwt row table" }
    }
    const pwtTableWikitext = pwtTables[0][0];

    const extractMatchProperties = (m) => { return {
      fullmatch: m[0],
      input: m[1],
      sortValue: getSortedValue(m[1]),
    }};
    const pwtSongs = Array.from(pwtTableWikitext.matchAll(__rxPwtRowTemplate)).map(extractMatchProperties);

    for (let missingSong of missingSongs) {
      let sortValue = getSortedValue(missingSong);
      let pwtTemplate = `|-\n| {{pwt row|${missingSong}}}`;
      let addToIndex = 0;
      while (addToIndex < pwtSongs.length) {
        if (pwtSongs[addToIndex].sortValue > sortValue) {
          break;
        }
        addToIndex++;
      }
      pwtSongs.splice(addToIndex, 0, { fullmatch: pwtTemplate, input: missingSong, sortValue });
    }

    let newPwtTableWikitext = pwtTables[0].groups['head'] + pwtSongs.map((m) => m.fullmatch).join('\n') + '\n|}';
    return pageContents.replace(pwtTableWikitext, newPwtTableWikitext);
  },
  
  updateAwt(pageContents, missingAlbums) {
    if (missingAlbums.length === 0) {
      return pageContents;
    }
    const awtTables = Array.from(pageContents.matchAll(__rxAwtTable));
    const extractMatchProperties = (m) => { return {
      fullmatch: m[0],
      input: m[1],
      sortValue: getSortedValue(m[1], true),
    }};

    let awtTableWikitext;
    let newAwtTableWikitext;
    let awtTableWikitextCompilations;
    let newAwtTableWikitextCompilations;
    let awtAlbums;
    let awtCompilationAlbums;

    switch (awtTables.length) {
      case 0:
        missingAlbums = missingAlbums.map((a) => a[0]);
        missingAlbums = missingAlbums.sort((a, b) => {
          if (getSortedValue(a, true) < getSortedValue(b, true)) {
            return -1;
          }
          if (getSortedValue(a, true) > getSortedValue(b, true)) {
            return 1;
          }
          return 0;
        })
        newAwtTableWikitext = `==Discography==\n{| class=\"sortable producer-table\"\n|- class=\"vcolor-default\"\n! {{awt head}}\n`;
        newAwtTableWikitext += missingAlbums.map((s) => {
          return `|-\n| {{awt row|${s}}}`;
        });
        newAwtTableWikitext += "\n|}\n\n";
        
        let manualCategories = pageContents.match(/^(.*?)(__NOTOC__|)\s*(\[\[[Cc]ategory:.*)$/s);
        if (manualCategories === null) {
          return pageContents + newAwtTableWikitext;
        } else {
          return pageContents.replace(manualCategories[0], manualCategories[1]+newAwtTableWikitext+manualCategories[2]+'\n'+manualCategories[3]);
        }
      case 1:
        awtTableWikitext = awtTables[0][0];
        awtAlbums = Array.from(awtTableWikitext.matchAll(__rxAwtRowTemplate)).map(extractMatchProperties);
        for (let [missingAlbum, _] of missingAlbums) {
          let sortValue = getSortedValue(missingAlbum, true);
          let awtTemplate = `|-\n| {{awt row|${missingAlbum}}}`;
          let addToIndex = 0;
          while (addToIndex < awtAlbums.length) {
            if (awtAlbums[addToIndex].sortValue > sortValue) {
              break;
            }
            addToIndex++;
          }
          awtAlbums.splice(addToIndex, 0, { fullmatch: awtTemplate, input: missingAlbum, sortValue });
        }
        newAwtTableWikitext = awtTables[0].groups['head'] + awtAlbums.map((m) => m.fullmatch).join('\n') + '\n|}';
        return pageContents.replace(awtTableWikitext, newAwtTableWikitext);
      default:
        awtTableWikitext = awtTables[0][0];
        awtTableWikitextCompilations = awtTables[1][0];
        awtAlbums = Array.from(awtTableWikitext.matchAll(__rxAwtRowTemplate)).map(extractMatchProperties);
        awtCompilationAlbums = Array.from(awtTableWikitextCompilations.matchAll(__rxAwtRowTemplate)).map(extractMatchProperties);
        for (let [missingAlbum, isCompilation] of missingAlbums) {
          let sortValue = getSortedValue(missingAlbum, true);
          let awtTemplate = `|-\n| {{awt row|${missingAlbum}}}`;
          let addToIndex = 0;
          let searchInTable = isCompilation ? awtCompilationAlbums : awtAlbums;
          while (addToIndex < searchInTable.length) {
            if (searchInTable[addToIndex].sortValue > sortValue) {
              break;
            }
            addToIndex++;
          }
          searchInTable.splice(addToIndex, 0, { fullmatch: awtTemplate, input: missingAlbum, sortValue });
        }
        newAwtTableWikitext = awtTables[0].groups['head'] + awtAlbums.map((m) => m.fullmatch).join('\n') + '\n|}';
        newAwtTableWikitextCompilations = awtTables[1].groups['head'] + awtCompilationAlbums.map((m) => m.fullmatch).join('\n') + '\n|}';
        pageContents = pageContents.replace(awtTableWikitext, newAwtTableWikitext);
        pageContents = pageContents.replace(awtTableWikitextCompilations, newAwtTableWikitextCompilations);
        return pageContents;
    }
  }
}

module.exports = { producerPageBotMixin }