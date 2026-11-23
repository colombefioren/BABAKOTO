/** Abuse guards for the token endpoint: same-origin check and a per-client rate limit. */

export interface RateLimit {
  max: number;
  windowMs: number;
}

export const DEFAULT_LIMIT: RateLimit = { max: 10, windowMs: 60_000 };

/**
 * Fixed-window counter per key, in memory. It protects a single instance only; a public
 * deployment needs an edge or WAF limit as well (ADR-0022).
 */
export class RateLimiter {
  private readonly hits = new Map<string, { count: number; resetAt: number }>();

  constructor(
    private readonly limit: RateLimit = DEFAULT_LIMIT,
    private readonly now: () => number = Date.now,
  ) {}

  /** Returns true when the request is allowed. */
  allow(key: string): boolean {
    const time = this.now();
    for (const [name, entry] of this.hits) {
      if (entry.resetAt <= time) this.hits.delete(name);
    }
    const entry = this.hits.get(key);
    if (!entry) {
      this.hits.set(key, { count: 1, resetAt: time + this.limit.windowMs });
      return true;
    }
    entry.count += 1;
    return entry.count <= this.limit.max;
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

/** Client key from the proxy header, falling back to one shared bucket. */
export function clientKey(headers: Pick<Headers, 'get'>): string {
  const forwarded = headers.get('x-forwarded-for')?.split(',')[0]?.trim();
  return forwarded || 'unknown';
}
