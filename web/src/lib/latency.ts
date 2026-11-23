/** Per-reply latency published by the agent on the `babakoto.latency` data topic. */

export const LATENCY_TOPIC = 'babakoto.latency';

export interface TurnLatency {
  /** End of user speech to first agent audio, seconds. */
  e2e: number;
  llmTtft: number | null;
  ttsTtfb: number | null;
}

const isNumberOrNull = (value: unknown): value is number | null =>
  value === null || (typeof value === 'number' && Number.isFinite(value));

/** Parse the agent's JSON payload, returning null for anything malformed. */
export function parseLatency(payload: Uint8Array): TurnLatency | null {
  let data: unknown;
  try {
    data = JSON.parse(new TextDecoder().decode(payload));
  } catch {
    return null;
  }
  if (typeof data !== 'object' || data === null) return null;
  const { e2e, llm_ttft: llm, tts_ttfb: tts } = data as Record<string, unknown>;
  if (typeof e2e !== 'number' || !Number.isFinite(e2e)) return null;
  const llmTtft = llm === undefined ? null : llm;
  const ttsTtfb = tts === undefined ? null : tts;
  if (!isNumberOrNull(llmTtft) || !isNumberOrNull(ttsTtfb)) return null;
  return { e2e, llmTtft, ttsTtfb };
}

/** Linear-interpolated percentile (q in 0..100); null for an empty list. */
export function percentile(values: readonly number[], q: number): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const rank = ((sorted.length - 1) * q) / 100;
  const low = Math.floor(rank);
  const high = Math.min(low + 1, sorted.length - 1);
  const lower = sorted[low] ?? 0;
  const upper = sorted[high] ?? lower;
  return lower + (upper - lower) * (rank - low);
}
