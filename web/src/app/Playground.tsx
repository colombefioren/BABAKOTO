'use client';

import Link from 'next/link';
import { Room, RoomEvent, type Track } from 'livekit-client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { LATENCY_TOPIC, parseLatency, percentile, type TurnLatency } from '@/lib/latency';
import { applySegment, TRANSCRIPTION_TOPIC, type Line } from '@/lib/transcript';

type Status = 'idle' | 'connecting' | 'live' | 'error';

const seconds = (value: number | null): string =>
  value === null ? 'n/a' : `${value.toFixed(2)} s`;

export default function Playground({
  selectedAgent,
}: {
  selectedAgent?: { id: string; name: string };
}): React.JSX.Element {
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [turns, setTurns] = useState<TurnLatency[]>([]);
  const roomRef = useRef<Room | null>(null);
  const audioRef = useRef<HTMLDivElement>(null);

  const stop = useCallback(async () => {
    const room = roomRef.current;
    roomRef.current = null;
    if (room) await room.disconnect();
    if (audioRef.current) audioRef.current.replaceChildren();
    setStatus('idle');
  }, []);

  useEffect(
    () => () => {
      void roomRef.current?.disconnect();
    },
    [],
  );

  const start = useCallback(async () => {
    setStatus('connecting');
    setError(null);
    setLines([]);
    setTurns([]);
    try {
      const endpoint = selectedAgent ? `/api/token?agent=${selectedAgent.id}` : '/api/token';
      const response = await fetch(endpoint, { method: 'POST' });
      const body = (await response.json()) as { token?: string; url?: string; error?: string };
      if (!response.ok || !body.token || !body.url) {
        throw new Error(body.error ?? `Token request failed (${response.status})`);
      }
      const room = new Room();
      roomRef.current = room;

      room.registerTextStreamHandler(TRANSCRIPTION_TOPIC, async (reader) => {
        let text = '';
        for await (const chunk of reader) {
          text += chunk;
          setLines((current) =>
            applySegment(current, {
              streamId: reader.info.id,
              attributes: reader.info.attributes ?? {},
              text,
            }),
          );
        }
      });
      room.on(RoomEvent.DataReceived, (payload, _participant, _kind, topic) => {
        if (topic !== LATENCY_TOPIC) return;
        const turn = parseLatency(payload);
        if (turn) setTurns((current) => [...current, turn]);
      });
      room.on(RoomEvent.TrackSubscribed, (track: Track) => {
        if (track.kind === 'audio') audioRef.current?.append(track.attach());
      });
      room.on(RoomEvent.Disconnected, () => setStatus('idle'));

      await room.connect(body.url, body.token);
      await room.localParticipant.setMicrophoneEnabled(true);
      setStatus('live');
    } catch (caught) {
      roomRef.current?.disconnect().catch(() => undefined);
      roomRef.current = null;
      setError(caught instanceof Error ? caught.message : 'Could not start the conversation');
      setStatus('error');
    }
  }, [selectedAgent]);

  const e2e = turns.map((turn) => turn.e2e);
  const last = turns.at(-1);
  const live = status === 'live';

  return (
    <main className="shell">
      <header>
        <h1>Babakoto</h1>
        <p className="muted">Talk to a Malagasy voice agent. Captions are always on.</p>
        {selectedAgent && <p className="muted">Selected agent: {selectedAgent.name}</p>}
        <Link className="configuration-link" href="/agents">
          Agent configurations
        </Link>
      </header>

      <button
        type="button"
        className="mic"
        aria-pressed={live}
        disabled={status === 'connecting'}
        onClick={() => void (live ? stop() : start())}
      >
        {status === 'connecting' ? 'Connecting…' : live ? 'End conversation' : 'Start conversation'}
      </button>
      <p role="status" className="muted">
        {status === 'live' && 'Listening. Speak when you are ready.'}
        {status === 'idle' && 'Not connected. Your browser will ask for microphone access.'}
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      <section aria-labelledby="transcript-title">
        <h2 id="transcript-title">Transcript</h2>
        <ol className="transcript" aria-live="polite" aria-relevant="additions text">
          {lines.length === 0 && <li className="muted">Nothing said yet.</li>}
          {lines.map((line) => (
            <li key={line.id} className={line.role} data-final={line.final}>
              <strong>{line.role === 'user' ? 'You' : 'Agent'}</strong>
              <span>{line.text}</span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="latency-title">
        <h2 id="latency-title">Latency</h2>
        <p className="muted">End of your speech to first agent audio, per reply.</p>
        <dl className="stats">
          <div>
            <dt>Last reply</dt>
            <dd data-testid="latency-last">{seconds(last?.e2e ?? null)}</dd>
          </div>
          <div>
            <dt>Median (p50)</dt>
            <dd data-testid="latency-p50">{seconds(percentile(e2e, 50))}</dd>
          </div>
          <div>
            <dt>p95</dt>
            <dd data-testid="latency-p95">{seconds(percentile(e2e, 95))}</dd>
          </div>
          <div>
            <dt>Replies</dt>
            <dd>{turns.length}</dd>
          </div>
        </dl>
        {last && (
          <p className="muted">
            Last reply: model {seconds(last.llmTtft)}, voice {seconds(last.ttsTtfb)}.
          </p>
        )}
      </section>

      <div ref={audioRef} hidden />
    </main>
  );
}
