import 'server-only';

export async function requestConfiguration(
  path: string,
  method: 'GET' | 'PUT' | 'DELETE' = 'GET',
  body?: object,
): Promise<Response> {
  const baseUrl = process.env.API_URL;
  const token = process.env.API_SECRET_KEY;
  if (!baseUrl || !token) throw new Error('Agent configuration API is unavailable');

  const headers: Record<string, string> = { Authorization: `Bearer ${token}` };
  if (body) headers['Content-Type'] = 'application/json';
  return fetch(new URL(path, baseUrl), {
    cache: 'no-store',
    redirect: 'error',
    signal: AbortSignal.timeout(5000),
    headers,
    method,
    body: body ? JSON.stringify(body) : undefined,
  });
}
