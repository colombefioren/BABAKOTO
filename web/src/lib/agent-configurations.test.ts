import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getAgent, listAgents } from './agent-configurations';

vi.mock('server-only', () => ({}));

const profile = {
  id: '01234567-0000-0000-0000-000000000001',
  name: 'Fixture',
  system_prompt: 'Reply briefly.',
  first_message: 'Hello.',
};

beforeEach(() => {
  vi.stubEnv('API_URL', 'http://config.test:8000');
  vi.stubEnv('API_SECRET_KEY', 'fixture-operator-credential');
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('saved agent API reads', () => {
  it('loads the selected ID using only the configured private API', async () => {
    const fetchAgent = vi.fn(async () => Response.json(profile));
    vi.stubGlobal('fetch', fetchAgent);
    await expect(getAgent(profile.id)).resolves.toEqual(profile);
    expect(fetchAgent).toHaveBeenCalledExactlyOnceWith(
      new URL(`http://config.test:8000/v1/agents/${profile.id}`),
      expect.objectContaining({
        headers: { Authorization: 'Bearer fixture-operator-credential' },
        cache: 'no-store',
        redirect: 'error',
      }),
    );
  });

  it('distinguishes a removed selection from a broken API response', async () => {
    const fetchAgent = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 404 }))
      .mockResolvedValueOnce(
        Response.json({ ...profile, id: '00000000-0000-0000-0000-000000000002' }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 502 }));
    vi.stubGlobal('fetch', fetchAgent);

    await expect(getAgent(profile.id)).resolves.toBeNull();
    await expect(getAgent(profile.id)).rejects.toThrow('unexpected response');
    await expect(getAgent(profile.id)).rejects.toThrow('unavailable');
  });

  it('validates records and cursors from the API list', async () => {
    const fetchAgents = vi
      .fn()
      .mockResolvedValueOnce(Response.json({ items: [profile], next_after: profile.id }))
      .mockResolvedValueOnce(Response.json({ items: [{ id: profile.id }], next_after: null }))
      .mockResolvedValueOnce(Response.json({ items: [], next_after: 'invalid' }));
    vi.stubGlobal('fetch', fetchAgents);

    await expect(listAgents(undefined)).resolves.toEqual({
      items: [profile],
      next_after: profile.id,
    });
    await expect(listAgents(profile.id)).rejects.toThrow('unexpected response');
    await expect(listAgents(profile.id)).rejects.toThrow('unexpected response');
  });
});
