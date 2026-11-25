import { describe, expect, it } from 'vitest';
import { PLAYGROUND_USERNAME, rejectPlaygroundAccess } from './playground-auth';

const password = 'fixture-password'.repeat(3);

function basic(username: string, secret: string): string {
  return `Basic ${Buffer.from(`${username}:${secret}`).toString('base64')}`;
}

describe('playground authentication', () => {
  it('fails closed for missing and weak configuration', () => {
    for (const invalid of ['', 'short', password + '\n']) {
      expect(rejectPlaygroundAccess(basic(PLAYGROUND_USERNAME, invalid), invalid)).toMatchObject({
        status: 503,
        headers: { 'Cache-Control': 'no-store' },
      });
    }
  });

  it('challenges missing, malformed and incorrect credentials', () => {
    for (const authorization of [
      null,
      'Basic !!!',
      basic('other', password),
      basic('babakoto', 'bad'),
    ]) {
      expect(rejectPlaygroundAccess(authorization, password)).toMatchObject({
        status: 401,
        headers: { 'WWW-Authenticate': expect.stringMatching(/^Basic realm=/) },
      });
    }
  });

  it('accepts the operator credentials with a case-insensitive scheme', () => {
    const authorization = basic(PLAYGROUND_USERNAME, password).replace('Basic', 'basic');
    expect(rejectPlaygroundAccess(authorization, password)).toBeNull();
  });
});
