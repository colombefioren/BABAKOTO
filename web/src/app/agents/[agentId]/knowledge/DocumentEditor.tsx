'use client';

import { useActionState, useState } from 'react';
import type { KnowledgeDocument } from '@/lib/knowledge-documents';
import { changeDocument } from './actions';

export default function DocumentEditor({
  agent,
  document,
  editing,
  saved,
}: {
  agent: string;
  document: KnowledgeDocument;
  editing: boolean;
  saved: boolean;
}): React.JSX.Element {
  const [error, action, pending] = useActionState(changeDocument, null);
  const [title, setTitle] = useState(document.title);
  const [text, setText] = useState(document.text);
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <form className="agent-editor" action={action}>
      <input type="hidden" name="agent" value={agent} />
      <input type="hidden" name="document" value={document.id} />
      <fieldset className="agent-fields" disabled={pending}>
        <label htmlFor="document-title">Title</label>
        <input
          id="document-title"
          name="title"
          required
          maxLength={160}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <label htmlFor="document-text">Document text</label>
        <textarea
          id="document-text"
          name="text"
          required
          maxLength={10000}
          rows={12}
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <div className="agent-pages">
          <button type="submit" name="intent" value="save">
            Save document
          </button>
          {editing && !confirmDelete && (
            <button className="secondary" type="button" onClick={() => setConfirmDelete(true)}>
              Delete document
            </button>
          )}
        </div>
        {confirmDelete && (
          <div role="group" aria-label="Confirm document deletion">
            <p>Delete this document from the agent’s knowledge?</p>
            <div className="agent-pages">
              <button className="secondary" type="button" onClick={() => setConfirmDelete(false)}>
                Cancel
              </button>
              <button type="submit" name="intent" value="delete" formNoValidate>
                Confirm deletion
              </button>
            </div>
          </div>
        )}
      </fieldset>
      {pending && <p role="status">Updating document…</p>}
      {error && <p role="alert">{error}</p>}
      {saved && !pending && !error && <p role="status">Document saved.</p>}
    </form>
  );
}
