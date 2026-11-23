import { describe, expect, it } from 'vitest';
import { applySegment, type Line } from './transcript';

const seg = (streamId: string, text: string, attributes: Record<string, string> = {}) => ({
  streamId,
  text,
  attributes,
});

describe('applySegment', () => {
  it('treats text without a track id as the agent speaking', () => {
    const lines = applySegment([], seg('s1', 'Salama', { 'lk.segment_id': 'a1' }));
    expect(lines).toEqual([{ id: 'a1', role: 'agent', text: 'Salama', final: false }]);
  });

  it('treats a transcribed track as the user speaking', () => {
    const lines = applySegment(
      [],
      seg('s1', 'manao ahoana', {
        'lk.segment_id': 'u1',
        'lk.transcribed_track_id': 'TR_1',
        'lk.transcription_final': 'true',
      }),
    );
    expect(lines).toEqual([{ id: 'u1', role: 'user', text: 'manao ahoana', final: true }]);
  });

  it('replaces an existing segment instead of adding a line', () => {
    const first = applySegment([], seg('s1', 'Sal', { 'lk.segment_id': 'a1' }));
    const second = applySegment(first, seg('s2', 'Salama', { 'lk.segment_id': 'a1' }));
    expect(second).toHaveLength(1);
    expect(second[0]?.text).toBe('Salama');
  });

  it('keeps arrival order across speakers and does not mutate its input', () => {
    const start: readonly Line[] = [];
    const a = applySegment(start, seg('s1', 'one', { 'lk.segment_id': 'a' }));
    const b = applySegment(
      a,
      seg('s2', 'two', { 'lk.segment_id': 'b', 'lk.transcribed_track_id': 't' }),
    );
    expect(b.map((l) => l.text)).toEqual(['one', 'two']);
    expect(start).toHaveLength(0);
    expect(a).toHaveLength(1);
  });

  it('falls back to the stream id when there is no segment id', () => {
    const lines = applySegment([], seg('stream-9', 'x'));
    expect(lines[0]?.id).toBe('stream-9');
  });
});
