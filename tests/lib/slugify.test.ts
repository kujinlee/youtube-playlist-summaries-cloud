import { slugify } from '../../lib/slugify';

describe('slugify', () => {
  it('lowercases and replaces spaces with hyphens', () => {
    expect(slugify('Hello World')).toBe('hello-world');
  });

  it('handles Unicode letters and numbers', () => {
    expect(slugify('안녕 World')).toBe('안녕-world');
  });

  it('trims result to 60 characters', () => {
    expect(slugify('A'.repeat(80))).toHaveLength(60);
  });

  it('strips leading and trailing hyphens', () => {
    expect(slugify('  hello  ')).toBe('hello');
  });

  it('collapses multiple separators to a single hyphen', () => {
    expect(slugify('Stanford CS146S – 2025')).toBe('stanford-cs146s-2025');
  });

  it('handles playlist IDs with no separators', () => {
    expect(slugify('PLtest123')).toBe('pltest123');
  });
});
