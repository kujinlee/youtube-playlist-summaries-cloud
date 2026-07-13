import { digSectionKey, digJobVersion } from '@/lib/dig/cloud/dig-blob-key';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';

it('key shape: dig/{base}/{sectionId}.r{V}.md', () => {
  expect(digSectionKey('0007_intro', 132)).toBe(`dig/0007_intro/132.r${DIG_GENERATOR_VERSION}.md`);
});
it('job version encodes the dig generator version', () => {
  expect(digJobVersion()).toBe(`dig-${DIG_GENERATOR_VERSION}`);
});
it.each([['neg', -1], ['float', 1.5], ['nan', NaN]])('rejects a non-nonneg-int sectionId: %s', (_l, bad) => {
  expect(() => digSectionKey('b', bad as number)).toThrow(/invalid dig sectionId/);
});
it.each([
  ['slash', 'a/b'],
  ['backslash', 'a\\b'],
  ['parent', '..'],
  ['lone-dot', '.'],
  ['nul', 'a\0b'],
  ['empty', ''],
])('rejects an unsafe base: %s', (_l, bad) => {
  expect(() => digSectionKey(bad, 1)).toThrow();
});
