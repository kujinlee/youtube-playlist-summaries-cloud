import { NextResponse } from 'next/server';
import { fetchPlaylistTitle } from '../../../lib/youtube';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const urlParam = searchParams.get('url');

  if (!urlParam) {
    return NextResponse.json({ error: 'url is required' }, { status: 400 });
  }

  let playlistId: string | null;
  try {
    playlistId = new URL(urlParam).searchParams.get('list');
  } catch {
    return NextResponse.json({ error: 'invalid url' }, { status: 400 });
  }

  if (!playlistId) {
    return NextResponse.json({ error: 'url has no ?list= param' }, { status: 400 });
  }

  const apiKey = process.env.YOUTUBE_API_KEY;
  if (apiKey) {
    try {
      const title = await fetchPlaylistTitle(playlistId, apiKey);
      return NextResponse.json({ playlistId, title });
    } catch {
      // API call failed — fall through to ID-as-title fallback
    }
  }

  return NextResponse.json({ playlistId, title: playlistId });
}
