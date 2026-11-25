import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { deleteDocument, getDocument, listDocuments, putDocument } from './knowledge-documents';

vi.mock('server-only', () => ({}));

const agent = '00000000-0000-0000-0000-000000000001';
const id = '00000000-0000-0000-0000-000000000002';
const document = { id, title: 'Hours', text: 'Office opens Sundays.' };
const collection = `http://config.test/v1/agents/${agent}/documents`;

beforeEach(() => {
  vi.stubEnv('API_URL', 'http://config.test');
  vi.stubEnv('API_SECRET_KEY', 'fixture-operator-credential');
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

it('scopes document changes to a saved agent using the private API', async () => {
  const request = vi.fn().mockImplementation(() => new Response(null, { status: 204 }));
  vi.stubGlobal('fetch', request);
  const fields = { title: document.title, text: document.text };
  await expect(putDocument(agent, id, fields)).resolves.toBe(true);
  await expect(deleteDocument(agent, id)).resolves.toBe(true);
  expect(request).toHaveBeenNthCalledWith(
    1,
    new URL(`${collection}/${id}`),
    expect.objectContaining({
      cache: 'no-store',
      redirect: 'error',
      method: 'PUT',
      body: JSON.stringify(fields),
      headers: {
        Authorization: 'Bearer fixture-operator-credential',
        'Content-Type': 'application/json',
      },
    }),
  );
  expect(request).toHaveBeenNthCalledWith(
    2,
    new URL(`${collection}/${id}`),
    expect.objectContaining({ method: 'DELETE' }),
  );
});

it('validates cursors and refuses to load a different document than requested', async () => {
  const request = vi
    .fn()
    .mockResolvedValueOnce(Response.json({ items: [document], next_after: id }))
    .mockResolvedValueOnce(Response.json({ items: [document], next_after: 'invalid' }))
    .mockResolvedValueOnce(Response.json({ ...document, id: agent }))
    .mockResolvedValueOnce(new Response(null, { status: 404 }));
  vi.stubGlobal('fetch', request);
  await expect(listDocuments(agent, id)).resolves.toMatchObject({ next_after: id });
  expect(request).toHaveBeenNthCalledWith(
    1,
    new URL(`${collection}?after=${id}`),
    expect.any(Object),
  );
  await expect(listDocuments(agent)).rejects.toThrow('Unexpected');
  await expect(getDocument(agent, id)).rejects.toThrow('Unexpected');
  await expect(getDocument(agent, id)).resolves.toBeNull();
});
