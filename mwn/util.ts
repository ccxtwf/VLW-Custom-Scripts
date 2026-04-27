import { existsSync, readFileSync } from 'fs';

export interface WikiProfile {
  apiEntrypoint: string
  botUsername?: string
  botPassword?: string
  botUseragent?: string
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