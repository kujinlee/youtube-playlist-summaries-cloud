import { NextResponse } from 'next/server';
import { readSettings, writeSettings } from '../../../lib/settings-store';
import { assertOutputFolder } from '../../../lib/index-store';

export async function GET(_request: Request) {
  const settings = readSettings();
  return NextResponse.json(settings);
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const outputFolder = body?.outputFolder;

  if (!outputFolder || typeof outputFolder !== 'string') {
    return NextResponse.json({ error: 'outputFolder is required' }, { status: 400 });
  }

  try {
    assertOutputFolder(outputFolder);
  } catch {
    return NextResponse.json({ error: 'invalid outputFolder' }, { status: 400 });
  }

  writeSettings({ outputFolder });
  return NextResponse.json({ ok: true });
}
