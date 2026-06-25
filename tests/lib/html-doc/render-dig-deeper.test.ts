import fs from 'fs';
import os from 'os';
import path from 'path';
import { renderDigDeeperHtml, renderDigDeeperDoc } from '@/lib/html-doc/render-dig-deeper';
import type { ParsedSummary } from '@/lib/html-doc/types';
import type { ModelEnvelope } from '@/lib/html-doc/model-store';
import type { DugSection } from '@/lib/dig/companion-doc';

// Minimal valid JPEG bytes (SOI + EOI markers only — enough for Buffer.isBuffer / readFileSync)
const MINIMAL_JPEG = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xff, 0xd9]);

function makeTempDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'render-dig-deeper-'));
}

describe('renderDigDeeperHtml', () => {
  // -------------------------------------------------------------------------
  // Behavior 1: Image inlined as base64 when file exists
  // -------------------------------------------------------------------------
  describe('Behavior 1 — image inlined as base64', () => {
    let tmpDir: string;
    let assetsDir: string;
    let mdPath: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      assetsDir = path.join(tmpDir, 'assets', 'v');
      fs.mkdirSync(assetsDir, { recursive: true });
      const jpegPath = path.join(assetsDir, '300-352.jpg');
      fs.writeFileSync(jpegPath, MINIMAL_JPEG);
      mdPath = path.join(tmpDir, 'test.md');
      const mdContent = `# Slide deck\n\n![A caption](assets/v/300-352.jpg)\n\nSome prose after.\n`;
      html = renderDigDeeperHtml(mdContent, mdPath);
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('contains a data:image/jpeg;base64, src', () => {
      expect(html).toContain('src="data:image/jpeg;base64,');
    });

    it('preserves the alt caption', () => {
      expect(html).toContain('alt="A caption"');
    });

    it('does NOT contain a relative assets/ src', () => {
      expect(html).not.toMatch(/src="assets\//);
    });

    it('does not contain a broken file:// or relative path src', () => {
      expect(html).not.toMatch(/src="(?!data:)[^"]*assets/);
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 2: Missing asset → img omitted entirely, no relative src, no throw
  // -------------------------------------------------------------------------
  describe('Behavior 2 — missing asset dropped, no relative src, no throw', () => {
    let tmpDir: string;
    let mdPath: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      mdPath = path.join(tmpDir, 'test.md');
      // Reference a file that does NOT exist
      const mdContent = `# Missing slide\n\n![No file](assets/v/missing-999.jpg)\n\nProse continues.\n`;
      html = renderDigDeeperHtml(mdContent, mdPath);
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('does NOT throw when the asset file is missing', () => {
      expect(() => renderDigDeeperHtml(
        `# x\n\n![x](assets/v/no-exist.jpg)\n`,
        path.join(tmpDir, 'x.md'),
      )).not.toThrow();
    });

    it('does NOT emit a relative src="assets/..." for the missing image', () => {
      expect(html).not.toMatch(/src="assets\//);
    });

    it('does NOT emit any <img> for the missing asset (drop, not alt placeholder)', () => {
      expect(html).not.toContain('<img');
    });

    it('emits the surrounding prose (img drop does not swallow the whole doc)', () => {
      expect(html).toContain('Prose continues.');
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 3: HTML escaped (markdown-it html:false)
  // -------------------------------------------------------------------------
  describe('Behavior 3 — HTML escaped (html:false)', () => {
    const mdContent = `# XSS test\n\n<script>alert('xss')</script>\n\n![cap <script>](assets/safe.jpg)\n`;
    let tmpDir: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      html = renderDigDeeperHtml(mdContent, path.join(tmpDir, 'test.md'));
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('escapes raw <script> tags in the body (html:false)', () => {
      expect(html).not.toContain('<script>alert(');
      expect(html).toContain('&lt;script&gt;');
    });

    it('escapes < in the image alt attribute', () => {
      // The alt should be HTML-escaped — no raw < in alt
      expect(html).not.toMatch(/alt="cap <script>/);
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 4: data-t anchors preserved
  // -------------------------------------------------------------------------
  describe('Behavior 4 — data-t anchors preserved', () => {
    const mdContent = `# Slides\n\nProse with a <a class="dig" data-type="summary" data-t="90">↑ summary</a> control.\n`;
    // Note: html:false means raw HTML is escaped, but markdown handles links normally.
    // We test via a markdown link that outputs data attributes.
    const mdWithLink = `# Slides\n\n[section](https://youtube.com/watch?v=abc&t=90s)\n`;
    let tmpDir: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      html = renderDigDeeperHtml(mdWithLink, path.join(tmpDir, 'test.md'));
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('renders a YouTube link with t= param in the href', () => {
      expect(html).toContain('t=90s');
    });

    it('includes the NAV_SCRIPT (a.dig handling)', () => {
      expect(html).toContain('a.dig');
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 5: Self-contained output
  // -------------------------------------------------------------------------
  describe('Behavior 5 — self-contained output', () => {
    const mdContent = `# Self-contained test\n\nSome body text.\n`;
    let tmpDir: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      html = renderDigDeeperHtml(mdContent, path.join(tmpDir, 'test.md'));
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('is a valid HTML document starting with <!DOCTYPE html>', () => {
      expect(html).toMatch(/^<!DOCTYPE html>/);
    });

    it('has no external <link> stylesheet references', () => {
      expect(html).not.toContain('<link');
    });

    it('inlines CSS inside a <style> block', () => {
      expect(html).toContain('<style>');
    });

    it('inlines the magazine light palette (cream card, gold, ghost vars)', () => {
      expect(html).toContain('--card:#fbf9f6');
      expect(html).toContain('--gold:#b07700');
      expect(html).toContain('--ghost:#f0e7d6');
    });

    it('includes the dark palette + system-dark media query', () => {
      expect(html).toContain('[data-theme="dark"]');
      expect(html).toContain('@media(prefers-color-scheme:dark)');
    });

    it('includes the theme toggle button and scripts', () => {
      expect(html).toContain('id="theme-toggle"');
      expect(html).toContain("localStorage.getItem('html-doc-theme')");
    });

    it('includes the Print button', () => {
      expect(html).toContain('id="print-btn"');
      expect(html).toContain('onclick="window.print()"');
    });

    it('includes the NAV_CSS (.dig rule)', () => {
      expect(html).toContain('.dig{');
    });

    it('includes the NAV_SCRIPT (wireDigLinks + scrollToHashSection)', () => {
      expect(html).toContain('a.dig');
    });

    it('renders the body content', () => {
      expect(html).toContain('Self-contained test');
      expect(html).toContain('Some body text.');
    });

    it('uses the generator meta tag', () => {
      expect(html).toContain('<meta name="generator" content="dig-deeper-html v1">');
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 5b: path traversal in image src → img dropped, no file disclosed
  // -------------------------------------------------------------------------
  describe('Behavior 5b — path traversal dropped, no arbitrary file disclosure', () => {
    let tmpDir: string;
    let secretPath: string;
    let mdPath: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      // Place a "secret" file two levels above tmpDir (in os.tmpdir()).
      // assets/../../<basename> passes startsWith('assets/') but resolves
      // OUTSIDE docDir/assets/ → should be blocked by the containment check.
      secretPath = path.join(os.tmpdir(), `secret-traversal-${path.basename(tmpDir)}.txt`);
      fs.writeFileSync(secretPath, 'supersecret');
      mdPath = path.join(tmpDir, 'test.md');
      // assets/../../<file> resolves to os.tmpdir()/<file> — outside docDir
      const traversalSrc = `assets/../../${path.basename(secretPath)}`;
      const mdContent = `# Traversal test\n\n![x](${traversalSrc})\n\nProse.\n`;
      html = renderDigDeeperHtml(mdContent, mdPath);
    });

    afterAll(() => {
      try { fs.rmSync(secretPath); } catch { /* ignore */ }
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('does NOT emit any <img> for a traversal path', () => {
      expect(html).not.toContain('<img');
    });

    it('does NOT embed the secret file contents as base64', () => {
      const secretB64 = Buffer.from('supersecret').toString('base64');
      expect(html).not.toContain(secretB64);
    });

    it('does not throw', () => {
      expect(html).toContain('Prose.');
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 5c: markdown timestamp links render to clickable href anchors
  // -------------------------------------------------------------------------
  describe('Behavior 5c — markdown timestamp links render as href anchors', () => {
    // Dig-deeper bodies use markdown timestamp LINKS like
    //   ▶ [11:00–21:19](https://www.youtube.com/watch?v=abc&t=660s)
    // (output of resolveTranscriptTokens), NOT raw inline <a data-t> HTML.
    // html:false would escape raw HTML anchors, but markdown links are rendered
    // normally by markdown-it → href anchors with the t= param preserved.
    let tmpDir: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      const mdContent = `# Timestamps\n\n▶ [11:00–21:19](https://www.youtube.com/watch?v=abc&t=660s)\n`;
      html = renderDigDeeperHtml(mdContent, path.join(tmpDir, 'test.md'));
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('renders a markdown timestamp link as a clickable <a> with t= in href', () => {
      expect(html).toContain('href="https://www.youtube.com/watch?v=abc&amp;t=660s"');
    });

    it('preserves the link text including timestamp range', () => {
      expect(html).toContain('11:00');
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 7 (H-1): sentinel-delimited companion doc → section data-start attrs
  // -------------------------------------------------------------------------
  describe('Behavior 7 — sentinel blocks render as <section data-start="N">', () => {
    let tmpDir: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      const mdContent = [
        '---',
        'title: "Test Video"',
        'videoId: "abc12345678"',
        '---',
        '# Test Video',
        '',
        '<!-- dig-section: 312 -->',
        '## Introduction',
        '',
        'Body text for section 312.',
        '<!-- /dig-section -->',
        '',
        '<!-- dig-section: 600 -->',
        '## Advanced Topics',
        '',
        'Body text for section 600.',
        '<!-- /dig-section -->',
      ].join('\n');
      html = renderDigDeeperHtml(mdContent, path.join(tmpDir, 'test-dig-deeper.md'));
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('contains <section data-start="312"', () => {
      expect(html).toContain('<section data-start="312"');
    });

    it('contains <section data-start="600"', () => {
      expect(html).toContain('<section data-start="600"');
    });

    it('renders the section body text inside the section element', () => {
      expect(html).toContain('Body text for section 312');
      expect(html).toContain('Body text for section 600');
    });

    it('pre-sentinel content (title) renders normally outside sections', () => {
      expect(html).toContain('Test Video');
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 8 (Issue #1): style parity — muted ▶ ts links and lead accent
  // -------------------------------------------------------------------------
  describe('Behavior 8 — style parity: muted ▶ ts link + lead accent per sentinel section', () => {
    let tmpDir: string;
    let assetsDir: string;
    let mdPath: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      assetsDir = path.join(tmpDir, 'assets', 'v');
      fs.mkdirSync(assetsDir, { recursive: true });
      fs.writeFileSync(path.join(assetsDir, 'slide.jpg'), MINIMAL_JPEG);
      mdPath = path.join(tmpDir, 'test-style.md');
      const mdContent = [
        '---',
        'title: "Style Parity Test"',
        '---',
        '# Style Parity Test',
        '',
        '<!-- dig-section: 312 -->',
        '## Introduction',
        '',
        '▶ [05:12–10:30](https://www.youtube.com/watch?v=abc&t=312s)',
        '',
        'This is the first sentence of the lead. And more prose follows here.',
        '',
        '- Bullet one',
        '- Bullet two',
        '',
        '![slide](assets/v/slide.jpg)',
        '<!-- /dig-section -->',
        '',
        '<!-- dig-section: 630 -->',
        '## Second Section',
        '',
        '▶ [10:30–15:00](https://www.youtube.com/watch?v=abc&t=630s)',
        '',
        'Second section lead sentence. More text here.',
        '<!-- /dig-section -->',
      ].join('\n');
      html = renderDigDeeperHtml(mdContent, mdPath);
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('section data-start uses sentinel sectionId (312), not ▶ url time', () => {
      expect(html).toContain('<section data-start="312"');
      expect(html).toContain('<section data-start="630"');
    });

    it('renders ▶ link with class="ts" and target="_blank"', () => {
      expect(html).toContain('class="ts"');
      expect(html).toContain('target="_blank"');
    });

    it('renders ▶ link with rel="noopener noreferrer"', () => {
      expect(html).toContain('rel="noopener noreferrer"');
    });

    it('renders lead paragraph with class="lead" for first prose paragraph', () => {
      expect(html).toContain('class="lead"');
    });

    it('renders lead-accent span around the first sentence', () => {
      expect(html).toContain('class="lead-accent"');
    });

    it('inlines slide image as base64 (image inlining preserved under style-parity path)', () => {
      expect(html).toContain('src="data:image/jpeg;base64,');
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 9 (Issue #2): ↑ summary back-link per sentinel section
  // -------------------------------------------------------------------------
  describe('Behavior 9 — ↑ summary back-link per sentinel section', () => {
    let tmpDir: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      const mdContent = [
        '# Nav Test',
        '',
        '<!-- dig-section: 312 -->',
        '## Introduction',
        '',
        'Body text for section 312.',
        '<!-- /dig-section -->',
        '',
        '<!-- dig-section: 600 -->',
        '## Advanced Topics',
        '',
        'Body text for section 600.',
        '<!-- /dig-section -->',
      ].join('\n');
      html = renderDigDeeperHtml(mdContent, path.join(tmpDir, 'test-nav.md'));
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('contains a ↑ summary control with data-type="summary" for section 312', () => {
      expect(html).toContain('data-type="summary"');
      expect(html).toContain('data-t="312"');
      expect(html).toContain('↑ summary');
    });

    it('contains a ↑ summary control with data-t="600" for second section', () => {
      expect(html).toContain('data-t="600"');
    });

    it('back-link anchors have class="dig"', () => {
      // digControl('summary', N) returns <a class="dig" data-type="summary" data-t="N">
      expect(html).toContain('class="dig"');
    });
  });

  // -------------------------------------------------------------------------
  // Behavior 6: multiple images — present one inlined, missing one dropped
  // -------------------------------------------------------------------------
  describe('mixed present + missing assets in one doc', () => {
    let tmpDir: string;
    let assetsDir: string;
    let mdPath: string;
    let html: string;

    beforeAll(() => {
      tmpDir = makeTempDir();
      assetsDir = path.join(tmpDir, 'assets', 'v');
      fs.mkdirSync(assetsDir, { recursive: true });
      fs.writeFileSync(path.join(assetsDir, 'present.jpg'), MINIMAL_JPEG);
      mdPath = path.join(tmpDir, 'test.md');
      const mdContent = [
        '# Mixed',
        '',
        '![present](assets/v/present.jpg)',
        '',
        '![missing](assets/v/absent.jpg)',
        '',
        'End.',
      ].join('\n');
      html = renderDigDeeperHtml(mdContent, mdPath);
    });

    afterAll(() => {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    });

    it('inlines the present image as base64', () => {
      expect(html).toContain('src="data:image/jpeg;base64,');
    });

    it('does NOT emit any relative assets/ src', () => {
      expect(html).not.toMatch(/src="assets\//);
    });

    it('does NOT emit a second <img> for the missing asset', () => {
      // Only one <img> should appear (the inlined one)
      const count = (html.match(/<img/g) ?? []).length;
      expect(count).toBe(1);
    });

    it('still renders surrounding prose', () => {
      expect(html).toContain('End.');
    });
  });
});

// ──────────────────────────────────────────────────────────────────────────────
// renderDigDeeperDoc — merge renderer (Task 6)
// ──────────────────────────────────────────────────────────────────────────────

function makeSummary(overrides: Partial<ParsedSummary> = {}): ParsedSummary {
  return {
    title: 'Test Video',
    channel: null,
    duration: null,
    url: 'https://www.youtube.com/watch?v=vid123',
    lang: 'EN',
    videoId: 'vid123',
    tldr: null,
    takeaways: [],
    sourceMd: 'test.md',
    sections: [
      {
        numeral: '1',
        title: 'Introduction',
        prose: 'Intro prose',
        timeRange: { startSec: 60, endSec: 300, label: '1:00–5:00', url: 'https://www.youtube.com/watch?v=vid123&t=60s' },
      },
      {
        numeral: '2',
        title: 'Main Content',
        prose: 'Main prose',
        timeRange: { startSec: 300, endSec: 600, label: '5:00–10:00', url: 'https://www.youtube.com/watch?v=vid123&t=300s' },
      },
    ],
    ...overrides,
  };
}

function makeEnvelope(overrides: Partial<ModelEnvelope> = {}): ModelEnvelope {
  return {
    sourceMd: 'test.md',
    generatedAt: '2026-01-01T00:00:00.000Z',
    sourceSections: ['Introduction', 'Main Content'],
    model: {
      sections: [
        {
          lead: 'This is the intro lead sentence.',
          bullets: [
            { label: 'Point A', text: 'First bullet text' },
            { label: 'Point B', text: 'Second bullet text' },
            { label: 'Point C', text: 'Third bullet text' },
          ],
        },
        {
          lead: 'This is the main lead sentence.',
          bullets: [
            { label: 'Point X', text: 'Main bullet one' },
            { label: 'Point Y', text: 'Main bullet two' },
            { label: 'Point Z', text: 'Main bullet three' },
          ],
        },
      ],
    },
    ...overrides,
  };
}

function makeDugSection(overrides: Partial<DugSection> = {}): DugSection {
  return {
    sectionId: 60,
    startSec: 60,
    title: 'Introduction',
    bodyMarkdown: '## Introduction\n\nDug content for intro section.',
    generatedAt: '2026-01-01T00:00:00.000Z',
    ...overrides,
  };
}

describe('renderDigDeeperDoc', () => {
  let tmpDir: string;
  let mdPath: string;

  beforeAll(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'render-dig-deeper-doc-'));
    mdPath = path.join(tmpDir, 'test-dig-deeper.md');
  });

  afterAll(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 1: All sections rendered in order
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 1 — all sections rendered in order', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary();
      const envelope = makeEnvelope();
      html = renderDigDeeperDoc({ summary, envelope, dug: [], mdPath, videoId: 'vid123' });
    });

    it('renders a section element for each summary section', () => {
      const matches = html.match(/<section/g);
      expect(matches?.length).toBeGreaterThanOrEqual(2);
    });

    it('renders Introduction before Main Content', () => {
      const introIdx = html.indexOf('Introduction');
      const mainIdx = html.indexOf('Main Content');
      expect(introIdx).toBeGreaterThanOrEqual(0);
      expect(mainIdx).toBeGreaterThan(introIdx);
    });

    it('each section has data-dug attribute', () => {
      expect(html).toContain('data-dug="false"');
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 2: Un-dug section has .gist + dig-trigger
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 2 — un-dug section: .gist block + dig-trigger', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary();
      const envelope = makeEnvelope();
      html = renderDigDeeperDoc({ summary, envelope, dug: [], mdPath, videoId: 'vid123' });
    });

    it('renders .gist div for sections with gist data', () => {
      expect(html).toContain('class="gist"');
    });

    it('renders the lead sentence in .gist', () => {
      expect(html).toContain('This is the intro lead sentence.');
    });

    it('renders bullets inside .gist', () => {
      expect(html).toContain('First bullet text');
    });

    it('renders a dig-trigger anchor for un-dug sections', () => {
      expect(html).toContain('class="dig-trigger"');
    });

    it('dig-trigger has data-section attribute with the startSec', () => {
      expect(html).toContain('data-section="60"');
    });

    it('dig-trigger text contains "dig deeper ▶"', () => {
      expect(html).toContain('dig deeper ▶');
    });

    it('un-dug section has data-dug="false"', () => {
      expect(html).toContain('data-dug="false"');
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 3: Dug section has .gist (hidden) + .dug (shown) + dig-toggle
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 3 — dug section: .gist + .dug + dig-toggle', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary();
      const envelope = makeEnvelope();
      const dug = [makeDugSection({ sectionId: 60, startSec: 60 })];
      html = renderDigDeeperDoc({ summary, envelope, dug, mdPath, videoId: 'vid123' });
    });

    it('dug section has data-dug="true"', () => {
      expect(html).toContain('data-dug="true"');
    });

    it('dug section still has .gist block (hidden by CSS)', () => {
      expect(html).toContain('class="gist"');
    });

    it('dug section has .dug block with rendered bodyMarkdown', () => {
      expect(html).toContain('class="dug"');
    });

    it('.dug block contains the dug body content', () => {
      expect(html).toContain('Dug content for intro section.');
    });

    it('renders dig-toggle anchor for dug sections', () => {
      expect(html).toContain('class="dig-toggle"');
    });

    it('dig-toggle text contains "show summary ⌃"', () => {
      expect(html).toContain('show summary ⌃');
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 4: timeRange null → no data-start, no dig-trigger, .gist shown
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 4 — timeRange null: no data-start, no dig-trigger, .gist shown', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary({
        sections: [
          {
            numeral: null,
            title: 'Conclusion',
            prose: 'Conclusion prose',
            timeRange: null,
          },
        ],
      });
      const envelope: ModelEnvelope = {
        sourceMd: 'test.md',
        generatedAt: '2026-01-01T00:00:00.000Z',
        sourceSections: ['Conclusion'],
        model: {
          sections: [
            {
              lead: 'Conclusion lead.',
              bullets: [
                { label: 'A', text: 'Bullet A' },
                { label: 'B', text: 'Bullet B' },
                { label: 'C', text: 'Bullet C' },
              ],
            },
          ],
        },
      };
      html = renderDigDeeperDoc({ summary, envelope, dug: [], mdPath, videoId: 'vid123' });
    });

    it('does NOT emit data-start attribute on the section element', () => {
      // The section element must not have data-start; NAV_SCRIPT may contain the string
      // in its querySelector calls, so we check the section tag itself.
      expect(html).not.toMatch(/<section[^>]*data-start/);
    });

    it('does NOT emit a dig-trigger for a no-timestamp section', () => {
      expect(html).not.toContain('class="dig-trigger"');
    });

    it('renders .gist block even without a timestamp', () => {
      expect(html).toContain('class="gist"');
      expect(html).toContain('Conclusion lead.');
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 5: Skeleton section (gist null) — no .gist, but dig-trigger if startSec
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 5 — skeleton: no .gist, dig-trigger present when startSec exists', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary({
        sections: [
          {
            numeral: '1',
            title: 'Section One',
            prose: 'Some prose',
            timeRange: { startSec: 120, endSec: 240, label: '2:00–4:00', url: 'https://www.youtube.com/watch?v=vid123&t=120s' },
          },
        ],
      });
      // envelope null → skeleton (gist null for all sections)
      html = renderDigDeeperDoc({ summary, envelope: null, dug: [], mdPath, videoId: 'vid123' });
    });

    it('does NOT render a .gist block for a skeleton section', () => {
      expect(html).not.toContain('class="gist"');
    });

    it('still renders dig-trigger when startSec is present', () => {
      expect(html).toContain('class="dig-trigger"');
      expect(html).toContain('data-section="120"');
    });

    it('section has data-dug="false" (un-dug)', () => {
      expect(html).toContain('data-dug="false"');
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 6: Orphan region rendered when orphans exist
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 6 — orphan region rendered', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary({
        sections: [
          {
            numeral: '1',
            title: 'Only Section',
            prose: 'Prose',
            timeRange: { startSec: 60, endSec: 120, label: '1:00–2:00', url: 'https://www.youtube.com/watch?v=vid123&t=60s' },
          },
        ],
      });
      // orphan: sectionId 999 does not match any summary section
      const orphanDug: DugSection = {
        sectionId: 999,
        startSec: 999,
        title: 'Orphaned Section',
        bodyMarkdown: 'Orphan body content here.',
        generatedAt: '2026-01-01T00:00:00.000Z',
      };
      html = renderDigDeeperDoc({ summary, envelope: null, dug: [orphanDug], mdPath, videoId: 'vid123' });
    });

    it('renders a .dg-orphans section', () => {
      expect(html).toContain('class="dg-orphans"');
    });

    it('renders orphan title in the orphan region', () => {
      expect(html).toContain('Orphaned Section');
    });

    it('renders orphan body content', () => {
      expect(html).toContain('Orphan body content here.');
    });

    it('renders orphan comment sentinel', () => {
      expect(html).toContain('<!-- orphan: 999 -->');
    });

    it('renders re-dig notice paragraph', () => {
      expect(html).toContain('class="dg-orphan-note"');
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 6b: No orphan region when orphans is empty
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 6b — no orphan region when no orphans', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary();
      html = renderDigDeeperDoc({ summary, envelope: null, dug: [], mdPath, videoId: 'vid123' });
    });

    it('does NOT render .dg-orphans when there are no orphans', () => {
      expect(html).not.toContain('class="dg-orphans"');
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 7: Top bar rendered once
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 7 — top bar rendered once', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary();
      html = renderDigDeeperDoc({ summary, envelope: null, dug: [], mdPath, videoId: 'vid123' });
    });

    it('renders exactly one .dg-topbar div', () => {
      const matches = html.match(/class="dg-topbar"/g);
      expect(matches?.length).toBe(1);
    });

    it('topbar contains ↑ summary anchor', () => {
      expect(html).toContain('↑ summary');
    });

    it('topbar ↑ summary anchor has class="dig" and data-type="summary"', () => {
      expect(html).toContain('data-type="summary"');
    });

    it('topbar contains expand-all button', () => {
      expect(html).toContain('class="dg-expand-all"');
      expect(html).toContain('⤢ expand all');
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // Behavior 8: Spacing CSS present
  // ──────────────────────────────────────────────────────────────────────────
  describe('Behavior 8 — spacing and toggle CSS present', () => {
    let html: string;

    beforeAll(() => {
      const summary = makeSummary();
      html = renderDigDeeperDoc({ summary, envelope: null, dug: [], mdPath, videoId: 'vid123' });
    });

    it('includes section padding CSS', () => {
      expect(html).toContain('padding:2.4em 0');
    });

    it('includes 2px top border rule between sections', () => {
      expect(html).toMatch(/border-top:2px/);
    });

    it('includes 1.2em margin around .dug img', () => {
      expect(html).toContain('.dug img');
      expect(html).toMatch(/1\.2em/);
    });

    it('includes default hide-gist CSS for dug sections', () => {
      expect(html).toContain('section[data-dug="true"] .gist{display:none}');
    });

    it('includes .show-gist toggle CSS', () => {
      expect(html).toContain('.show-gist .gist{display:block}');
      expect(html).toContain('.show-gist .dug{display:none}');
    });
  });
});
