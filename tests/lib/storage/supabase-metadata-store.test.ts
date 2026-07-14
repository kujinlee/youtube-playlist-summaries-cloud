import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';

// ---------------------------------------------------------------------------
// Chainable mock SupabaseClient
// ---------------------------------------------------------------------------

/**
 * Builds a minimal chainable Supabase client stub that records calls and
 * returns preset data. Each query builder method returns `this` to support
 * the fluent chain (from().select().eq().maybeSingle() etc.).
 *
 * Design constraints:
 * - No live DB — every call is synchronous except the terminal `.maybeSingle()`,
 *   `.order()` (which returns the list), `.upsert()`, `.update()`, `.delete()`,
 *   and `.rpc()` — all of which are async.
 * - Calls are recorded on a flat `calls` array for assertion.
 */
function buildMockClient(overrides: {
  playlistRow?: { id: string; playlist_url: string; playlist_title?: string } | null;
  videoRows?: { data: unknown }[];
  rpcResults?: Record<string, unknown>;
  userId?: string;
  errors?: Record<string, string | null>;
  /** Rows returned by an `.update().select()` chain (e.g. setPlaylistTitleIfNull's
   *  conditional update) — a non-empty array simulates a row that matched the
   *  predicates (including `is('playlist_title', null)`) and was updated. */
  updateSelectResult?: { id: string }[];
} = {}) {
  const {
    playlistRow = null,
    videoRows = [],
    rpcResults = {},
    userId = 'user-uuid-1',
    errors = {},
    updateSelectResult = [],
  } = overrides;

  const calls: Array<{ method: string; args: unknown[] }> = [];

  function record(method: string, ...args: unknown[]) {
    calls.push({ method, args });
  }

  // Build a chainable query builder; the final terminal calls resolve.
  function makeBuilder(table: string) {
    const builder: Record<string, unknown> = {};
    let _filter: Record<string, unknown> = {};
    let _op: string | null = null;
    let _payload: unknown = null;
    let _upsertOpts: unknown = null;
    let _selectAfterOp = false;

    builder.select = (cols?: string) => {
      record('select', table, cols);
      // A .select() chained after .update() (setPlaylistTitleIfNull's
      // `.update().eq().eq().is().select('id')`) makes the builder terminal —
      // resolve with updateSelectResult instead of the plain update ack.
      if (_op === 'update') _selectAfterOp = true;
      return builder;
    };
    builder.eq = (col: string, val: unknown) => {
      record('eq', table, col, val);
      _filter[col] = val;
      return builder;
    };
    builder.is = (col: string, val: unknown) => {
      record('is', table, col, val);
      _filter[col] = val;
      return builder;
    };
    builder.order = (col: string, opts?: unknown) => {
      record('order', table, col, opts);
      // Terminal for video list queries — resolve immediately.
      const errKey = `${table}.select`;
      const err = errors[errKey] ? new Error(errors[errKey]!) : null;
      return Promise.resolve({ data: err ? null : videoRows, error: err });
    };
    builder.maybeSingle = () => {
      record('maybeSingle', table);
      const errKey = `${table}.maybeSingle`;
      const err = errors[errKey] ? new Error(errors[errKey]!) : null;
      // Return the playlist row if we are querying playlists, null otherwise.
      const data = err ? null : table === 'playlists' ? playlistRow : null;
      return Promise.resolve({ data, error: err });
    };
    builder.upsert = (payload: unknown, opts?: unknown) => {
      record('upsert', table, payload, opts);
      _op = 'upsert'; _payload = payload; _upsertOpts = opts;
      const errKey = `${table}.upsert`;
      const err = errors[errKey] ? new Error(errors[errKey]!) : null;
      return Promise.resolve({ data: null, error: err });
    };
    builder.update = (payload: unknown) => {
      record('update', table, payload);
      _op = 'update'; _payload = payload;
      return builder;
    };
    builder.delete = () => {
      record('delete', table);
      _op = 'delete';
      return builder;
    };

    // `.update().eq().eq()` chain — the second `.eq()` call is the terminal.
    // We override the Promise resolution by making the builder itself thenable
    // after an update or delete.
    builder.then = (resolve: (v: unknown) => unknown) => {
      // Only called when the builder is awaited directly (update/delete chain).
      const errKey = `${table}.${_op}`;
      const err = errors[errKey] ? new Error(errors[errKey]!) : null;
      if (_op === 'update' && _selectAfterOp) {
        return Promise.resolve({ data: err ? null : updateSelectResult, error: err }).then(resolve);
      }
      return Promise.resolve({ data: null, error: err }).then(resolve);
    };

    return builder;
  }

  const rpcCalls: Array<{ name: string; args: unknown }> = [];

  const client = {
    calls,
    rpcCalls,
    from(table: string) {
      record('from', table);
      return makeBuilder(table);
    },
    rpc(name: string, args: unknown) {
      record('rpc', name, args);
      rpcCalls.push({ name, args });
      const errKey = `rpc.${name}`;
      const err = errors[errKey] ? new Error(errors[errKey]!) : null;
      const data = err ? null : (rpcResults[name] ?? null);
      return Promise.resolve({ data, error: err });
    },
    auth: {
      getUser() {
        record('auth.getUser');
        return Promise.resolve({ data: { user: { id: userId } } });
      },
    },
  };

  return client;
}

// ---------------------------------------------------------------------------
// Convenience principal
// ---------------------------------------------------------------------------
const p = localPrincipal('listX');

// ---------------------------------------------------------------------------
// readIndex
// ---------------------------------------------------------------------------
describe('readIndex', () => {
  test('returns emptyPlaylistIndex when no playlist row exists', async () => {
    const client = buildMockClient({ playlistRow: null });
    const store = new SupabaseMetadataStore(client as any);
    const idx = await store.readIndex(p);
    expect(idx).toEqual({ playlistUrl: '', outputFolder: 'listX', videos: [] });
    // Should NOT query videos when playlist is absent.
    expect(client.calls.filter((c) => c.method === 'from' && c.args[0] === 'videos')).toHaveLength(0);
  });

  test('returns PlaylistIndex with videos ordered by position', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list', playlist_title: 'My List' },
      videoRows: [{ data: { id: 'v1' } }, { data: { id: 'v2' } }],
    });
    const store = new SupabaseMetadataStore(client as any);
    const idx = await store.readIndex(p);
    expect(idx.playlistUrl).toBe('https://yt.be/list');
    expect(idx.playlistTitle).toBe('My List');
    expect(idx.outputFolder).toBe('listX');
    expect(idx.videos).toEqual([
      { id: 'v1', summaryReady: false },
      { id: 'v2', summaryReady: false },
    ]);
    // Verify video query is ordered ascending.
    expect(client.calls.some((c) => c.method === 'order' && (c.args[2] as any)?.ascending === true)).toBe(true);
  });

  test('omits playlistTitle when playlist row has no title', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    const idx = await store.readIndex(p);
    expect('playlistTitle' in idx).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// setPlaylistMeta
// ---------------------------------------------------------------------------
describe('setPlaylistMeta', () => {
  test('upserts with owner_id from auth.getUser, playlist_key from principal', async () => {
    const client = buildMockClient({ userId: 'owner-uuid' });
    const store = new SupabaseMetadataStore(client as any);
    await store.setPlaylistMeta(p, { playlistUrl: 'https://yt.be/list', playlistTitle: 'T' });
    const upsertCall = client.calls.find((c) => c.method === 'upsert');
    expect(upsertCall).toBeDefined();
    const payload = upsertCall!.args[1] as any;
    expect(payload.owner_id).toBe('owner-uuid');
    expect(payload.playlist_key).toBe('listX');
    expect(payload.playlist_url).toBe('https://yt.be/list');
    expect(payload.playlist_title).toBe('T');
  });

  test('sets playlist_title to null when omitted', async () => {
    const client = buildMockClient({ userId: 'owner-uuid' });
    const store = new SupabaseMetadataStore(client as any);
    await store.setPlaylistMeta(p, { playlistUrl: 'https://yt.be/list' });
    const upsertCall = client.calls.find((c) => c.method === 'upsert');
    const payload = upsertCall!.args[1] as any;
    expect(payload.playlist_title).toBeNull();
  });

  test('passes onConflict option for owner_id,playlist_key', async () => {
    const client = buildMockClient({ userId: 'owner-uuid' });
    const store = new SupabaseMetadataStore(client as any);
    await store.setPlaylistMeta(p, { playlistUrl: 'https://yt.be/list' });
    const upsertCall = client.calls.find((c) => c.method === 'upsert');
    const opts = upsertCall!.args[2] as any;
    expect(opts?.onConflict).toBe('owner_id,playlist_key');
  });

  test('throws when no authenticated user', async () => {
    const client = buildMockClient({ userId: '' });
    // Override getUser to return no user.
    (client.auth as any).getUser = () => Promise.resolve({ data: { user: null } });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.setPlaylistMeta(p, { playlistUrl: 'https://yt.be/list' })).rejects.toThrow('no authenticated user');
  });
});

// ---------------------------------------------------------------------------
// claimVideoSlot
// ---------------------------------------------------------------------------
describe('claimVideoSlot', () => {
  test('calls claim_video_slot RPC with playlist_id and video_id, returns position+serialNumber', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
      rpcResults: { claim_video_slot: [{ position: 2, serial_number: 3 }] },
    });
    const store = new SupabaseMetadataStore(client as any);
    const result = await store.claimVideoSlot(p, 'vid1');
    expect(result).toEqual({ position: 2, serialNumber: 3 });
    const rpc = client.rpcCalls.find((c) => c.name === 'claim_video_slot');
    expect(rpc).toBeDefined();
    expect((rpc!.args as any).p_playlist_id).toBe('pl-id');
    expect((rpc!.args as any).p_video_id).toBe('vid1');
  });

  test('throws when playlist not found', async () => {
    const client = buildMockClient({ playlistRow: null });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.claimVideoSlot(p, 'vid1')).rejects.toThrow('playlist not found');
  });
});

// ---------------------------------------------------------------------------
// upsertVideo
// ---------------------------------------------------------------------------
describe('upsertVideo', () => {
  test('updates videos row with the full Video object', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    const video = { id: 'vid1' } as any;
    await store.upsertVideo(p, video);
    const updateCall = client.calls.find((c) => c.method === 'update');
    expect(updateCall).toBeDefined();
    expect((updateCall!.args[1] as any).data).toEqual(video);
    // Should filter by playlist_id and video_id.
    const eqCalls = client.calls.filter((c) => c.method === 'eq' && c.args[0] === 'videos');
    expect(eqCalls.some((c) => c.args[1] === 'playlist_id' && c.args[2] === 'pl-id')).toBe(true);
    expect(eqCalls.some((c) => c.args[1] === 'video_id' && c.args[2] === 'vid1')).toBe(true);
  });

  test('strips a caller-supplied updatedAt before writing to data', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    // Simulates a Video sourced from readIndex(), which surfaces updatedAt.
    const video = { id: 'vid1', updatedAt: '2026-01-01T00:00:00Z' } as any;
    await store.upsertVideo(p, video);
    const updateCall = client.calls.find((c) => c.method === 'update');
    expect(updateCall).toBeDefined();
    const written = (updateCall!.args[1] as any).data;
    expect(written).not.toHaveProperty('updatedAt');
    expect(written).toEqual({ id: 'vid1' });
  });

  test('strips a caller-supplied summaryReady (and updatedAt) before writing to data', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    // Simulates a Video sourced from readIndex(), which surfaces both
    // updatedAt and the derived summaryReady flag.
    const video = { id: 'vid1', updatedAt: 'x', summaryReady: true } as any;
    await store.upsertVideo(p, video);
    const updateCall = client.calls.find((c) => c.method === 'update');
    expect(updateCall).toBeDefined();
    const written = (updateCall!.args[1] as any).data;
    expect(written).not.toHaveProperty('summaryReady');
    expect(written).not.toHaveProperty('updatedAt');
    expect(written).toEqual({ id: 'vid1' });
  });
});

// ---------------------------------------------------------------------------
// updateVideoFields
// ---------------------------------------------------------------------------
describe('updateVideoFields', () => {
  test('calls merge_video_data RPC with correct args', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    await store.updateVideoFields(p, 'vid1', { summaryMd: 'hello' } as any);
    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data');
    expect(rpc).toBeDefined();
    expect((rpc!.args as any).p_playlist_id).toBe('pl-id');
    expect((rpc!.args as any).p_video_id).toBe('vid1');
    expect((rpc!.args as any).p_fields).toEqual({ summaryMd: 'hello' });
  });

  test('strips a caller-supplied updatedAt from p_fields before the RPC call', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    await store.updateVideoFields(p, 'vid1', {
      personalScore: 5,
      updatedAt: '2026-01-01T00:00:00Z',
    } as any);
    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data');
    expect(rpc).toBeDefined();
    const pFields = (rpc!.args as any).p_fields;
    expect(pFields).not.toHaveProperty('updatedAt');
    expect(pFields).toEqual({ personalScore: 5 });
  });
});

// ---------------------------------------------------------------------------
// bulkUpdateVideoFields
// ---------------------------------------------------------------------------
describe('bulkUpdateVideoFields', () => {
  test('calls merge_video_data_bulk with mapped { video_id, fields } shape', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    const patches = [
      { videoId: 'vid1', fields: { summaryMd: 'a' } as any },
      { videoId: 'vid2', fields: { summaryMd: 'b' } as any },
    ];
    await store.bulkUpdateVideoFields(p, patches);
    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
    expect(rpc).toBeDefined();
    expect((rpc!.args as any).p_playlist_id).toBe('pl-id');
    expect((rpc!.args as any).p_patches).toEqual([
      { video_id: 'vid1', fields: { summaryMd: 'a' } },
      { video_id: 'vid2', fields: { summaryMd: 'b' } },
    ]);
  });

  test('passes playlist_id derived from playlist_key lookup', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-uuid-42', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    await store.bulkUpdateVideoFields(p, [{ videoId: 'v1', fields: {} as any }]);
    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
    expect((rpc!.args as any).p_playlist_id).toBe('pl-uuid-42');
  });

  test('strips a caller-supplied updatedAt from each patch fields before the RPC call', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    const patches = [
      { videoId: 'vid1', fields: { summaryMd: 'a', updatedAt: '2026-01-01T00:00:00Z' } as any },
      { videoId: 'vid2', fields: { summaryMd: 'b', updatedAt: '2026-01-02T00:00:00Z' } as any },
    ];
    await store.bulkUpdateVideoFields(p, patches);
    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
    expect(rpc).toBeDefined();
    const pPatches = (rpc!.args as any).p_patches;
    expect(pPatches).toEqual([
      { video_id: 'vid1', fields: { summaryMd: 'a' } },
      { video_id: 'vid2', fields: { summaryMd: 'b' } },
    ]);
    for (const patch of pPatches) {
      expect(patch.fields).not.toHaveProperty('updatedAt');
    }
  });
});

// ---------------------------------------------------------------------------
// reconcilePlaylistMembership
// ---------------------------------------------------------------------------
describe('reconcilePlaylistMembership', () => {
  test('calls reconcile_membership RPC with playlist_id and present ids array', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    await store.reconcilePlaylistMembership(p, ['vid1', 'vid2']);
    const rpc = client.rpcCalls.find((c) => c.name === 'reconcile_membership');
    expect(rpc).toBeDefined();
    expect((rpc!.args as any).p_playlist_id).toBe('pl-id');
    expect((rpc!.args as any).p_present).toEqual(['vid1', 'vid2']);
  });

  test('throws when playlist not found', async () => {
    const client = buildMockClient({ playlistRow: null });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.reconcilePlaylistMembership(p, [])).rejects.toThrow('playlist not found');
  });
});

// ---------------------------------------------------------------------------
// deleteVideo
// ---------------------------------------------------------------------------
describe('deleteVideo', () => {
  test('deletes from videos filtered by playlist_id and video_id', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: 'https://yt.be/list' },
    });
    const store = new SupabaseMetadataStore(client as any);
    await store.deleteVideo(p, 'vid-to-delete');
    expect(client.calls.some((c) => c.method === 'delete' && c.args[0] === 'videos')).toBe(true);
    const eqCalls = client.calls.filter((c) => c.method === 'eq' && c.args[0] === 'videos');
    expect(eqCalls.some((c) => c.args[1] === 'playlist_id' && c.args[2] === 'pl-id')).toBe(true);
    expect(eqCalls.some((c) => c.args[1] === 'video_id' && c.args[2] === 'vid-to-delete')).toBe(true);
  });

  test('throws when playlist not found', async () => {
    const client = buildMockClient({ playlistRow: null });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.deleteVideo(p, 'vid1')).rejects.toThrow('playlist not found');
  });
});

// ---------------------------------------------------------------------------
// setPlaylistTitleIfNull
// ---------------------------------------------------------------------------
describe('setPlaylistTitleIfNull', () => {
  test('updates playlist_title and scopes by owner_id, playlist_key, is-null; returns {updated:true} on a matched row', async () => {
    const client = buildMockClient({ userId: 'owner-uuid', updateSelectResult: [{ id: 'pl-id' }] });
    const store = new SupabaseMetadataStore(client as any);
    const result = await store.setPlaylistTitleIfNull(p, 'Real Title');
    expect(result).toEqual({ updated: true });

    const updateCall = client.calls.find((c) => c.method === 'update' && c.args[0] === 'playlists');
    expect(updateCall).toBeDefined();
    expect(updateCall!.args[1]).toEqual({ playlist_title: 'Real Title' });

    const eqCalls = client.calls.filter((c) => c.method === 'eq' && c.args[0] === 'playlists');
    expect(eqCalls.some((c) => c.args[1] === 'owner_id' && c.args[2] === 'owner-uuid')).toBe(true);
    // playlist_key predicate comes from p.indexKey — NOT a separate listId param.
    expect(eqCalls.some((c) => c.args[1] === 'playlist_key' && c.args[2] === p.indexKey)).toBe(true);

    const isCall = client.calls.find((c) => c.method === 'is' && c.args[0] === 'playlists');
    expect(isCall).toBeDefined();
    expect(isCall!.args[1]).toBe('playlist_title');
    expect(isCall!.args[2]).toBeNull();
  });

  test('returns {updated:false} when no row matches (already titled — is-null predicate excludes it)', async () => {
    const client = buildMockClient({ userId: 'owner-uuid', updateSelectResult: [] });
    const store = new SupabaseMetadataStore(client as any);
    const result = await store.setPlaylistTitleIfNull(p, 'Real Title');
    expect(result).toEqual({ updated: false });
  });

  test('throws when no authenticated user', async () => {
    const client = buildMockClient({ userId: '' });
    (client.auth as any).getUser = () => Promise.resolve({ data: { user: null } });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.setPlaylistTitleIfNull(p, 'Real Title')).rejects.toThrow('no authenticated user');
  });
});

// ---------------------------------------------------------------------------
// deletePlaylist
// ---------------------------------------------------------------------------
describe('deletePlaylist', () => {
  test('deletes from playlists filtered by BOTH id and owner_id', async () => {
    const client = buildMockClient({ userId: 'owner-uuid' });
    const store = new SupabaseMetadataStore(client as any);
    await store.deletePlaylist(p, 'pl-id-1');
    expect(client.calls.some((c) => c.method === 'delete' && c.args[0] === 'playlists')).toBe(true);
    const eqCalls = client.calls.filter((c) => c.method === 'eq' && c.args[0] === 'playlists');
    expect(eqCalls.some((c) => c.args[1] === 'id' && c.args[2] === 'pl-id-1')).toBe(true);
    expect(eqCalls.some((c) => c.args[1] === 'owner_id' && c.args[2] === 'owner-uuid')).toBe(true);
  });

  test('throws when no authenticated user', async () => {
    const client = buildMockClient({ userId: '' });
    (client.auth as any).getUser = () => Promise.resolve({ data: { user: null } });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.deletePlaylist(p, 'pl-id-1')).rejects.toThrow('no authenticated user');
  });

  test('throws on delete error', async () => {
    const client = buildMockClient({ userId: 'owner-uuid', errors: { 'playlists.delete': 'db down' } });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.deletePlaylist(p, 'pl-id-1')).rejects.toThrow('db down');
  });
});

// ---------------------------------------------------------------------------
// Error propagation
// ---------------------------------------------------------------------------
describe('error propagation', () => {
  test('readIndex throws when playlist query fails', async () => {
    const client = buildMockClient({ errors: { 'playlists.maybeSingle': 'DB error' } });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.readIndex(p)).rejects.toThrow('DB error');
  });

  test('claimVideoSlot throws on RPC error', async () => {
    const client = buildMockClient({
      playlistRow: { id: 'pl-id', playlist_url: '' },
      errors: { 'rpc.claim_video_slot': 'rpc failed' },
    });
    const store = new SupabaseMetadataStore(client as any);
    await expect(store.claimVideoSlot(p, 'vid1')).rejects.toThrow('rpc failed');
  });
});
