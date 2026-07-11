import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { assertVideoId } from '../../../../../lib/index-store';
import { getPrincipal, getStorageBundle, getPrincipalFromSession } from '../../../../../lib/storage/resolve';
import { createServerSupabase, type CookieStore } from '../../../../../lib/supabase/server';
import { resolveOwnedPlaylistKey } from '../../../../../lib/storage/serve-playlist';
import type { Video } from '../../../../../types';

type Params = { params: Promise<{ id: string }> };

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Shared body validation (local + cloud): exactly the same bounds as before Task 7.
 *  Returns an error message on failure, or null when the body is acceptable. */
function validateBody(body: Record<string, unknown> | null): { hasScore: boolean; hasNote: boolean; error: string | null } {
  const hasScore = body !== null && 'personalScore' in body;
  const hasNote  = body !== null && 'personalNote'  in body;

  if (!hasScore && !hasNote) {
    return { hasScore, hasNote, error: 'at least one field required' };
  }

  // Validate personalScore: must be 1–5 integer, or null (to clear)
  if (hasScore) {
    const score = body!.personalScore;
    if (
      score !== null &&
      (typeof score !== 'number' || !Number.isInteger(score) || score < 1 || score > 5)
    ) {
      return { hasScore, hasNote, error: 'personalScore must be 1–5 or null' };
    }
  }

  // Validate personalNote: must be string ≤ 500 chars (empty string = clear)
  if (hasNote) {
    const note = body!.personalNote;
    if (typeof note !== 'string') {
      return { hasScore, hasNote, error: 'personalNote must be a string' };
    }
    if (note.length > 500) {
      return { hasScore, hasNote, error: 'personalNote must be 500 characters or fewer' };
    }
  }

  return { hasScore, hasNote, error: null };
}

export async function POST(request: Request, { params }: Params) {
  const { id: videoId } = await params;
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') return serveCloud(request, videoId);
  return serveLocal(request, videoId);
}

// ---- LOCAL path — preserved verbatim (pre-2a Task 7 behavior, filesystem-backed) ----
async function serveLocal(request: Request, videoId: string): Promise<Response> {
  const body = await request.json().catch(() => null) as Record<string, unknown> | null;
  const outputFolder = body?.outputFolder;

  if (!outputFolder || typeof outputFolder !== 'string') {
    return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  }

  const { hasScore, hasNote, error } = validateBody(body);
  if (error) return NextResponse.json({ error }, { status: 400 });

  let principal;
  try {
    principal = getPrincipal(outputFolder);
    assertVideoId(videoId);
  } catch {
    return NextResponse.json({ error: 'invalid request' }, { status: 400 });
  }

  // Map null → undefined (score deletion) and "" → undefined (note deletion)
  const patch: Partial<Pick<Video, 'personalScore' | 'personalNote'>> = {};
  if (hasScore) {
    patch.personalScore = (body!.personalScore === null) ? undefined : (body!.personalScore as number);
  }
  if (hasNote) {
    patch.personalNote = (body!.personalNote === '') ? undefined : (body!.personalNote as string);
  }

  try {
    await getStorageBundle().metadataStore.updateVideoFields(principal, videoId, patch);
  } catch (err) {
    const e = err as Error;
    if (e.message.startsWith('Video not found in index')) {
      return NextResponse.json({ error: 'video not found' }, { status: 404 });
    }
    return NextResponse.json({ error: 'internal error' }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}

// ---- CLOUD path (Stage 2a Task 7) — session-scoped Supabase, owner-asserted via
// resolveOwnedPlaylistKey + RLS + the update_video_annotations RPC's own auth.uid()
// guard (belt-and-suspenders). Mirrors the Task 5/6 cloud flow: createServerSupabase →
// getUser → UUID guard → reject outputFolder → (same field validation as serveLocal) →
// resolveOwnedPlaylistKey → getPrincipalFromSession → getStorageBundle({supabaseClient}).
// Writes go through updateVideoAnnotations (update_video_annotations RPC), NOT
// updateVideoFields/merge_video_data — the allowlist + owner guard are enforced in SQL.
async function serveCloud(request: Request, videoId: string): Promise<Response> {
  const { searchParams } = new URL(request.url);

  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) {
    return NextResponse.json({ error: 'invalid playlist' }, { status: 400 }); // before any DB call
  }

  const body = await request.json().catch(() => null) as Record<string, unknown> | null;

  if (body && 'outputFolder' in body) {
    return NextResponse.json({ error: 'outputFolder not valid on this backend' }, { status: 400 });
  }

  const { hasScore, hasNote, error } = validateBody(body);
  if (error) return NextResponse.json({ error }, { status: 400 });

  const playlistKey = await resolveOwnedPlaylistKey(supabase, playlistId, user.id); // owner-asserted (D6/D9)
  if (!playlistKey) return NextResponse.json({ error: 'not found' }, { status: 404 });

  const principal = getPrincipalFromSession({ userId: user.id }, playlistKey);
  const bundle = getStorageBundle({ supabaseClient: supabase }); // session-scoped, RLS-enforced

  // Map null → clear (score) and "" → clear (note); other values → set.
  const set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived'>> = {};
  const clear: ('personalScore' | 'personalNote')[] = [];
  if (hasScore) {
    if (body!.personalScore === null) clear.push('personalScore');
    else set.personalScore = body!.personalScore as number;
  }
  if (hasNote) {
    if (body!.personalNote === '') clear.push('personalNote');
    else set.personalNote = body!.personalNote as string;
  }

  const { found } = await bundle.metadataStore.updateVideoAnnotations(principal, videoId, set, clear);
  if (!found) return NextResponse.json({ error: 'video not found' }, { status: 404 });

  return NextResponse.json({ ok: true });
}
