import { describe, expect, it } from 'vitest';
import { ConfigError, createSession, readConfig } from './token';

const env = {
  LIVEKIT_URL: 'ws://lk:7880',
  LIVEKIT_API_KEY: 'key',
  LIVEKIT_API_SECRET: 'x'.repeat(32),
};

describe('readConfig', () => {
  it('reads the three variables', () => {
    expect(readConfig(env)).toEqual({
      url: 'ws://lk:7880',
      apiKey: 'key',
      apiSecret: 'x'.repeat(32),
    });
  });

  it('names every missing variable', () => {
    expect(() => readConfig({})).toThrow(ConfigError);
    expect(() => readConfig({ LIVEKIT_URL: 'ws://x' })).toThrow(
      'LIVEKIT_API_KEY, LIVEKIT_API_SECRET',
    );
  });
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const claims = (jwt: string): Record<string, any> =>
  JSON.parse(Buffer.from(jwt.split('.')[1] ?? '', 'base64url').toString());

describe('createSession', () => {
  it('mints a token scoped to one random room', async () => {
    const config = readConfig(env);
    const a = await createSession(config);
    const b = await createSession(config);
    expect(a.room).toMatch(/^babakoto-[0-9a-f-]{36}$/);
    expect(a.room).not.toBe(b.room);
    expect(a.url).toBe('ws://lk:7880');
    const payload = claims(a.token);
    expect(payload.iss).toBe('key');
    expect(payload.sub).toBe(a.identity);
    expect(payload.video).toMatchObject({
      room: a.room,
      roomJoin: true,
      canPublishData: false,
      canPublishSources: ['microphone'],
    });
    expect(payload.exp - payload.nbf).toBeLessThanOrEqual(600);
  });
});
