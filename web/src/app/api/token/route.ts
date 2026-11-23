import { NextResponse } from 'next/server';
import { clientKey, isSameOrigin, RateLimiter } from '@/lib/guard';
import { ConfigError, createSession, readConfig } from '@/lib/token';

export const dynamic = 'force-dynamic';

const limiter = new RateLimiter();

/** Mint a short-lived LiveKit token for one browser visitor. */
export async function POST(request: Request): Promise<NextResponse> {
  if (!isSameOrigin(request.headers)) {
    return NextResponse.json({ error: 'Cross-site requests are not allowed' }, { status: 403 });
  }
  if (!limiter.allow(clientKey(request.headers))) {
    return NextResponse.json({ error: 'Too many requests, try again soon' }, { status: 429 });
  }
  try {
    return NextResponse.json(await createSession(readConfig()), {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    if (error instanceof ConfigError) {
      return NextResponse.json({ error: error.message }, { status: 503 });
    }
    throw error;
  }
}
