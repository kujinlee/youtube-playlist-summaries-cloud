import fs from 'fs';
import os from 'os';
import path from 'path';
import { GET } from '../../app/api/html/[id]/route';
import { GENERATOR_VERSION } from '../../lib/html-doc/render';

// Mock reRenderSummaryHtml so tests control return values without hitting disk/Gemini.
jest.mock('../../lib/html-doc/rerender', () => ({
  ...jest.requireActual('../../lib/html-doc/rerender'),
  reRenderSummaryHtml: jest.fn(),
}));

import { reRenderSummaryHtml } from '../../lib/html-doc/rerender';
const mockReRender = reRenderSummaryHtml as jest.MockedFunction<typeof reRenderSummaryHtml>;

let dir: string;
const VIDEO_ID = 'vid12345';

function video(extra: Record<string, unknown> = {}) {
  return {
    id: VIDEO_ID, title: 'T', youtubeUrl: 'https://youtu.be/x', language: 'en',
    durationSeconds: 60, archived: false,
    ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
    overallScore: 4, summaryMd: 'a.md', summaryPdf: null, deepDiveMd: null, deepDivePdf: null,
    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z', ...extra,
  };
}
function writeIndex(v: unknown) {
  fs.writeFileSync(path.join(dir, 'playlist-index.json'),
    JSON.stringify({ playlistUrl: 'https://x.test/p', outputFolder: dir, videos: [v] }));
}
function url(extra = '') {
  return new Request(`http://localhost/api/html/${VIDEO_ID}?outputFolder=${encodeURIComponent(dir)}&type=summary${extra}`);
}
const ctx = { params: Promise.resolve({ id: VIDEO_ID }) };

// Must be under homedir — assertOutputFolder (not mocked) enforces this on macOS
beforeEach(() => { dir = fs.mkdtempSync(path.join(os.homedir(), '.tmp-htmlserve-')); });
afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

it('400s without outputFolder', async () => {
  const res = await GET(new Request(`http://localhost/api/html/${VIDEO_ID}`), ctx);
  expect(res.status).toBe(400);
});

it('400s when type is missing or unsupported', async () => {
  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
  const base = `http://localhost/api/html/${VIDEO_ID}?outputFolder=${encodeURIComponent(dir)}`;
  expect((await GET(new Request(base), ctx)).status).toBe(400);                 // missing type
  expect((await GET(new Request(`${base}&type=bogus`), ctx)).status).toBe(400); // unsupported type
});

it('404s on a path-traversal summaryHtml value (Codex BLOCKING)', async () => {
  writeIndex(video({ summaryHtml: '../../../../etc/passwd' }));
  const res = await GET(url(), ctx);
  expect([400, 404]).toContain(res.status); // never 200
  expect(res.status).not.toBe(200);
});

it('404s when summaryHtml is unset', async () => {
  writeIndex(video({ summaryHtml: null }));
  const res = await GET(url(), ctx);
  expect(res.status).toBe(404);
});

it('404s when the file is missing on disk', async () => {
  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
  const res = await GET(url(), ctx);
  expect(res.status).toBe(404);
});

it('serves the cached HTML with text/html', async () => {
  fs.mkdirSync(path.join(dir, 'htmls'));
  // Include current generator version so the version check serves cached without calling rerender.
  fs.writeFileSync(path.join(dir, 'htmls', 'a.html'),
    `<!DOCTYPE html><head><meta name="generator" content="${GENERATOR_VERSION}"></head><title>ok</title>`);
  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
  const res = await GET(url(), ctx);
  expect(res.status).toBe(200);
  expect(res.headers.get('Content-Type')).toMatch(/text\/html/);
  expect(await res.text()).toContain('<title>ok</title>');
});

it('serves a summary HTML whose filename has a Korean slug (B-1)', async () => {
  const koFile = 'htmls/모든-곳에-구글이-있었다.html';
  fs.mkdirSync(path.join(dir, 'htmls'), { recursive: true });
  // Include current generator version so the version check serves cached without calling rerender.
  fs.writeFileSync(path.join(dir, koFile),
    `<!DOCTYPE html><head><meta name="generator" content="${GENERATOR_VERSION}"></head><title>ko</title>`);
  writeIndex(video({ summaryHtml: koFile }));
  const res = await GET(new Request(
    `http://localhost/api/html/${VIDEO_ID}?outputFolder=${encodeURIComponent(dir)}&type=summary`), ctx);
  expect(res.status).toBe(200); // was 404 before the Unicode-regex fix
});

// --- type=dig-deeper (Behaviors 1–3) ---

function digDeeperUrl() {
  return new Request(
    `http://localhost/api/html/${VIDEO_ID}?outputFolder=${encodeURIComponent(dir)}&type=dig-deeper`
  );
}

it('dig-deeper: 404 when digDeeperMd is absent (B-3)', async () => {
  writeIndex(video({ digDeeperMd: null }));
  const res = await GET(digDeeperUrl(), ctx);
  expect(res.status).toBe(404);
});

it('dig-deeper: 404 when digDeeperMd file is missing on disk (B-3)', async () => {
  writeIndex(video({ digDeeperMd: 'wiki/missing-dig-deeper.md' }));
  const res = await GET(digDeeperUrl(), ctx);
  expect(res.status).toBe(404);
});

it('dig-deeper: 200 HTML rendered from digDeeperMd (B-1)', async () => {
  fs.mkdirSync(path.join(dir, 'wiki'), { recursive: true });
  fs.writeFileSync(
    path.join(dir, 'wiki', 'dig-deeper.md'),
    '# Dig Deeper\n\nSome deeper content here.\n'
  );
  writeIndex(video({ digDeeperMd: 'wiki/dig-deeper.md' }));
  const res = await GET(digDeeperUrl(), ctx);
  expect(res.status).toBe(200);
  expect(res.headers.get('Content-Type')).toMatch(/text\/html/);
  const body = await res.text();
  expect(body).toContain('<!DOCTYPE html');
  expect(body).toContain('Dig Deeper');
});

it('unknown type still 400 (B-2)', async () => {
  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
  const base = `http://localhost/api/html/${VIDEO_ID}?outputFolder=${encodeURIComponent(dir)}`;
  const res = await GET(new Request(`${base}&type=banana`), ctx);
  expect(res.status).toBe(400);
});

// --- version-gated summary re-render (Task 5 behaviors) ---

function makeHtmlWithGenerator(generatorContent: string) {
  return `<!DOCTYPE html><html><head><meta name="generator" content="${generatorContent}"></head><body></body></html>`;
}

describe('version-gated summary re-render', () => {
  beforeEach(() => {
    mockReRender.mockReset();
    fs.mkdirSync(path.join(dir, 'htmls'), { recursive: true });
  });

  it('B1: current generator version → serves cached, does NOT call reRenderSummaryHtml', async () => {
    const cached = makeHtmlWithGenerator(GENERATOR_VERSION);
    fs.writeFileSync(path.join(dir, 'htmls', 'a.html'), cached);
    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));

    const res = await GET(url(), ctx);
    expect(res.status).toBe(200);
    expect(await res.text()).toContain('meta name="generator"');
    expect(mockReRender).not.toHaveBeenCalled();
  });

  it('B2: stale + rerendered → serves result.html from reRenderSummaryHtml', async () => {
    const staleCached = makeHtmlWithGenerator('magazine-skim v1');
    fs.writeFileSync(path.join(dir, 'htmls', 'a.html'), staleCached);
    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));

    const freshHtml = `<!DOCTYPE html><html><head><meta name="generator" content="${GENERATOR_VERSION}"></head><body>fresh</body></html>`;
    mockReRender.mockReturnValue({ status: 'rerendered', htmlPath: 'htmls/a.html', html: freshHtml });

    const res = await GET(url(), ctx);
    expect(res.status).toBe(200);
    expect(await res.text()).toContain('fresh');
    expect(mockReRender).toHaveBeenCalledWith(VIDEO_ID, dir);
  });

  it('B3: stale + skipped-drift → serves stale cached, 200, console.warn called', async () => {
    const staleCached = makeHtmlWithGenerator('magazine-skim v1');
    fs.writeFileSync(path.join(dir, 'htmls', 'a.html'), staleCached);
    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));

    mockReRender.mockReturnValue({ status: 'skipped-drift', mdSections: ['A'], modelSections: ['B'] });
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

    const res = await GET(url(), ctx);
    expect(res.status).toBe(200);
    expect(await res.text()).toContain('magazine-skim v1');
    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it('B4: stale + skipped-no-model → serves stale cached, 200', async () => {
    const staleCached = makeHtmlWithGenerator('magazine-skim v1');
    fs.writeFileSync(path.join(dir, 'htmls', 'a.html'), staleCached);
    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));

    mockReRender.mockReturnValue({ status: 'skipped-no-model' });

    const res = await GET(url(), ctx);
    expect(res.status).toBe(200);
    expect(await res.text()).toContain('magazine-skim v1');
  });

  it('B5: missing file → 404 regardless of version logic', async () => {
    writeIndex(video({ summaryHtml: 'htmls/missing.html', summaryMd: 'wiki/a.md' }));
    // no file on disk
    const res = await GET(url(), ctx);
    expect(res.status).toBe(404);
    // rerender should not be called since file read throws
    expect(mockReRender).not.toHaveBeenCalled();
  });

  it('B6: null summaryHtml → 404', async () => {
    writeIndex(video({ summaryHtml: null }));
    const res = await GET(url(), ctx);
    expect(res.status).toBe(404);
    expect(mockReRender).not.toHaveBeenCalled();
  });
});
