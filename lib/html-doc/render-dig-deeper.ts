import fs from 'fs';
import path from 'path';
import MarkdownIt from 'markdown-it';
import type { RenderRuleRecord } from 'markdown-it/lib/renderer.mjs';
import {
  themeStyleBlock, THEME_HEAD_SCRIPT, THEME_TOGGLE_BUTTON, THEME_TOGGLE_SCRIPT, PRINT_BUTTON,
  BASE_PALETTE_LIGHT_PRE, BASE_PALETTE_LIGHT_POST, BASE_PALETTE_DARK_PRE, BASE_PALETTE_DARK_POST,
  type Palette,
} from './theme';
import { digControl, NAV_SCRIPT, NAV_CSS } from './nav';
import {
  extractTimestamp,
  takeFirstParagraph,
  splitFirstSentence,
  tsAnchor,
} from './render-deep-dive';
import type { ParsedSummary } from './types';
import type { ModelEnvelope } from './model-store';
import type { DugSection } from '../dig/companion-doc';
import { mergeDigDoc } from './dig-merge';

const LIGHT: Palette = {
  ...BASE_PALETTE_LIGHT_PRE, ...BASE_PALETTE_LIGHT_POST, link: '#b07700', h3: '#5b463a', h4: '#6b5a4a',
  codebg: '#f1ebe0', preborder: '#e6ddcf', quote: '#8a8276', meta: '#8a8276',
};
const DARK: Palette = {
  ...BASE_PALETTE_DARK_PRE, ...BASE_PALETTE_DARK_POST, link: '#e6b54d', h3: '#d8cdb8', h4: '#c4b7a0',
  codebg: '#2a241c', preborder: '#332c24', quote: '#9a9082', meta: '#9a9082',
};

const STRUCTURAL_CSS = `
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);line-height:1.7;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",'Apple SD Gothic Neo','Malgun Gothic',Helvetica,Arial,sans-serif}
.dg{max-width:52rem;margin:0 auto;background:var(--card);padding:2.8rem 3rem 4rem;box-shadow:var(--shadow)}
html.theme-ready .dg{transition:background-color .2s,color .2s}
.dg h1{font-family:Georgia,'Nanum Myeongjo','Apple SD Gothic Neo','Times New Roman',serif;font-size:2rem;line-height:1.2;margin:0 0 .15em;color:var(--ink)}
.dg h2{font-family:Georgia,'Nanum Myeongjo',serif;font-size:1.5rem;margin:2.2em 0 .35em;padding-top:1.5em;border-top:1px solid var(--rule);color:var(--ink)}
.dg h2:first-of-type{border-top:0;padding-top:0;margin-top:.4em}
.dg .lead{font-size:1.02rem;line-height:1.55;color:var(--ink);font-weight:400;margin:.3em 0 .9em;max-width:92%}
.dg .lead-accent{color:var(--gold);font-weight:400}
.dg .ts{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--meta);font-size:.85rem;font-weight:400;text-decoration:none;white-space:nowrap}
.dg .ts:hover{text-decoration:underline}
.dg h3{font-size:1.15rem;margin:1.6em 0 .3em;color:var(--h3)}
.dg h4{font-size:1.02rem;margin:1.2em 0 .3em;color:var(--h4)}
.dg p{margin:.75em 0;color:var(--ink)}
.dg a{color:var(--link)}
.dg ul,.dg ol{padding-left:1.4em;margin:.5em 0}
.dg li{margin:.4em 0;color:var(--li);line-height:1.65}
.dg strong{color:var(--ink);font-weight:700}
.dg blockquote{border-left:3px solid var(--goldline);margin:1.1em 0;padding:.2em 1.1em;color:var(--quote);font-style:italic}
.dg code{font-family:'SF Mono',Menlo,Monaco,Consolas,monospace;font-size:.88em;background:var(--codebg);padding:.1em .35em;border-radius:4px}
.dg pre{background:var(--codebg);border:1px solid var(--preborder);border-radius:8px;padding:1em 1.2em;overflow:auto;line-height:1.4}
.dg pre code{background:none;padding:0;font-size:.85em;white-space:pre}
.dg img{max-width:100%;height:auto;border-radius:6px;margin:.75em 0;display:block}
.dg footer{margin-top:2.6em;padding-top:1.2em;border-top:1px solid var(--rule);color:var(--foot);font-size:.8rem}
@media print{body{background:#fff}.dg{box-shadow:none}#theme-toggle{display:none}}
`;

function esc(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Build a markdown-it instance with the image rule overridden to inline `assets/…` files as
 * base64 data URIs. The instance is created fresh per render call so the `mdPath` closure is
 * correct for each document.
 *
 * Decision (M-5): override the `image` renderer rule (not post-hoc HTML regex) so the inlining
 * happens at the token level. If the asset file is missing, drop the `<img>` entirely (return '')
 * so no broken relative src ever ships in the output.
 *
 * Note: dig-deeper bodies use markdown timestamp LINKS like
 *   ▶ [11:00–21:19](https://www.youtube.com/watch?v=abc&t=660s)
 * (output of resolveTranscriptTokens), NOT raw inline <a data-t> HTML anchors.
 * markdown-it renders these markdown links to <a href="...t=660s..."> anchors normally,
 * so html:false (which escapes raw HTML) does not affect timestamp link rendering.
 */
function buildRenderer(mdPath: string): MarkdownIt {
  const renderer = new MarkdownIt({ html: false });
  const docDir = path.dirname(mdPath);
  // assetsRoot is the only directory from which images may be inlined.
  const assetsRoot = path.resolve(docDir, 'assets');

  const rules = renderer.renderer.rules as RenderRuleRecord;
  rules.image = (tokens, idx) => {
    const token = tokens[idx];
    const srcAttr = token.attrGet('src') ?? '';
    const altAttr = token.children
      ? token.children.map((t) => t.content).join('')
      : (token.attrGet('alt') ?? '');

    // Only inline relative `assets/` paths; leave absolute URLs untouched.
    if (srcAttr.startsWith('assets/')) {
      const absPath = path.resolve(docDir, srcAttr);
      // Containment check: resolved path must stay inside assetsRoot.
      // Blocks traversal like assets/../../etc/passwd (passes startsWith but
      // resolves outside the doc's assets directory → arbitrary file disclosure).
      if (!absPath.startsWith(assetsRoot + path.sep)) return '';
      let data: Buffer | null = null;
      try {
        data = fs.readFileSync(absPath);
      } catch {
        // File missing — drop the <img> entirely (no broken relative src)
        return '';
      }
      const b64 = data.toString('base64');
      return `<img src="data:image/jpeg;base64,${b64}" alt="${esc(altAttr)}">`;
    }

    // Non-assets src: let markdown-it render normally but escape the src.
    return `<img src="${esc(srcAttr)}" alt="${esc(altAttr)}">`;
  };

  return renderer;
}

/**
 * Render a dig-deeper `.md` into a self-contained HTML page with slide screenshots inlined as
 * base64. Mirrors `renderDeepDiveHtml`'s CSS/theme/NAV pattern.
 *
 * @param mdContent  Raw markdown string (may include YAML frontmatter — stripped).
 * @param mdPath     Absolute path to the source `.md` file (used to resolve `assets/` images).
 */
export function renderDigDeeperHtml(mdContent: string, mdPath: string): string {
  const renderer = buildRenderer(mdPath);

  // Strip the leading YAML frontmatter block and normalize line endings.
  const body = mdContent
    .replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, '')
    .replace(/\r\n/g, '\n');

  const title = body.match(/^#\s+(.+)$/m)?.[1]?.trim() ?? 'Dig Deeper';

  // Parse sentinel-delimited blocks from the body.
  // If the body contains sentinel blocks, render each as <section data-start="N">.
  // Pre-sentinel content (e.g. the H1 title) renders normally.
  const sentinelRe = /<!-- dig-section: (\d+) -->\n([\s\S]*?)<!-- \/dig-section -->/g;
  const parts: string[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = sentinelRe.exec(body)) !== null) {
    // Render content before this sentinel block
    if (match.index > lastIndex) {
      parts.push(renderer.render(body.slice(lastIndex, match.index)));
    }
    // Render the sentinel block with deep-dive style treatment:
    // - Extract ## heading line
    // - Extract optional leading ▶ timestamp line → muted trailing link on <h2>
    // - Extract first prose paragraph → lead accent (gold first sentence)
    // - ↑ summary back-link (digControl) on the heading
    // - data-start uses the sentinel sectionId (H-1: NOT the ▶ url time)
    const sectionId = match[1];
    const blockContent = match[2];

    const blockLines = blockContent.split('\n');
    // Extract the ## heading (first non-blank line starting with ##)
    const h2Idx = blockLines.findIndex((l) => /^##\s+/.test(l));
    let heading = '';
    let bodyLines: string[];
    if (h2Idx !== -1) {
      heading = blockLines[h2Idx].replace(/^##\s+/, '').trim();
      bodyLines = blockLines.slice(h2Idx + 1);
    } else {
      bodyLines = blockLines;
    }

    // Extract optional leading ▶ timestamp line (mutates bodyLines)
    const ts = extractTimestamp(bodyLines);
    const tsHtml = tsAnchor(ts);

    // Build ↑ summary back-link (Issue #2)
    const backLink = digControl('summary', Number(sectionId));

    // Render <h2> with muted ts link + back-link
    const headingHtml = heading
      ? `<h2>${renderer.renderInline(heading)}${tsHtml}${backLink}</h2>`
      : '';

    // Extract lead paragraph and render with gold first-sentence accent (Issue #1)
    const { para, rest } = takeFirstParagraph(bodyLines);
    let leadHtml = '';
    if (para) {
      const { first, rest: tail } = splitFirstSentence(para);
      const firstHtml = renderer.renderInline(first);
      const tailHtml = tail ? ` ${renderer.renderInline(tail)}` : '';
      leadHtml = `<p class="lead"><span class="lead-accent">${firstHtml}</span>${tailHtml}</p>`;
    }

    // Render the rest via the image-aware renderer (preserves base64 inlining)
    const restHtml = rest.trim() ? renderer.render(rest) : '';

    const sectionInner = [headingHtml, leadHtml, restHtml].filter(Boolean).join('\n');
    parts.push(`<section data-start="${sectionId}">\n${sectionInner}\n</section>\n`);
    lastIndex = match.index + match[0].length;
  }

  // Render any remaining content after the last sentinel block (or the whole body if no sentinels)
  if (lastIndex < body.length) {
    parts.push(renderer.render(body.slice(lastIndex)));
  }

  const bodyHtml = parts.join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="dig-deeper-html v1">
<meta name="source-md" content="${esc(path.basename(mdPath))}">
<title>${esc(title)}</title>
${THEME_HEAD_SCRIPT}
<style>${themeStyleBlock(LIGHT, DARK)}${STRUCTURAL_CSS}${NAV_CSS}</style>
</head>
<body>
${THEME_TOGGLE_BUTTON}${PRINT_BUTTON}
<article class="dg">
${bodyHtml}</article>
${NAV_SCRIPT}${THEME_TOGGLE_SCRIPT}
</body>
</html>`;
}

// ── Dig-deeper merge renderer CSS additions (Task 6) ─────────────────────────
const DIG_DOC_CSS = `
section{padding:2.4em 0;border-top:2px solid var(--rule)}
section:first-of-type{border-top:0}
.dug img{margin:1.2em 0}
section[data-dug="true"] .gist{display:none}
.show-gist .gist{display:block}
.show-gist .dug{display:none}
.dg-topbar{display:flex;align-items:center;gap:1em;margin-bottom:1.6em;font-size:.85rem}
.dg-expand-all{background:none;border:1px solid var(--rule);border-radius:4px;padding:.2em .6em;cursor:pointer;font-size:.85rem;color:var(--meta)}
.dg-orphans{margin-top:3em;padding-top:1.5em;border-top:2px dashed var(--rule)}
.dg-orphan-note{font-size:.82rem;color:var(--meta);font-style:italic}
`;

/**
 * Render a dig-deeper doc using the structured merge result (Task 6).
 *
 * Takes structured summary + model data (rather than a raw .md string) and
 * emits a full HTML page where each MergedSection is rendered with its gist
 * and/or dug-content in the correct state.
 *
 * This function is ADDITIVE — the old renderDigDeeperHtml is left intact.
 */
export function renderDigDeeperDoc(args: {
  summary: ParsedSummary;
  envelope: ModelEnvelope | null;
  dug: DugSection[];
  mdPath: string;
  videoId: string;
}): string {
  const { summary, envelope, dug, mdPath } = args;
  const renderer = buildRenderer(mdPath);

  const { sections, orphans } = mergeDigDoc(summary, envelope, dug);

  const title = summary.title;

  // Determine the first section that has a startSec for the top-bar back-link.
  const firstStartSec = sections.find((s) => s.startSec !== null)?.startSec ?? null;

  // ── Top bar ──────────────────────────────────────────────────────────────
  const summaryLink = firstStartSec !== null
    ? digControl('summary', firstStartSec)
    : `<a class="dig" data-type="summary">↑ summary</a>`;
  const topBar = `<div class="dg-topbar">${summaryLink} <button class="dg-expand-all">⤢ expand all</button></div>`;

  // ── Sections ──────────────────────────────────────────────────────────────
  const sectionsHtml = sections.map((ms) => {
    const { startSec, title: sectionTitle, gist, dug: dugData } = ms;
    const isDug = dugData !== null;

    // section open tag — omit data-start when startSec is null
    const startAttr = startSec !== null ? ` data-start="${startSec}"` : '';
    const dugAttr = ` data-dug="${isDug}"`;
    const sectionOpen = `<section${startAttr}${dugAttr}>`;

    // heading with muted ts link (when startSec known) + control
    const tsLink = startSec !== null
      ? ` <a class="ts" href="https://www.youtube.com/watch?v=${esc(summary.videoId ?? '')}&amp;t=${startSec}s" target="_blank" rel="noopener noreferrer">${esc(ms.numeral ? `${ms.numeral}. ${sectionTitle}` : sectionTitle)} ▶</a>`
      : '';
    // control: un-dug (with startSec) → dig-trigger; dug → dig-toggle; no startSec → neither
    let control = '';
    if (isDug) {
      control = ` <a class="dig-toggle">show summary ⌃</a>`;
    } else if (startSec !== null) {
      control = ` <a class="dig-trigger" data-section="${startSec}">dig deeper ▶</a>`;
    }

    const heading = `<h2>${esc(sectionTitle)}${tsLink}${control}</h2>`;

    // .gist block — only when gist != null (skeleton → omit)
    let gistHtml = '';
    if (gist !== null) {
      const leadHtml = `<p class="lead">${esc(gist.lead)}</p>`;
      const bulletsHtml = gist.bullets.map((b) => `<li>${esc(b.text)}</li>`).join('');
      gistHtml = `<div class="gist">${leadHtml}<ul>${bulletsHtml}</ul></div>`;
    }

    // .dug block — only when dug matched
    let dugHtml = '';
    if (dugData !== null) {
      const rendered = renderer.render(dugData.bodyMarkdown);
      dugHtml = `<div class="dug">${rendered}</div>`;
    }

    return `${sectionOpen}\n${heading}${gistHtml}${dugHtml}\n</section>`;
  }).join('\n');

  // ── Orphan region ─────────────────────────────────────────────────────────
  let orphansHtml = '';
  if (orphans.length > 0) {
    const orphanItems = orphans.map((o) => {
      const rendered = renderer.render(o.bodyMarkdown);
      return [
        `<h3>${esc(o.title)}</h3>`,
        rendered,
        `<p class="dg-orphan-note">This section was dug but could not be matched to a current summary section. Re-dig to regenerate.</p>`,
        `<!-- orphan: ${o.sectionId} -->`,
      ].join('\n');
    }).join('\n');
    orphansHtml = `\n<section class="dg-orphans"><h2>Unmapped dug sections</h2>\n${orphanItems}\n</section>`;
  }

  const bodyHtml = `${topBar}\n${sectionsHtml}${orphansHtml}`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="dig-deeper-doc v1">
<meta name="source-md" content="${esc(path.basename(mdPath))}">
<title>${esc(title)}</title>
${THEME_HEAD_SCRIPT}
<style>${themeStyleBlock(LIGHT, DARK)}${STRUCTURAL_CSS}${NAV_CSS}${DIG_DOC_CSS}</style>
</head>
<body>
${THEME_TOGGLE_BUTTON}${PRINT_BUTTON}
<article class="dg">
${bodyHtml}
</article>
${NAV_SCRIPT}${THEME_TOGGLE_SCRIPT}
</body>
</html>`;
}
