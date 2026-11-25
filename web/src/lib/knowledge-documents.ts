import 'server-only';

import { isUuid } from './agent-configurations';
import { requestConfiguration } from './configuration-api';

interface DocumentSummary {
  id: string;
  title: string;
}

export interface KnowledgeDocument extends DocumentSummary {
  text: string;
}

interface DocumentPage {
  items: DocumentSummary[];
  next_after: string | null;
}

function isSummary(value: unknown): value is DocumentSummary {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    isUuid(value.id) &&
    'title' in value &&
    typeof value.title === 'string'
  );
}

function collection(agentId: string): string {
  return `/v1/agents/${encodeURIComponent(agentId)}/documents`;
}

export async function listDocuments(agentId: string, after?: string): Promise<DocumentPage | null> {
  const query = after ? '?' + new URLSearchParams({ after }) : '';
  const response = await requestConfiguration(collection(agentId) + query);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Knowledge documents unavailable');
  const value: unknown = await response.json();
  if (
    typeof value !== 'object' ||
    value === null ||
    !('items' in value) ||
    !Array.isArray(value.items) ||
    !value.items.every(isSummary) ||
    !('next_after' in value) ||
    !(value.next_after === null || isUuid(value.next_after))
  ) {
    throw new Error('Unexpected knowledge document listing');
  }
  return { items: value.items, next_after: value.next_after };
}

export async function getDocument(agentId: string, id: string): Promise<KnowledgeDocument | null> {
  const response = await requestConfiguration(`${collection(agentId)}/${encodeURIComponent(id)}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Knowledge document unavailable');
  const value: unknown = await response.json();
  if (
    !isSummary(value) ||
    value.id !== id ||
    !('text' in value) ||
    typeof value.text !== 'string'
  ) {
    throw new Error('Unexpected knowledge document');
  }
  return { id: value.id, title: value.title, text: value.text };
}

export async function putDocument(
  agentId: string,
  id: string,
  fields: { title: string; text: string },
): Promise<boolean> {
  const response = await requestConfiguration(
    `${collection(agentId)}/${encodeURIComponent(id)}`,
    'PUT',
    fields,
  );
  return response.ok;
}

export async function deleteDocument(agentId: string, id: string): Promise<boolean> {
  const response = await requestConfiguration(
    `${collection(agentId)}/${encodeURIComponent(id)}`,
    'DELETE',
  );
  return response.ok;
}
