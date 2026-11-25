import { headers } from 'next/headers';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getAgent, isUuid } from '@/lib/agent-configurations';
import { rejectPlaygroundAccess } from '@/lib/playground-auth';
import Playground from './Playground';

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ agent?: string | string[] }>;
}): Promise<React.JSX.Element> {
  if (rejectPlaygroundAccess((await headers()).get('authorization'))) notFound();

  const { agent: selected } = await searchParams;
  if (selected === undefined) return <Playground />;
  if (!isUuid(selected)) notFound();

  let agent;
  try {
    agent = await getAgent(selected);
  } catch {
    return (
      <main className="shell">
        <h1>Babakoto</h1>
        <p className="error" role="alert">
          The configuration API is unavailable.
        </p>
        <Link href="/agents">Agent configurations</Link>
      </main>
    );
  }
  if (!agent) notFound();
  return <Playground key={agent.id} selectedAgent={{ id: agent.id, name: agent.name }} />;
}
