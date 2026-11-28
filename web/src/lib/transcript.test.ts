import { describe, expect, it } from 'vitest';
import { applySegment, type Line } from './transcript';

const caller = 'caller-identity';
const seg = (
  streamId: string,
  text: string,
  attributes: Record<string, string> = {},
  senderIdentity = 'agent-identity',
) => ({ streamId, text, attributes, senderIdentity });

describe('applySegment', () => {
  it('labels text from the remote agent even without a track id', () => {
    const lines = applySegment([], seg('s1', 'Salama', { 'lk.segment_id': 'a1' }), caller);
    expect(lines).toEqual([{ id: 'a1', role: 'agent', text: 'Salama', final: false }]);
  });

  it('labels the local participant as the caller', () => {
    const lines = applySegment(
      [],
      seg(
        's1',
        'manao ahoana',
        {
          'lk.segment_id': 'u1',
          'lk.transcribed_track_id': 'TR_CALLER',
          'lk.transcription_final': 'true',
        },
        caller,
      ),
      caller,
    );
    expect(lines).toEqual([{ id: 'u1', role: 'user', text: 'manao ahoana', final: true }]);
  });

  it('uses the speaker identity when the agent also has a transcribed track', () => {
    const segment = seg('agent-stream', 'Welcome', { 'lk.transcribed_track_id': 'TR_AGENT' });
    const lines = applySegment([], segment, caller);
    expect(lines[0]?.role).toBe('agent');
  });

  it('replaces an existing segment instead of adding a line', () => {
    const first = applySegment([], seg('s1', 'Sal', { 'lk.segment_id': 'a1' }), caller);
    const second = applySegment(first, seg('s2', 'Salama', { 'lk.segment_id': 'a1' }), caller);
    expect(second).toHaveLength(1);
    expect(second[0]?.text).toBe('Salama');
  });

  it('keeps arrival order across speakers and does not mutate its input', () => {
    const start: readonly Line[] = [];
    const a = applySegment(start, seg('s1', 'one', { 'lk.segment_id': 'a' }), caller);
    const b = applySegment(
      a,
      seg('s2', 'two', { 'lk.segment_id': 'b', 'lk.transcribed_track_id': 't' }, caller),
      caller,
    );
    expect(b.map((l) => l.text)).toEqual(['one', 'two']);
    expect(start).toHaveLength(0);
    expect(a).toHaveLength(1);
  });

  it('falls back to the stream id when there is no segment id', () => {
    const lines = applySegment([], seg('stream-9', 'x'), caller);
    expect(lines[0]?.id).toBe('stream-9');
  });
});
