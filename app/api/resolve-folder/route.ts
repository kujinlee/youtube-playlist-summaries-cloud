import { NextResponse } from 'next/server';
import { readSettings } from '../../../lib/settings-store';
import { resolveOutputFolder, InvalidPlaylistUrlError } from '../../../lib/output-folder';

// Resolve the output folder for a playlist URL, anchored at the configured root
// (baseOutputFolder). Existing playlists resolve to their on-disk folder by id;
// new playlists resolve to <root>/<slug(title)>/raw.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const url = searchParams.get('url');
  if (!url) {
    return NextResponse.json({ error: 'url is required' }, { status: 400 });
  }

  const settings = readSettings();
  // `??` is correct because readSettings returns baseOutputFolder as undefined
  // (not '') when unset (lib/settings-store.ts).
  const root = settings.baseOutputFolder ?? settings.outputFolder;
  if (!root) {
    return NextResponse.json({ error: 'no base output folder configured' }, { status: 400 });
  }

  try {
    const outputFolder = await resolveOutputFolder(url, root, process.env.YOUTUBE_API_KEY);
    return NextResponse.json({ outputFolder });
  } catch (err) {
    // Only a malformed playlist URL is the caller's fault (400); anything else
    // (filesystem, unexpected) is internal — 500 with a generic message, no leak.
    if (err instanceof InvalidPlaylistUrlError) {
      return NextResponse.json({ error: err.message }, { status: 400 });
    }
    return NextResponse.json({ error: 'failed to resolve folder' }, { status: 500 });
  }
}
