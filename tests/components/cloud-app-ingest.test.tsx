/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';

const push = jest.fn();
const replace = jest.fn();
let searchParamsValue = new URLSearchParams('');
const setSearchParams = (v: string) => (searchParamsValue = new URLSearchParams(v));
jest.mock('next/navigation', () => ({ useRouter: () => ({ push, replace }), useSearchParams: () => searchParamsValue }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  class IngestError extends Error { constructor(public status: number, public info: any = {}) { super('e'); } }
  return {
    listPlaylists: jest.fn().mockResolvedValue([]),
    listVideos: jest.fn().mockResolvedValue({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=X', playlistTitle: 'X' }),
    createIngest: jest.fn(),
    backfillPlaylistTitles: jest.fn().mockResolvedValue({ updated: 1, attempted: 1 }),
    getJobStatus: jest.fn().mockResolvedValue({ jobs: [], rollup: { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false } }),
    ingestErrorMessage: (e: any) => `msg-${e.status}`,
    IngestError, UnauthorizedError,
  };
});
import CloudApp from '@/components/cloud/CloudApp';
import { createIngest, listPlaylists, backfillPlaylistTitles } from '@/lib/client/api';
const createIngestMock = createIngest as jest.MockedFunction<typeof createIngest>;
const listPlaylistsMock = listPlaylists as jest.MockedFunction<typeof listPlaylists>;
const backfillPlaylistTitlesMock = backfillPlaylistTitles as jest.MockedFunction<typeof backfillPlaylistTitles>;

const result = (over: any = {}) => ({ playlistId: 'p-uuid', jobs: [], challengeRequired: false, counts: { enqueued: 3, joined: 0, skipped: 3, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 }, ...over });
beforeEach(() => { jest.clearAllMocks(); setSearchParams(''); sessionStorage.clear();
  listPlaylistsMock.mockReset().mockResolvedValue([]);
  backfillPlaylistTitlesMock.mockReset().mockResolvedValue({ updated: 1, attempted: 1 }); });

async function openAndSubmit() {
  fireEvent.click(await screen.findByRole('button', { name: /new playlist/i }));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'https://youtube.com/playlist?list=X' } });
  fireEvent.click(screen.getByRole('button', { name: /add/i }));
}

it('opens the modal from the sidebar and navigates on success', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();
  await waitFor(() => expect(push).toHaveBeenCalledWith('/?playlist=p-uuid'));
});

// backlog #37. The sidebar is a SIBLING of the content pane and is never keyed by playlistId, so
// `router.push('/?playlist=…')` reconciles it instead of remounting it. Its only fetch is keyed on
// [userId], which is stable for a signed-in session — so before this fix the list a user saw was
// whatever existed at sign-in, and every playlist they ingested was invisible until a hard reload.
// Measured against prod v6 on 2026-08-12: 3 playlists in the database, 1 in the sidebar, and a
// reload showed all 3.
//
// Asserts the RENDERED LINK, not a listPlaylists call count: a call-count assertion passes on a
// refetch whose result is thrown away, which is the same defect wearing a green tick.
it('shows a newly ingested playlist in the sidebar without a reload (backlog #37)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  listPlaylistsMock
    .mockResolvedValueOnce([])                    // at sign-in the owner has no playlists
    .mockResolvedValue([                          // …and one immediately after the ingest
      { id: 'p-uuid', playlistKey: 'X', playlistUrl: 'https://youtube.com/playlist?list=X', playlistTitle: 'Business', createdAt: '2026-08-13T00:40:51Z' },
    ]);
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByText(/no playlists yet/i)).toBeInTheDocument();
  await openAndSubmit();
  expect(await screen.findByRole('link', { name: 'Business' })).toBeInTheDocument();
});

// Review (Low) killed the first version of this test: it only re-rendered with a changed search
// param, so an implementation that ALSO polled on a timer would have passed it — no timers were
// ever advanced. Fake timers close that hole; the rerender case is kept as the second assertion.
it('does not refetch the sidebar on a timer within an hour, nor on plain navigation (backlog #37)', async () => {
  jest.useFakeTimers();
  try {
    createIngestMock.mockResolvedValue(result() as any);
    setSearchParams('playlist=p-uuid');
    const { rerender } = render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
    await waitFor(() => expect(listPlaylistsMock).toHaveBeenCalledTimes(1));

    await act(async () => { jest.advanceTimersByTime(60 * 60 * 1000); }); // an hour of nothing
    expect(listPlaylistsMock).toHaveBeenCalledTimes(1);

    setSearchParams('playlist=other');
    rerender(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />); // plain navigation, no ingest
    await act(async () => { jest.advanceTimersByTime(60 * 60 * 1000); });
    expect(listPlaylistsMock).toHaveBeenCalledTimes(1);
    // Honest limit (review r2, Low): this refutes an interval poll up to an hour and a
    // navigation-triggered refetch. It cannot refute a focus/visibilitychange listener — no such
    // event is dispatched here — so it is named for what it actually covers.
  } finally {
    jest.useRealTimers();
  }
});

// Review (High). The first version of this branch guarded each effect with its own `cancelled`
// boolean. Neither flag can see the other, so a SLOW mount fetch could resolve after a fast
// post-ingest refetch and overwrite the new playlist with the pre-ingest list — reinstating exactly
// the defect being fixed. Reachable because "+ New playlist" renders while the list is still
// loading. A shared monotonic sequence is what actually forbids it.
it('a slow initial load cannot overwrite the post-ingest list (backlog #37, review High)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  const fresh = [
    { id: 'p-uuid', playlistKey: 'X', playlistUrl: 'https://youtube.com/playlist?list=X', playlistTitle: 'Business', createdAt: '2026-08-13T00:40:51Z' },
  ];
  let resolveInitial!: (v: any) => void;
  listPlaylistsMock
    .mockReturnValueOnce(new Promise((r) => { resolveInitial = r; }) as any) // sign-in fetch: STALLS
    .mockResolvedValue(fresh as any);                                        // post-ingest refetch

  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();                                                     // ingest while it stalls
  expect(await screen.findByRole('link', { name: 'Business' })).toBeInTheDocument();

  await act(async () => { resolveInitial([]); });                            // stale load lands LAST
  expect(screen.getByRole('link', { name: 'Business' })).toBeInTheDocument();
  expect(screen.queryByText(/no playlists yet/i)).not.toBeInTheDocument();
});

// Review r2 (High, direction 1). A load that has been overtaken has no standing to put an error on
// screen. Round 1's guard covered only the success path, so a stale REJECTION still reached the
// mount effect's catch and hid a correctly rendered list behind an error banner.
it('a stale rejection cannot raise an error over a newer good list (backlog #37, review r2 High)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  let rejectInitial!: (e: any) => void;
  listPlaylistsMock
    .mockReturnValueOnce(new Promise((_r, rj) => { rejectInitial = rj; }) as any)
    .mockResolvedValue([
      { id: 'p-uuid', playlistKey: 'X', playlistUrl: 'https://youtube.com/playlist?list=X', playlistTitle: 'Business', createdAt: '2026-08-13T00:40:51Z' },
    ] as any);

  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();
  expect(await screen.findByRole('link', { name: 'Business' })).toBeInTheDocument();

  await act(async () => { rejectInitial(new Error('transient network blip')); });
  expect(screen.getByRole('link', { name: 'Business' })).toBeInTheDocument();
  expect(screen.queryByText(/transient network blip/i)).not.toBeInTheDocument();
  expect(replace).not.toHaveBeenCalledWith('/login');
});

// Review r2 (High, direction 2) — the mirror case, and the more dangerous one: discarding a
// LEGITIMATE result. When the newer load fails it applies nothing, so an older in-flight load that
// then succeeds is the best information available and must be allowed to render. Guarding against
// "newest STARTED" stranded the sidebar on "Loading playlists…" while holding a good list.
it('a newer failed load does not discard an older successful one (backlog #37, review r2 High)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  const existing = [
    { id: 'old', playlistKey: 'O', playlistUrl: 'https://youtube.com/playlist?list=O', playlistTitle: 'CS146S', createdAt: '2026-07-22T19:52:12Z' },
  ];
  let resolveInitial!: (v: any) => void;
  listPlaylistsMock
    .mockReturnValueOnce(new Promise((r) => { resolveInitial = r; }) as any) // sign-in load: stalls
    .mockRejectedValue(new Error('refetch failed') as any);                  // post-ingest: fails

  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();                                    // newer load starts, then rejects
  await waitFor(() => expect(listPlaylistsMock).toHaveBeenCalledTimes(2));

  await act(async () => { resolveInitial(existing); });     // older load succeeds afterwards
  expect(await screen.findByRole('link', { name: 'CS146S' })).toBeInTheDocument();
  expect(screen.queryByText(/loading playlists/i)).not.toBeInTheDocument();
});

// Review (Medium). producer.ts leaves the playlist row untitled when the YouTube title fetch misses
// or throws, on the stated expectation that the backfill route retries later. Before this branch the
// row was invisible so the gap never showed; now it renders, and the mount effect's backfill is
// once-per-session and already spent. The refresh path has to run its own repair.
it('repairs a newly ingested playlist that arrived with no title (backlog #37, review Medium)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  const base = { id: 'p-uuid', playlistKey: 'X', playlistUrl: 'https://youtube.com/playlist?list=X', createdAt: '2026-08-13T00:40:51Z' };
  listPlaylistsMock
    .mockResolvedValueOnce([] as any)                                    // sign-in: nothing yet
    .mockResolvedValueOnce([{ ...base, playlistTitle: null }] as any)    // post-ingest: untitled
    .mockResolvedValue([{ ...base, playlistTitle: 'Business' }] as any); // after backfill: named
  sessionStorage.setItem('backfilledTitles:u', '1'); // the sign-in sweep has already been spent

  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByText(/no playlists yet/i)).toBeInTheDocument();
  await openAndSubmit();

  expect(await screen.findByRole('link', { name: 'Business' })).toBeInTheDocument();
  expect(backfillPlaylistTitlesMock).toHaveBeenCalledTimes(1);
});

// The paired negative (review r2, Low): the test above on its own only shows a mock returned a
// title. Holding everything constant except a FAILING backfill must leave the row untitled — that
// is what pins the repair on the backfill call rather than on mock ordering.
it('leaves the row untitled when the repair backfill fails (backlog #37, review r2 Low)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  const base = { id: 'p-uuid', playlistKey: 'X', playlistUrl: 'https://youtube.com/playlist?list=X', createdAt: '2026-08-13T00:40:51Z' };
  listPlaylistsMock
    .mockResolvedValueOnce([] as any)
    .mockResolvedValue([{ ...base, playlistTitle: null }] as any);
  backfillPlaylistTitlesMock.mockRejectedValue(new Error('quota exhausted') as any);
  sessionStorage.setItem('backfilledTitles:u', '1');

  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByText(/no playlists yet/i)).toBeInTheDocument();
  await openAndSubmit();

  expect(await screen.findByRole('link', { name: 'Untitled playlist' })).toBeInTheDocument();
  expect(backfillPlaylistTitlesMock).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(/quota exhausted/i)).not.toBeInTheDocument();
});

it('shows the summary notice on the target playlist page (cross-playlist nav does not wipe it)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=other');          // currently viewing a DIFFERENT playlist
  const { rerender } = render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();
  await waitFor(() => expect(push).toHaveBeenCalledWith('/?playlist=p-uuid'));
  setSearchParams('playlist=p-uuid');          // navigation resolves
  rerender(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByText(/Queued 3 · 3 skipped/)).toBeInTheDocument();
});

it('Refresh re-POSTs the playlistUrl and does not navigate', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=p-uuid');
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  const refresh = await screen.findByRole('button', { name: /refresh/i });
  await waitFor(() => expect(refresh).toBeEnabled()); // enabled once listVideos loaded playlistUrl
  fireEvent.click(refresh);
  await waitFor(() => expect(createIngestMock).toHaveBeenCalledWith('https://youtube.com/playlist?list=X'));
  expect(push).not.toHaveBeenCalled();
});

it('drops a stale listVideos response so Refresh uses the current playlist url (R3 High)', async () => {
  // Playlist A's listVideos is slow; navigate to B; A resolves LATE with A's url.
  // The sequence guard must drop A so Refresh re-POSTs B, never A.
  const { listVideos } = jest.requireMock('@/lib/client/api');
  let resolveA!: (v: any) => void;
  (listVideos as jest.Mock)
    .mockReturnValueOnce(new Promise((r) => { resolveA = r; }))                                                // A (slow)
    .mockResolvedValue({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=B', playlistTitle: 'B' }); // B
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=A');
  const { rerender } = render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  setSearchParams('playlist=B');
  rerender(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />); // B mounts, bumps reqSeq
  resolveA({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=A', playlistTitle: 'A' }); // stale → dropped
  const refresh = await screen.findByRole('button', { name: /refresh/i });
  await waitFor(() => expect(refresh).toBeEnabled());
  fireEvent.click(refresh);
  await waitFor(() => expect(createIngestMock).toHaveBeenCalledWith('https://youtube.com/playlist?list=B'));
  expect(createIngestMock).not.toHaveBeenCalledWith('https://youtube.com/playlist?list=A');
});

it('does not let Refresh re-POST the previous playlist after cross-playlist navigation', async () => {
  const { listVideos } = jest.requireMock('@/lib/client/api');
  let resolveB!: (v: any) => void;
  (listVideos as jest.Mock)
    .mockResolvedValueOnce({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=A', playlistTitle: 'A' }) // A loads
    .mockReturnValueOnce(new Promise((r) => { resolveB = r; }));  // B stays pending
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=A');
  const { rerender } = render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  const refresh = await screen.findByRole('button', { name: /refresh/i });
  await waitFor(() => expect(refresh).toBeEnabled());          // A loaded → Refresh enabled with A's url
  setSearchParams('playlist=B');
  rerender(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />); // now viewing B; B's fetch pending; urlEntry still {A}
  await waitFor(() => expect(screen.getByRole('button', { name: /refresh/i })).toBeDisabled());
  fireEvent.click(screen.getByRole('button', { name: /refresh/i }));
  expect(createIngestMock).not.toHaveBeenCalledWith('https://youtube.com/playlist?list=A');
  resolveB({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=B', playlistTitle: 'B' });
});

it('Refresh is guarded against double-fire (two rapid clicks POST once)', async () => {
  let resolve!: (v: any) => void;
  createIngestMock.mockReturnValue(new Promise((r) => { resolve = r; }) as any);
  setSearchParams('playlist=p-uuid');
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  const refresh = await screen.findByRole('button', { name: /refresh/i });
  await waitFor(() => expect(refresh).toBeEnabled());
  fireEvent.click(refresh);
  fireEvent.click(refresh); // second click before the first createIngest resolves
  expect(createIngestMock).toHaveBeenCalledTimes(1);
  resolve(result());
  await waitFor(() => expect(createIngestMock).toHaveBeenCalledTimes(1));
});

// ---------------------------------------------------------------------------------------------
// Round 3 findings. Each of these covers a defect that round 2's OWN fix introduced.
// ---------------------------------------------------------------------------------------------

// Round 3 (High). `loadPlaylists` writes state internally, so a caller checking its own `cancelled`
// flag on the returned promise checks too late. On an in-place account switch (no remount) user A's
// in-flight load would render A's playlists under B's sidebar — a cross-account leak in the UI.
it('an in-flight load from the previous account cannot render under the new one (backlog #37, review r3 High)', async () => {
  const aPlaylists = [
    { id: 'a1', playlistKey: 'A', playlistUrl: 'https://youtube.com/playlist?list=A', playlistTitle: 'Alice private list', createdAt: '2026-07-01T00:00:00Z' },
  ];
  const bPlaylists = [
    { id: 'b1', playlistKey: 'B', playlistUrl: 'https://youtube.com/playlist?list=B', playlistTitle: 'Bob own list', createdAt: '2026-08-01T00:00:00Z' },
  ];
  // BOTH loads stall, and A resolves while B is still IN FLIGHT. That ordering is the whole point:
  // if A resolved after B had already applied, the sequence guard alone would catch it and this
  // test would pass with the cancellation check deleted — which is exactly what the mutation run
  // showed on the first version of this test. Only "A lands while nothing newer has applied yet"
  // reaches the cancellation branch.
  let resolveA!: (v: any) => void;
  let resolveB!: (v: any) => void;
  listPlaylistsMock
    .mockReturnValueOnce(new Promise((r) => { resolveA = r; }) as any) // account A: stalls
    .mockReturnValueOnce(new Promise((r) => { resolveB = r; }) as any); // account B: also stalls

  const { rerender } = render(<CloudApp session={{ userId: 'a', email: 'a@x.com' }} />);
  rerender(<CloudApp session={{ userId: 'b', email: 'b@x.com' }} />);  // A's effect tears down here
  await waitFor(() => expect(listPlaylistsMock).toHaveBeenCalledTimes(2));

  await act(async () => { resolveA(aPlaylists); });                   // A lands, nothing applied yet
  expect(screen.queryByRole('link', { name: 'Alice private list' })).not.toBeInTheDocument();

  await act(async () => { resolveB(bPlaylists); });
  expect(await screen.findByRole('link', { name: 'Bob own list' })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Alice private list' })).not.toBeInTheDocument();
});

// Round 3 (High). Round 2 made the older result render when the newer one failed — correct, but it
// did so SILENTLY, which is the "quietly serves stale data" mode this project treats as the worst
// kind. The user just created a playlist; a sidebar that omits it without explanation looks exactly
// like the bug being fixed. Both rounds are satisfied only because the banner and the list now
// coexist: show the best data available AND say the refresh failed.
it('a failed post-ingest refresh shows the stale list AND says so (backlog #37, review r3 High)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  listPlaylistsMock
    .mockResolvedValueOnce([
      { id: 'old', playlistKey: 'O', playlistUrl: 'https://youtube.com/playlist?list=O', playlistTitle: 'CS146S', createdAt: '2026-07-22T19:52:12Z' },
    ] as any)
    .mockRejectedValue(new Error('refetch failed') as any);

  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByRole('link', { name: 'CS146S' })).toBeInTheDocument();
  await openAndSubmit();

  expect(await screen.findByText(/could not refresh/i)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'CS146S' })).toBeInTheDocument(); // list NOT hidden by it
});

// Round 3 (Low). The stale-rejection test proves a suppressed error stays suppressed — but an
// implementation that suppressed EVERY list error would also pass it. This is its positive twin:
// a failure that is genuinely the newest load must still reach the user.
it('a genuine initial load failure is still reported (backlog #37, review r3 Low)', async () => {
  listPlaylistsMock.mockRejectedValue(new Error('server exploded') as any);
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByText(/server exploded/i)).toBeInTheDocument();
  expect(screen.queryByText(/loading playlists/i)).not.toBeInTheDocument();
});

// Round 3 (Medium). A banner left by an earlier failure must not sit above a list that later loaded
// fine — the render shows both now, so nothing else would ever remove it.
it('a later successful load clears an earlier error banner (backlog #37, review r3 Medium)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  listPlaylistsMock
    .mockRejectedValueOnce(new Error('server exploded') as any)   // sign-in load fails
    .mockResolvedValue([
      { id: 'p-uuid', playlistKey: 'X', playlistUrl: 'https://youtube.com/playlist?list=X', playlistTitle: 'Business', createdAt: '2026-08-13T00:40:51Z' },
    ] as any);

  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByText(/server exploded/i)).toBeInTheDocument();
  await openAndSubmit();

  expect(await screen.findByRole('link', { name: 'Business' })).toBeInTheDocument();
  expect(screen.queryByText(/server exploded/i)).not.toBeInTheDocument();
});

// Round 4 (High). The banner belongs to the request that failed, not to wall-clock arrival order.
// An unconditional setError(null) on success let a slow PRE-ingest load, landing after the
// post-ingest refetch had already failed, erase an accurate warning — leaving the user looking at a
// list that genuinely lacks the playlist they just made, with nothing on screen to say so.
it('an older load landing later cannot erase a newer refresh-failure banner (backlog #37, review r4 High)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  const preIngest = [
    { id: 'old', playlistKey: 'O', playlistUrl: 'https://youtube.com/playlist?list=O', playlistTitle: 'CS146S', createdAt: '2026-07-22T19:52:12Z' },
  ];
  let resolveInitial!: (v: any) => void;
  listPlaylistsMock
    .mockReturnValueOnce(new Promise((r) => { resolveInitial = r; }) as any) // sign-in load: stalls
    .mockRejectedValue(new Error('refetch failed') as any);                  // post-ingest: fails

  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();
  await waitFor(() => expect(screen.getByText(/could not refresh/i)).toBeInTheDocument());

  await act(async () => { resolveInitial(preIngest); });   // the OLD load lands after the failure
  expect(screen.getByRole('link', { name: 'CS146S' })).toBeInTheDocument();
  expect(screen.getByText(/could not refresh/i)).toBeInTheDocument(); // warning must SURVIVE
});

// Round 4 (High), the class-level half. The refresh effect's cleanup is scoped to [refreshKey], so
// it does NOT fire when userId changes — round 3 had fixed exactly this defect for the mount effect
// and it survived, untouched, one effect over. The guard is therefore on the REQUEST (compare the
// userId it was issued for against the one now mounted), which covers every caller at once.
//
// Unreachable in the app as it stands — sign-out unmounts CloudApp via router.replace('/login') and
// there is no router.refresh() anywhere — but a guard without a test is a claim, and the scenario is
// one account-switcher away. Constructed here directly.
it('an in-flight REFRESH from the previous account cannot render under the new one (backlog #37, review r4 High)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  const aPlaylists = [
    { id: 'a1', playlistKey: 'A', playlistUrl: 'https://youtube.com/playlist?list=A', playlistTitle: 'Alice private list', createdAt: '2026-07-01T00:00:00Z' },
  ];
  const bPlaylists = [
    { id: 'b1', playlistKey: 'B', playlistUrl: 'https://youtube.com/playlist?list=B', playlistTitle: 'Bob own list', createdAt: '2026-08-01T00:00:00Z' },
  ];
  let resolveARefresh!: (v: any) => void;
  let resolveBMount!: (v: any) => void;
  listPlaylistsMock
    .mockResolvedValueOnce([] as any)                                          // A signs in
    .mockReturnValueOnce(new Promise((r) => { resolveARefresh = r; }) as any)  // A's post-ingest refresh: stalls
    .mockReturnValueOnce(new Promise((r) => { resolveBMount = r; }) as any);   // B's mount load: stalls

  const { rerender } = render(<CloudApp session={{ userId: 'a', email: 'a@x.com' }} />);
  expect(await screen.findByText(/no playlists yet/i)).toBeInTheDocument();
  await openAndSubmit();                                                       // starts A's refresh
  await waitFor(() => expect(listPlaylistsMock).toHaveBeenCalledTimes(2));

  rerender(<CloudApp session={{ userId: 'b', email: 'b@x.com' }} />);           // refresh effect does NOT tear down
  await waitFor(() => expect(listPlaylistsMock).toHaveBeenCalledTimes(3));

  await act(async () => { resolveARefresh(aPlaylists); });                      // A's data arrives under B
  expect(screen.queryByRole('link', { name: 'Alice private list' })).not.toBeInTheDocument();

  await act(async () => { resolveBMount(bPlaylists); });
  expect(await screen.findByRole('link', { name: 'Bob own list' })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Alice private list' })).not.toBeInTheDocument();
});
