'use server';

import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { isUuid } from '@/lib/agent-configurations';
import { isSameOrigin } from '@/lib/guard';
import { deleteDocument, putDocument } from '@/lib/knowledge-documents';
import { rejectPlaygroundAccess } from '@/lib/playground-auth';

export async function changeDocument(
  _previous: string | null,
  data: FormData,
): Promise<string | null> {
  const requestHeaders = await headers();
  if (
    !isSameOrigin(requestHeaders) ||
    rejectPlaygroundAccess(requestHeaders.get('authorization'))
  ) {
    return 'Sign in again before changing a document.';
  }

  const agent = data.get('agent');
  const document = data.get('document');
  const intent = data.get('intent');
  if (!isUuid(agent) || !isUuid(document) || (intent !== 'save' && intent !== 'delete')) {
    return 'Open a document from the agent’s knowledge page and try again.';
  }

  const title = data.get('title');
  const text = data.get('text');
  try {
    if (intent === 'delete') {
      if (!(await deleteDocument(agent, document))) return 'Could not delete this document.';
    } else {
      if (
        typeof title !== 'string' ||
        !title.trim() ||
        title.length > 160 ||
        typeof text !== 'string' ||
        !text.trim() ||
        text.length > 10_000 ||
        title.includes('\0') ||
        text.includes('\0')
      ) {
        return 'Enter a title and document text within the field limits.';
      }
      if (!(await putDocument(agent, document, { title, text }))) {
        return 'Could not save this document. Check the fields and try again.';
      }
    }
  } catch {
    return 'The knowledge API is unavailable. Try again when it is running.';
  }

  const query = intent === 'delete' ? 'deleted=1' : `document=${document}&saved=1`;
  redirect(`/agents/${agent}/knowledge?${query}`);
}
