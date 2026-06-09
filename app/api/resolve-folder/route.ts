import { NextResponse } from 'next/server';
import { readSettings } from '../../../lib/settings-store';
import { resolveOutputFolder, normalizeToRoot, InvalidPlaylistUrlError } from '../../../lib/output-folder';

// Resolve the output folder for a playlist URL, anchored at a data root.
// The anchor is the optional `root` query param (the header's root field) or, when
// absent, the configured root from settings. Either way it is normalized to root
// first — so a stale `<root>/<slug>/raw` value never compounds into
// `<root>/<slug>/raw/<slug>/raw`. The normalized root is returned alongside the
// resolved target so the client's root field can self-correct in one round-trip.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const url = searchParams.get('url');
  if (!url) {
    return NextResponse.json({ error: 'url is required' }, { status: 400 });
  }

  const settings = readSettings();
  // Distinguish an ABSENT root param (fall back to settings) from a BLANK one
  // (`?root=` / whitespace → a client error, not a silent settings fallback).
  // `??` is correct because readSettings returns baseOutputFolder as undefined
  // (not '') when unset (lib/settings-store.ts).
  const rootParam = searchParams.get('root');
  const rawRoot = (rootParam === null ? (settings.baseOutputFolder ?? settings.outputFolder) : rootParam) ?? '';
  const trimmedRoot = rawRoot.trim();
  if (!trimmedRoot) {
    return NextResponse.json({ error: 'no base output folder configured' }, { status: 400 });
  }

  try {
    const root = normalizeToRoot(trimmedRoot);
    const outputFolder = await resolveOutputFolder(url, root, process.env.YOUTUBE_API_KEY);
    return NextResponse.json({ root, outputFolder });
  } catch (err) {
    // Only a malformed playlist URL is the caller's fault (400); anything else
    // (filesystem, unexpected) is internal — 500 with a generic message, no leak.
    if (err instanceof InvalidPlaylistUrlError) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }
    return NextResponse.json({ error: 'failed to resolve folder' }, { status: 500 });
  }
}
