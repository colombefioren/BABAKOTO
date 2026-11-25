'use client';

import { useActionState, useState } from 'react';
import { saveAgent } from './actions';
import type { AgentConfiguration } from './api';

export default function AgentEditor({
  agent,
  saved,
}: {
  agent: AgentConfiguration;
  saved: boolean;
}): React.JSX.Element {
  const [error, action, pending] = useActionState(saveAgent, null);
  const [name, setName] = useState(agent.name);
  const [prompt, setPrompt] = useState(agent.system_prompt);
  const [greeting, setGreeting] = useState(agent.first_message);

  return (
    <form action={action} className="agent-editor">
      <input type="hidden" name="id" value={agent.id} />
      <fieldset className="agent-fields" disabled={pending}>
        <label htmlFor="agent-name">Name</label>
        <input
          id="agent-name"
          name="name"
          required
          maxLength={100}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <label htmlFor="agent-prompt">System prompt</label>
        <textarea
          id="agent-prompt"
          name="system_prompt"
          required
          rows={8}
          maxLength={8000}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
        />
        <label htmlFor="agent-greeting">Greeting (optional)</label>
        <textarea
          id="agent-greeting"
          name="first_message"
          rows={3}
          maxLength={500}
          value={greeting}
          onChange={(event) => setGreeting(event.target.value)}
        />
        <button type="submit">{pending ? 'Saving…' : 'Save agent'}</button>
      </fieldset>
      {error && <p role="alert">{error}</p>}
      {saved && !pending && !error && <p role="status">Agent configuration saved.</p>}
    </form>
  );
}
