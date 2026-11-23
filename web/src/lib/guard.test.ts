import { describe, expect, it } from 'vitest';
import { clientKey, isSameOrigin, RateLimiter, trustedHopsFromEnv } from './guard';

const headers = (values: Record<string, string>) => ({
  get: (name: string) => values[name.toLowerCase()] ?? null,
});

describe('RateLimiter', () => {
  it('blocks after the limit and recovers when the window ends', () => {
    let now = 0;
    const limiter = new RateLimiter({ max: 2, windowMs: 1000 }, () => now);
    expect([limiter.allow('a'), limiter.allow('a'), limiter.allow('a')]).toEqual([
      true,
      true,
      false,
    ]);
    expect(limiter.allow('b')).toBe(true);
    now = 1001;
    expect(limiter.allow('a')).toBe(true);
  });
});

describe('isSameOrigin', () => {
  it('accepts same-origin, direct and header-less requests', () => {
    expect(isSameOrigin(headers({}))).toBe(true);
    expect(isSameOrigin(headers({ 'sec-fetch-site': 'same-origin' }))).toBe(true);
    expect(isSameOrigin(headers({ 'sec-fetch-site': 'none' }))).toBe(true);
    expect(isSameOrigin(headers({ origin: 'http://h:3000', host: 'h:3000' }))).toBe(true);
  });

  it('rejects cross-site requests and malformed origins', () => {
    expect(isSameOrigin(headers({ 'sec-fetch-site': 'cross-site' }))).toBe(false);
    expect(isSameOrigin(headers({ origin: 'http://evil.test', host: 'h:3000' }))).toBe(false);
    expect(isSameOrigin(headers({ origin: 'not a url', host: 'h' }))).toBe(false);
  });
});

describe('RateLimiter key cap', () => {
  it('refuses new keys when the table is full of live entries, then recovers', () => {
    let now = 0;
    const limiter = new RateLimiter({ max: 5, windowMs: 1000 }, () => now, 2);
    expect([limiter.allow('a'), limiter.allow('b'), limiter.allow('c')]).toEqual([
      true,
      true,
      false,
    ]);
    expect(limiter.allow('a')).toBe(true);
    now = 1001;
    expect(limiter.allow('c')).toBe(true);
  });
});

describe('clientKey', () => {
  it('ignores X-Forwarded-For unless proxies are trusted', () => {
    expect(clientKey(headers({ 'x-forwarded-for': '6.6.6.6' }))).toBe('shared');
    expect(clientKey(headers({}), 1)).toBe('shared');
  });

  it('takes the address the trusted proxy appended, counted from the right', () => {
    const h = headers({ 'x-forwarded-for': '6.6.6.6, 1.2.3.4, 10.0.0.1' });
    expect(clientKey(h, 1)).toBe('10.0.0.1');
    expect(clientKey(h, 2)).toBe('1.2.3.4');
    expect(clientKey(h, 9)).toBe('shared');
  });
});

describe('trustedHopsFromEnv', () => {
  it('defaults to 0 and rejects bad values', () => {
    expect(trustedHopsFromEnv({})).toBe(0);
    expect(trustedHopsFromEnv({ WEB_TRUSTED_PROXY_HOPS: '2' })).toBe(2);
    expect(trustedHopsFromEnv({ WEB_TRUSTED_PROXY_HOPS: 'x' })).toBe(0);
    expect(trustedHopsFromEnv({ WEB_TRUSTED_PROXY_HOPS: '-1' })).toBe(0);
    expect(trustedHopsFromEnv({ WEB_TRUSTED_PROXY_HOPS: '99' })).toBe(0);
  });
});
