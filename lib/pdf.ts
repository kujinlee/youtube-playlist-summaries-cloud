import mdToPdf from 'md-to-pdf';
import { promises as fs } from 'fs';

// Monospace font ensures ASCII art diagrams in deep-dive summaries render faithfully.
// CJK fallback fonts listed first for systems that have them (e.g. Noto CJK on Linux).
const CSS = `
  body { font-family: 'Noto Sans CJK KR', 'Malgun Gothic', sans-serif; line-height: 1.6; }
  pre, code { font-family: 'Courier New', Courier, monospace; white-space: pre; }
`;

// md-to-pdf opens a Chromium debug port; concurrent calls collide on the same port.
// Serialize all PDF generation through a promise chain to prevent EADDRINUSE.
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
  let buffer: Buffer;
  try {
    const result = await mdToPdf({ content: mdContent }, { css: CSS });
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
