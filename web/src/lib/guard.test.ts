import { describe, expect, it } from 'vitest';
import { clientKey, isSameOrigin, RateLimiter } from './guard';

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

describe('clientKey', () => {
  it('uses the first forwarded address', () => {
    expect(clientKey(headers({ 'x-forwarded-for': '1.2.3.4, 10.0.0.1' }))).toBe('1.2.3.4');
    expect(clientKey(headers({}))).toBe('unknown');
  });
});
