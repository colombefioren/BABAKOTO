import type { Metadata } from 'next';
import { headers } from 'next/headers';
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { rejectPlaygroundAccess } from '@/lib/playground-auth';
import AgentEditor from './AgentEditor';
import { getAgent, isUuid, listAgents, type AgentConfiguration } from '@/lib/agent-configurations';
import './agents.css';

export const metadata: Metadata = { title: 'Agent configurations · Babakoto' };

async function loadEditor(
  selected: string | undefined,
  after: string | undefined,
  creating: boolean,
) {
  try {
    const page = await listAgents(after);
    const agent = creating
      ? null
      : selected
        ? (page.items.find((item) => item.id === selected) ?? (await getAgent(selected)))
        : (page.items[0] ?? null);
    return { page, agent };
  } catch {
    return null;
  }
}

function agentLink(id: string, after: string | undefined): string {
  const parameters = new URLSearchParams({ agent: id });
  if (after) parameters.set('after', after);
  return `/agents?${parameters}`;
}

export default async function AgentsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<React.JSX.Element> {
  if (rejectPlaygroundAccess((await headers()).get('authorization'))) notFound();
  const query = await searchParams;
  if (query.agent !== undefined && !isUuid(query.agent)) redirect('/agents');
  if (query.after !== undefined && !isUuid(query.after)) redirect('/agents');
  const selected = query.agent;
  const after = query.after;
  const creating = query.new === '1';
  const data = await loadEditor(selected, after, creating);
  if (selected && data && data.agent === null && !creating) notFound();
  const formAgent: AgentConfiguration | null = data
    ? (data.agent ?? { id: crypto.randomUUID(), name: '', system_prompt: '', first_message: '' })
    : null;

  return (
    <main className="shell agent-dashboard">
      <nav aria-label="Babakoto">
        <Link href="/">Playground</Link>
      </nav>
      <header>
        <h1>Agent configurations</h1>
      </header>
      {data && formAgent ? (
        <div className="agent-workspace">
          <aside className="agent-directory" aria-labelledby="saved-agents-title">
            <h2 id="saved-agents-title">Saved agents</h2>
            <Link href="/agents?new=1">New agent</Link>
            {data.page.items.length === 0 ? (
              <p className="muted">No agents on this page.</p>
            ) : (
              <ul>
                {data.page.items.map((item) => (
                  <li key={item.id}>
                    <Link
                      href={agentLink(item.id, after)}
                      aria-current={data.agent?.id === item.id ? 'page' : undefined}
                    >
                      {item.name}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            <nav className="agent-pages" aria-label="Agent pages">
              {after && <Link href="/agents">First page</Link>}
              {data.page.next_after && (
                <Link href={`/agents?after=${data.page.next_after}`}>Next page</Link>
              )}
            </nav>
          </aside>
          <section className="agent-panel" aria-labelledby="agent-editor-title">
            <h2 id="agent-editor-title">{data.agent ? 'Edit agent' : 'New agent'}</h2>
            {data.agent && <Link href={`/?agent=${data.agent.id}`}>Open in playground</Link>}
            <AgentEditor
              key={formAgent.id}
              agent={formAgent}
              saved={query.saved === '1' && selected === formAgent.id}
            />
          </section>
        </div>
      ) : (
        <p className="error" role="alert">
          The configuration API is unavailable. Start it with <code>just up-dashboard</code>.
        </p>
      )}
    </main>
  );
}
