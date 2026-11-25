import { NextResponse, type NextRequest } from 'next/server';
import { rejectPlaygroundAccess } from '@/lib/playground-auth';

export const config = { matcher: ['/', '/agents/:path*'] };

export function proxy(request: NextRequest): NextResponse {
  const rejection = rejectPlaygroundAccess(request.headers.get('authorization'));
  if (rejection) return new NextResponse(rejection.message, rejection);
  const response = NextResponse.next();
  response.headers.set('Cache-Control', 'private, no-store');
  return response;
}
