/** Abuse guards for the token endpoint: same-origin check and a per-client rate limit. */

export interface RateLimit {
  max: number;
  windowMs: number;
}

export const DEFAULT_LIMIT: RateLimit = { max: 10, windowMs: 60_000 };
export const MAX_TRACKED_KEYS = 10_000;

/**
 * Fixed-window counter per key, in memory. It protects a single instance only; a public
 * deployment needs an edge or WAF limit as well (ADR-0023). The key table is capped: when it
 * is full of live entries, new keys are refused rather than letting memory grow.
 */
export class RateLimiter {
  private readonly hits = new Map<string, { count: number; resetAt: number }>();

  constructor(
    private readonly limit: RateLimit = DEFAULT_LIMIT,
    private readonly now: () => number = Date.now,
    private readonly maxKeys: number = MAX_TRACKED_KEYS,
  ) {}

  /** Returns true when the request is allowed. */
  allow(key: string): boolean {
    const time = this.now();
    const entry = this.hits.get(key);
    if (entry && entry.resetAt > time) {
      entry.count += 1;
      return entry.count <= this.limit.max;
    }
    if (this.hits.size >= this.maxKeys) this.sweep(time);
    if (this.hits.size >= this.maxKeys) return false;
    this.hits.set(key, { count: 1, resetAt: time + this.limit.windowMs });
    return true;
  }

  private sweep(time: number): void {
    for (const [name, entry] of this.hits) {
      if (entry.resetAt <= time) this.hits.delete(name);
    }
  }
}

/** Reject cross-site browser requests. Non-browser clients send neither header and pass. */
export function isSameOrigin(headers: Pick<Headers, 'get'>): boolean {
  const site = headers.get('sec-fetch-site');
  if (site !== null && site !== 'same-origin' && site !== 'none') return false;
  const origin = headers.get('origin');
  const host = headers.get('host');
  if (origin === null || host === null) return true;
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

/**
 * Client key for rate limiting. `X-Forwarded-For` is client-controlled, so it is used only
 * when `trustedHops` proxies you operate sit in front of the app: the address those proxies
 * appended is then the entry `trustedHops` from the right. With 0 hops the header is ignored
 * and every request shares one bucket, which is safe but coarse.
 */
export function clientKey(headers: Pick<Headers, 'get'>, trustedHops = 0): string {
  if (trustedHops <= 0) return 'shared';
  const parts = (headers.get('x-forwarded-for') ?? '')
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean);
  return parts[parts.length - trustedHops] ?? 'shared';
}

/** Number of trusted proxies in front of the app, from `WEB_TRUSTED_PROXY_HOPS` (default 0). */
export function trustedHopsFromEnv(env: Record<string, string | undefined> = process.env): number {
  const hops = Number.parseInt(env.WEB_TRUSTED_PROXY_HOPS ?? '0', 10);
  return Number.isInteger(hops) && hops > 0 && hops <= 5 ? hops : 0;
}
