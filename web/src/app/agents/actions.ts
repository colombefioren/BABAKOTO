'use server';

import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { isSameOrigin } from '@/lib/guard';
import { rejectPlaygroundAccess } from '@/lib/playground-auth';
import { isUuid, putAgent } from './api';

export async function saveAgent(_previous: string | null, data: FormData): Promise<string | null> {
  const requestHeaders = await headers();
  if (
    !isSameOrigin(requestHeaders) ||
    rejectPlaygroundAccess(requestHeaders.get('authorization'))
  ) {
    return 'Sign in again before saving an agent.';
  }

  const id = data.get('id');
  const name = data.get('name');
  const prompt = data.get('system_prompt');
  const greeting = data.get('first_message');
  if (
    !isUuid(id) ||
    typeof name !== 'string' ||
    !name.trim() ||
    name.length > 100 ||
    typeof prompt !== 'string' ||
    !prompt.trim() ||
    prompt.length > 8000 ||
    typeof greeting !== 'string' ||
    greeting.length > 500
  ) {
    return 'Enter a name and a system prompt within the field limits.';
  }

  try {
    const saved = await putAgent(id, {
      name,
      system_prompt: prompt,
      first_message: greeting,
    });
    if (!saved) return 'Could not save this configuration. Check the fields and try again.';
  } catch {
    return 'The configuration API is unavailable. Your changes are still in the form.';
  }

  redirect(`/agents?agent=${id}&saved=1`);
}
