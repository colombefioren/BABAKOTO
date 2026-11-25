import { createHash, timingSafeEqual } from 'node:crypto';

export const PLAYGROUND_USERNAME = 'babakoto';
const PASSWORD_FORMAT = /^[a-zA-Z0-9_-]{32,128}$/;
const CHALLENGE = 'Basic realm="Babakoto Playground", charset="UTF-8"';

type Rejection = {
  status: 401 | 503;
  message: string;
  headers: Record<string, string>;
};

function digest(value: string): Buffer {
  return createHash('sha256').update(value).digest();
}

/** Return the response details for a rejected request, or allow it with null. */
export function rejectPlaygroundAccess(
  authorization: string | null,
  password = process.env.WEB_PLAYGROUND_PASSWORD,
): Rejection | null {
  const headers = { 'Cache-Control': 'no-store' };
  if (!password || !PASSWORD_FORMAT.test(password)) {
    return { status: 503, message: 'Playground access is not configured', headers };
  }
  const expected = Buffer.from(`${PLAYGROUND_USERNAME}:${password}`, 'utf8').toString('base64');
  const encoded = /^Basic ([A-Za-z0-9+/]+={0,2})$/i.exec(authorization ?? '')?.[1];
  if (encoded && timingSafeEqual(digest(encoded), digest(expected))) return null;

  return {
    status: 401,
    message: 'Playground authentication is required',
    headers: { ...headers, 'WWW-Authenticate': CHALLENGE },
  };
}
