import { NextResponse } from 'next/server';
import { normalizeToRoot } from '../../../lib/output-folder';

// Reduce a folder path to the data ROOT. The header calls this when the user
// Browses to or types a folder, so a pick of `<root>/<slug>` or `<root>/<slug>/raw`
// (a sign of confusion) snaps back up to the root before any playlist URL exists.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const path = searchParams.get('path');
  if (!path || !path.trim()) {
    return NextResponse.json({ error: 'path is required' }, { status: 400 });
  }

  try {
    return NextResponse.json({ root: normalizeToRoot(path) });
  } catch {
    // Filesystem / unexpected error — generic 500, no path leak.
    return NextResponse.json({ error: 'failed to normalize folder' }, { status: 500 });
  }
}
