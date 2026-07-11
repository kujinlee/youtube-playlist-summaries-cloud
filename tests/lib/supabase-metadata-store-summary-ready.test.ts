import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';

// ---------------------------------------------------------------------------
// Chainable mock SupabaseClient — mirrors the helper in
// tests/lib/storage/supabase-metadata-store.test.ts (same shape; duplicated
// here per that file's own pattern rather than imported, since the helper is
// not exported). Only the readIndex path (playlists.maybeSingle +
// videos.order) is exercised by this test file.
// ---------------------------------------------------------------------------
function buildMockClient(overrides: {
  playlistRow?: { id: string; playlist_url: string; playlist_title?: string } | null;
  videoRows?: { data: unknown; updated_at?: string }[];
  errors?: Record<string, string | null>;
} = {}) {
  const {
    playlistRow = null,
    videoRows = [],
    errors = {},
  } = overrides;

  const calls: Array<{ method: string; args: unknown[] }> = [];

  function record(method: string, ...args: unknown[]) {
    calls.push({ method, args });
  }

  function makeBuilder(table: string) {
    const builder: Record<string, unknown> = {};

    builder.select = (cols?: string) => {
      record('select', table, cols);
      return builder;
    };
    builder.eq = (col: string, val: unknown) => {
      record('eq', table, col, val);
      return builder;
    };
    builder.order = (col: string, opts?: unknown) => {
      record('order', table, col, opts);
      const errKey = `${table}.select`;
      const err = errors[errKey] ? new Error(errors[errKey]!) : null;
      return Promise.resolve({ data: err ? null : videoRows, error: err });
    };
    builder.maybeSingle = () => {
      record('maybeSingle', table);
      const errKey = `${table}.maybeSingle`;
      const err = errors[errKey] ? new Error(errors[errKey]!) : null;
      const data = err ? null : table === 'playlists' ? playlistRow : null;
      return Promise.resolve({ data, error: err });
    };

    return builder;
  }

  const client = {
    calls,
    from(table: string) {
      record('from', table);
      return makeBuilder(table);
    },
  };

  return client;
}

// ---------------------------------------------------------------------------
// Convenience principal
// ---------------------------------------------------------------------------
const p = localPrincipal('listX');

// ---------------------------------------------------------------------------
// readIndex — summaryReady derivation
// ---------------------------------------------------------------------------
describe('readIndex — summaryReady derivation', () => {
  test('derives true for promoted, false for committed, false for artifacts-absent', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
      videoRows: [
        {
          data: {
            id: 'a',
            title: 'A',
            youtubeUrl: 'https://www.youtube.com/watch?v=a',
            language: 'en',
            durationSeconds: 100,
            archived: false,
            ratings: { usefulness: 4, depth: 3, originality: 5, recency: 4, completeness: 3 },
            overallScore: 3.8,
            summaryMd: 'hello',
            processedAt: '2026-01-01T00:00:00.000Z',
            artifacts: { summaryMd: { status: 'promoted' } },
          },
          updated_at: '2026-07-11T00:00:00.000Z',
        },
        {
          data: {
            id: 'b',
            title: 'B',
            youtubeUrl: 'https://www.youtube.com/watch?v=b',
            language: 'en',
            durationSeconds: 100,
            archived: false,
            ratings: { usefulness: 4, depth: 3, originality: 5, recency: 4, completeness: 3 },
            overallScore: 3.8,
            summaryMd: 'hello',
            processedAt: '2026-01-01T00:00:00.000Z',
            artifacts: { summaryMd: { status: 'committed' } },
          },
          updated_at: '2026-07-11T00:00:00.000Z',
        },
        {
          data: {
            id: 'c',
            title: 'C',
            youtubeUrl: 'https://www.youtube.com/watch?v=c',
            language: 'en',
            durationSeconds: 100,
            archived: false,
            ratings: { usefulness: 4, depth: 3, originality: 5, recency: 4, completeness: 3 },
            overallScore: 3.8,
            summaryMd: 'hello',
            processedAt: '2026-01-01T00:00:00.000Z',
            // no artifacts
          },
          updated_at: '2026-07-11T00:00:00.000Z',
        },
      ],
    });
    const store = new SupabaseMetadataStore(client as any);
    const index = await store.readIndex(p);

    expect(index.videos.find((v) => v.id === 'a')!.summaryReady).toBe(true);
    expect(index.videos.find((v) => v.id === 'b')!.summaryReady).toBe(false);
    expect(index.videos.find((v) => v.id === 'c')!.summaryReady).toBe(false);
  });
});
