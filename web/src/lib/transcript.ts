/** Live transcript state: turns a stream of partial segments into ordered lines. */

export type Role = 'user' | 'agent';

export interface Line {
  id: string;
  role: Role;
  text: string;
  final: boolean;
}

/** LiveKit text-stream attributes used by `lk.transcription`. */
export const ATTR_SEGMENT_ID = 'lk.segment_id';
export const ATTR_TRACK_ID = 'lk.transcribed_track_id';
export const ATTR_FINAL = 'lk.transcription_final';
export const TRANSCRIPTION_TOPIC = 'lk.transcription';

export interface SegmentInput {
  /** `reader.info.id` of the stream, used when the segment attribute is missing. */
  streamId: string;
  attributes: Record<string, string>;
  /** Text received so far for this segment. */
  text: string;
}

/**
 * Agent text arrives as deltas of one segment while the user's words arrive as
 * (usually) replaceable interim results; both are keyed by segment id.
 */
export function applySegment(lines: readonly Line[], segment: SegmentInput): Line[] {
  const id = segment.attributes[ATTR_SEGMENT_ID] ?? segment.streamId;
  const role: Role = ATTR_TRACK_ID in segment.attributes ? 'user' : 'agent';
  const final = segment.attributes[ATTR_FINAL] === 'true';
  const next: Line = { id, role, text: segment.text, final };
  const index = lines.findIndex((line) => line.id === id);
  if (index === -1) return [...lines, next];
  const copy = [...lines];
  copy[index] = next;
  return copy;
}
