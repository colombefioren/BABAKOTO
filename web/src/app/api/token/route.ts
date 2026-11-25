import { NextResponse } from 'next/server';
import { getAgent, isUuid } from '@/lib/agent-configurations';
import { clientKey, isSameOrigin, RateLimiter, trustedHopsFromEnv } from '@/lib/guard';
import { rejectPlaygroundAccess } from '@/lib/playground-auth';
import {
  RoomAdmission,
  RoomCapacityError,
  RoomServiceError,
  roomLimit,
  roomService,
} from '@/lib/room-admission';
import { ConfigError, readConfig } from '@/lib/token';

export const dynamic = 'force-dynamic';

const limiter = new RateLimiter();
const admission = new RoomAdmission();

/** Mint a short-lived LiveKit token for one browser visitor. */
export async function POST(request: Request): Promise<NextResponse> {
  if (!isSameOrigin(request.headers)) {
    return NextResponse.json({ error: 'Cross-site requests are not allowed' }, { status: 403 });
  }
  const rejection = rejectPlaygroundAccess(request.headers.get('authorization'));
  if (rejection) return NextResponse.json({ error: rejection.message }, rejection);
  if (!limiter.allow(clientKey(request.headers, trustedHopsFromEnv()))) {
    return NextResponse.json({ error: 'Too many requests, try again soon' }, { status: 429 });
  }
  const agents = new URL(request.url).searchParams.getAll('agent');
  const selected = agents[0];
  if (agents.length > 1 || (selected !== undefined && !isUuid(selected))) {
    return NextResponse.json({ error: 'Invalid saved agent identifier' }, { status: 400 });
  }

  if (selected) {
    try {
      if (!(await getAgent(selected))) {
        return NextResponse.json({ error: 'Saved agent was not found' }, { status: 404 });
      }
    } catch {
      return NextResponse.json(
        { error: 'The configuration API is unavailable' },
        { status: 503, headers: { 'Cache-Control': 'no-store' } },
      );
    }
  }

  try {
    const config = readConfig();
    const session = await admission.admit(roomService(config), config, roomLimit(), selected);
    return NextResponse.json(session, {
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch (error) {
    if (error instanceof RoomCapacityError) {
      return NextResponse.json(
        { error: error.message },
        { status: 429, headers: { 'Retry-After': '5', 'Cache-Control': 'no-store' } },
      );
    }
    if (error instanceof ConfigError || error instanceof RoomServiceError) {
      return NextResponse.json(
        { error: error.message },
        { status: 503, headers: { 'Cache-Control': 'no-store' } },
      );
    }
    throw error;
  }
}
