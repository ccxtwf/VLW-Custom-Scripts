import { existsSync, readFileSync } from 'fs';
import { Mwn } from 'mwn';

export interface WikiProfile {
  apiEntrypoint: string
  botUsername?: string
  botPassword?: string
  botUseragent?: string
  oauthToken?: string
  miscConfig?: unknown
}

export function readWikiProfiles(): Record<string, WikiProfile> | null {
  const fp = './profiles.json';
  if (!existsSync(fp)) {
    return null;
  }
  const profilesRawStr = readFileSync(fp, { encoding: 'utf-8', flag: 'r' });
  const res = JSON.parse(profilesRawStr) as Record<string, WikiProfile>;
  return res;
}

export async function integratedLogin(bot: Mwn) {
  if (!bot.options.OAuth2AccessToken) {
    // Login using Special:BotPasswords
    Mwn.log(`Logging into ${bot.options.apiUrl} as ${bot.options.username}`);
    await bot.login({
      apiUrl: bot.options.apiUrl,
      username: bot.options.username,
      password: bot.options.password,
    });
    Mwn.log(`Successfully logged in!`);
  } else {
    // Login using OAuth
    Mwn.log(`Authenticating OAuth credentials by checking in with ${bot.options.apiUrl}`);
    bot.initOAuth();
    await bot.getTokensAndSiteInfo();
    Mwn.log(`Successfully authenticated!`);
  }
}