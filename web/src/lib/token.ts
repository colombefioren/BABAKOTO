/** Server-side LiveKit token minting. Never import this from client code. */

import { AccessToken } from 'livekit-server-sdk';

export interface LiveKitConfig {
  url: string;
  apiKey: string;
  apiSecret: string;
}

export class ConfigError extends Error {}

/** Read and validate the LiveKit environment; throws a clear error for missing values. */
export function readConfig(env: Record<string, string | undefined> = process.env): LiveKitConfig {
  const url = env.LIVEKIT_URL;
  const apiKey = env.LIVEKIT_API_KEY;
  const apiSecret = env.LIVEKIT_API_SECRET;
  if (!url || !apiKey || !apiSecret) {
    const missing = [
      ['LIVEKIT_URL', url],
      ['LIVEKIT_API_KEY', apiKey],
      ['LIVEKIT_API_SECRET', apiSecret],
    ]
      .filter(([, value]) => !value)
      .map(([name]) => name);
    throw new ConfigError(`Missing environment variables: ${missing.join(', ')}`);
  }
  return { url, apiKey, apiSecret };
}

export interface Session {
  token: string;
  url: string;
  room: string;
  identity: string;
}

/** Create a one-room-per-visitor session. The room name is random and unguessable. */
export async function createSession(config: LiveKitConfig): Promise<Session> {
  const suffix = crypto.randomUUID();
  const room = `babakoto-${suffix}`;
  const identity = `visitor-${suffix.slice(0, 8)}`;
  const token = new AccessToken(config.apiKey, config.apiSecret, { identity, ttl: '10m' });
  token.addGrant({ roomJoin: true, room, canPublish: true, canSubscribe: true });
  return { token: await token.toJwt(), url: config.url, room, identity };
}
