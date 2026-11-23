import { describe, expect, it } from 'vitest';
import { parseLatency, percentile } from './latency';

const bytes = (value: unknown): Uint8Array => new TextEncoder().encode(JSON.stringify(value));

describe('parseLatency', () => {
  it('reads the agent payload', () => {
    expect(parseLatency(bytes({ e2e: 1.2, llm_ttft: 0.4, tts_ttfb: 0.5 }))).toEqual({
      e2e: 1.2,
      llmTtft: 0.4,
      ttsTtfb: 0.5,
    });
  });

  it('accepts missing or null stages', () => {
    expect(parseLatency(bytes({ e2e: 0.9 }))).toEqual({ e2e: 0.9, llmTtft: null, ttsTtfb: null });
    expect(parseLatency(bytes({ e2e: 0.9, llm_ttft: null, tts_ttfb: null }))?.llmTtft).toBeNull();
  });

  it.each([
    ['not json', new TextEncoder().encode('nope')],
    ['a string', bytes('x')],
    ['null', bytes(null)],
    ['no e2e', bytes({ llm_ttft: 1 })],
    ['text e2e', bytes({ e2e: '1' })],
    ['non-finite stage', bytes({ e2e: 1, llm_ttft: 'x' })],
  ])('rejects %s', (_name, payload) => {
    expect(parseLatency(payload)).toBeNull();
  });
});

describe('percentile', () => {
  it('is null for no data', () => {
    expect(percentile([], 50)).toBeNull();
  });

  it('interpolates', () => {
    const values = Array.from({ length: 100 }, (_, i) => i + 1);
    expect(percentile(values, 50)).toBeCloseTo(50.5);
    expect(percentile(values, 95)).toBeCloseTo(95.05);
    expect(percentile([3, 1], 0)).toBe(1);
    expect(percentile([2], 95)).toBe(2);
  });
});
