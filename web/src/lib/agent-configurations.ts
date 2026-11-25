import 'server-only';
import { requestConfiguration } from './configuration-api';

export interface AgentFields {
  name: string;
  system_prompt: string;
  first_message: string;
}

export interface AgentConfiguration extends AgentFields {
  id: string;
}

interface AgentPage {
  items: AgentConfiguration[];
  next_after: string | null;
}

export function isUuid(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(value);
}

function isAgent(value: unknown): value is AgentConfiguration {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    isUuid(value.id) &&
    'name' in value &&
    typeof value.name === 'string' &&
    'system_prompt' in value &&
    typeof value.system_prompt === 'string' &&
    'first_message' in value &&
    typeof value.first_message === 'string'
  );
}

export async function listAgents(after: string | undefined): Promise<AgentPage> {
  const query = new URLSearchParams();
  if (after) query.set('after', after);
  const response = await requestConfiguration(`/v1/agents?${query}`);
  if (!response.ok) throw new Error('Agent configuration API is unavailable');
  const data: unknown = await response.json();
  if (
    typeof data !== 'object' ||
    data === null ||
    !('items' in data) ||
    !Array.isArray(data.items) ||
    !data.items.every(isAgent) ||
    !('next_after' in data) ||
    !(data.next_after === null || isUuid(data.next_after))
  ) {
    throw new Error('Agent configuration API returned an unexpected response');
  }
  return { items: data.items, next_after: data.next_after };
}

export async function getAgent(id: string): Promise<AgentConfiguration | null> {
  const response = await requestConfiguration(`/v1/agents/${encodeURIComponent(id)}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Agent configuration API is unavailable');
  const item: unknown = await response.json();
  if (!isAgent(item) || item.id.toLowerCase() !== id.toLowerCase()) {
    throw new Error('Agent configuration API returned an unexpected response');
  }
  return item;
}

export async function putAgent(id: string, fields: AgentFields): Promise<boolean> {
  const response = await requestConfiguration(
    `/v1/agents/${encodeURIComponent(id)}`,
    'PUT',
    fields,
  );
  return response.ok;
}
