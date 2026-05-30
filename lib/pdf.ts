import mdToPdf from 'md-to-pdf';
import { promises as fs } from 'fs';

// Monospace font ensures ASCII art diagrams in deep-dive summaries render faithfully.
// CJK fallback fonts listed first for systems that have them (e.g. Noto CJK on Linux).
const CSS = `
  body { font-family: 'Noto Sans CJK KR', 'Malgun Gothic', sans-serif; line-height: 1.6; }
  pre, code { font-family: 'Courier New', Courier, monospace; white-space: pre; }
`;

// md-to-pdf starts an internal HTTP server (default port 56666) that Puppeteer
// connects to. Two collisions can break this:
// 1. Concurrent calls within the same worker (e.g. two backfill requests)
// 2. Calls across different Next.js workers / hot-reload cycles
//
// Defence layer 1: serialise calls within one worker via a promise chain.
// Defence layer 2: use a fresh random port per call so workers never share a port.
let pdfQueue: Promise<void> = Promise.resolve();

/**
 * Generate a PDF from Markdown content and write it to outputPath.
 * The parent directory of outputPath must already exist.
 * Path validation (outputFolder bounds, videoId format) is the caller's responsibility.
 *
 * Buffer mode is used (no `dest`) so the Puppeteer browser is closed before
 * the file write — preventing a Chromium process leak if the write fails.
 */
export function generatePdf(mdContent: string, outputPath: string): Promise<void> {
  const result = pdfQueue.then(() => _generatePdfUnlocked(mdContent, outputPath));
  pdfQueue = result.catch(() => {});
  return result;
}

async function _generatePdfUnlocked(mdContent: string, outputPath: string): Promise<void> {
  // Random port in 57000–59999 so concurrent workers never collide on 56666.
  const port = 57000 + Math.floor(Math.random() * 3000);
  let buffer: Buffer;
  try {
    const result = await mdToPdf({ content: mdContent }, { css: CSS, port });
    if (!result.content) throw new Error('md-to-pdf returned empty content');
    buffer = result.content;
  } catch (err) {
    const cause = err instanceof Error ? err.message : String(err);
    throw new Error(`PDF generation failed for ${outputPath}: ${cause}`, { cause: err });
  }

  try {
    await fs.writeFile(outputPath, buffer);
  } catch (err) {
    const cause = err instanceof Error ? err.message : String(err);
    throw new Error(`PDF generation failed for ${outputPath}: ${cause}`, { cause: err });
  }
}
