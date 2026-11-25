import type { Metadata } from 'next';
import { headers } from 'next/headers';
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { getAgent, isUuid } from '@/lib/agent-configurations';
import { getDocument, listDocuments } from '@/lib/knowledge-documents';
import { rejectPlaygroundAccess } from '@/lib/playground-auth';
import DocumentEditor from './DocumentEditor';
import '../../agents.css';

export const metadata: Metadata = { title: 'Agent knowledge · Babakoto' };

async function loadKnowledge(agentId: string, documentId?: string, after?: string) {
  try {
    const [agent, page, document] = await Promise.all([
      getAgent(agentId),
      listDocuments(agentId, after),
      documentId ? getDocument(agentId, documentId) : null,
    ]);
    return { agent, page, document };
  } catch {
    return null;
  }
}

export default async function KnowledgePage({
  params,
  searchParams,
}: {
  params: Promise<{ agentId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<React.JSX.Element> {
  if (rejectPlaygroundAccess((await headers()).get('authorization'))) notFound();
  const { agentId } = await params;
  if (!isUuid(agentId)) notFound();
  const path = `/agents/${agentId}/knowledge`;
  const query = await searchParams;
  if (query.document !== undefined && !isUuid(query.document)) redirect(path);
  if (query.after !== undefined && !isUuid(query.after)) redirect(path);
  const data = await loadKnowledge(agentId, query.document?.toLowerCase(), query.after);
  if (data && (!data.agent || !data.page || (query.document && !data.document))) notFound();

  const document = data?.document ?? { id: crypto.randomUUID(), title: '', text: '' };
  return (
    <main className="shell agent-dashboard">
      <nav aria-label="Babakoto">
        <Link href={`/agents?agent=${agentId}`}>Back to agent</Link>
      </nav>
      <header>
        <h1>Agent knowledge</h1>
        {data?.agent && <p className="muted">{data.agent.name}</p>}
      </header>
      {data?.page ? (
        <div className="agent-workspace">
          <aside className="agent-directory" aria-labelledby="documents-title">
            <h2 id="documents-title">Documents</h2>
            <Link href={path}>New document</Link>
            {data.page.items.length === 0 ? (
              <p className="muted">No documents on this page.</p>
            ) : (
              <ul>
                {data.page.items.map((item) => {
                  const search = new URLSearchParams({ document: item.id });
                  if (query.after && typeof query.after === 'string')
                    search.set('after', query.after);
                  return (
                    <li key={item.id}>
                      <Link
                        href={`${path}?${search}`}
                        prefetch={false}
                        aria-current={document.id === item.id ? 'page' : undefined}
                      >
                        {item.title}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
            <nav className="agent-pages" aria-label="Document pages">
              {query.after && <Link href={path}>First page</Link>}
              {data.page.next_after && (
                <Link href={`${path}?after=${data.page.next_after}`}>Next page</Link>
              )}
            </nav>
          </aside>
          <section className="agent-panel" aria-labelledby="document-editor-title">
            <h2 id="document-editor-title">{data.document ? 'Edit document' : 'New document'}</h2>
            {query.deleted === '1' && <p role="status">Document deleted.</p>}
            <DocumentEditor
              key={document.id}
              agent={agentId}
              document={document}
              editing={Boolean(data.document)}
              saved={Boolean(data.document) && query.saved === '1'}
            />
          </section>
        </div>
      ) : (
        <p className="error" role="alert">
          The knowledge API is unavailable. Start it with <code>just up-dashboard</code>.
        </p>
      )}
    </main>
  );
}
