import { 
  existsSync, 
  readFileSync, 
  mkdirSync, 
  createWriteStream
} from 'fs';
import { resolve } from 'path';
import { Mwn } from 'mwn';
import { styleText } from 'util';
import { PassThrough } from 'stream';

export interface WikiProfile {
  apiEntrypoint: string
  botUsername?: string
  botPassword?: string
  botUseragent?: string
  oauthToken?: string
  miscConfig?: unknown
}

/**
 * Reads the `credentials/profiles.json` file. 
 * 
 * @returns 
 */
export function readWikiProfiles(): Record<string, WikiProfile> | null {
  //@ts-ignore
  const __dirname = import.meta.dirname;
  const fp = resolve(__dirname, './profiles.json');
  if (!existsSync(fp)) {
    return null;
  }
  const profilesRawStr = readFileSync(fp, { encoding: 'utf-8', flag: 'r' });
  const res = JSON.parse(profilesRawStr) as Record<string, WikiProfile>;
  return res;
}

/**
 * Saves the Mwn logs to a filesystem write stream in the `logs/` folder. 
 * 
 * @param prefix      Log filename prefix
 * @param dualStream  Logs to console and filesystem write stream  
 */
export function setLoggingConfig({ prefix = 'mwn-log', dualStream = false }: { prefix?: string, dualStream?: boolean } = {}) {
  //@ts-ignore
  const __dirname = import.meta.dirname;
  const logsFolderPath = resolve(__dirname, '../logs');
  if (!existsSync(logsFolderPath)) { 
    console.log(styleText( 'magenta', `Making a folder at ${logsFolderPath}`));
    mkdirSync(logsFolderPath);
  }
  const currentDate = new Date(Date.now()).toISOString().slice(0, 10);
  const _ps = new PassThrough();
  const _fs = createWriteStream(
    resolve(logsFolderPath, `${prefix}-${currentDate}.log`), {
    flags: 'a',
    encoding: 'utf8'
  });
  _ps.pipe(_fs);
  Mwn.setLoggingConfig({
    stream: _ps,
  });

  if (dualStream) {
    _ps.pipe(process.stdout);
  }
}

/**
 * Utility function to handle bot login (using BotPasswords) and/or OAuth initialization.
 * 
 * @param bot Mwn bot instance
 */
export async function integratedLogin(bot: Mwn) {
  try {
    if (!bot.options.OAuth2AccessToken) {
      // Login using Special:BotPasswords
      Mwn.log(styleText( 'yellow', `[I] Logging into ${bot.options.apiUrl} as ${bot.options.username}` ));
      await bot.login({
        apiUrl: bot.options.apiUrl,
        username: bot.options.username,
        password: bot.options.password,
      });
      Mwn.log(styleText( 'green', `[S] Successfully logged in!` ));
    } else {
      // Login using OAuth
      Mwn.log(styleText( 'yellow', `[I] Authenticating OAuth credentials by checking in with ${bot.options.apiUrl}` ));
      bot.initOAuth();
      await bot.getTokensAndSiteInfo();
      Mwn.log(styleText( 'green', `[S] Successfully authenticated!` ));
    }
  } catch (err) {
    Mwn.log(styleText( 'red', `[E] ${err}` ));
  }
}