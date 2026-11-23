import { NextResponse } from 'next/server';
import { ConfigError, createSession, readConfig } from '@/lib/token';

export const dynamic = 'force-dynamic';

/** Mint a short-lived LiveKit token for one browser visitor. */
export async function POST(): Promise<NextResponse> {
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
