import { VideoSchema } from '@/types';
import { ModelEnvelopeSchema } from '@/lib/html-doc/model-store';

const baseVideo = {
  id: 'v1', title: 'T', youtubeUrl: 'https://youtu.be/v1', language: 'en',
  durationSeconds: 1, archived: false,
  ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
};

describe('VideoSchema sync signals', () => {
  it('accepts the new optional signal fields', () => {
    const v = VideoSchema.parse({
      ...baseVideo,
      mdGeneratedAt: '2026-07-17T00:00:00.000Z',
      mdCorrectionsHash: 'abc',
      annotationsEditedAt: { personalNote: '2026-07-17T00:00:00.000Z' },
    });
    expect(v.mdCorrectionsHash).toBe('abc');
    expect(v.annotationsEditedAt?.personalNote).toBeDefined();
  });
  it('still parses a legacy record with none of them', () => {
    expect(() => VideoSchema.parse(baseVideo)).not.toThrow();
  });
});

describe('ModelEnvelopeSchema forward tolerance', () => {
  const env = {
    sourceMd: 'x', generatedAt: '2026-07-17', sourceSections: ['A'],
    model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
  };
  it('accepts an optional sourceMdHash', () => {
    expect(ModelEnvelopeSchema.parse({ ...env, sourceMdHash: 'deadbeef' }).sourceMdHash).toBe('deadbeef');
  });
  it('ignores an unknown future key instead of failing (no .strict())', () => {
    expect(() => ModelEnvelopeSchema.parse({ ...env, futureKey: 1 })).not.toThrow();
  });
});
