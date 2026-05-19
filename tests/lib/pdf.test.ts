import { generatePdf } from '../../lib/pdf';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

jest.setTimeout(30_000);

const tmpDir = os.tmpdir();
let outputPath: string;

function tempPath(suffix: string): string {
  return path.join(tmpDir, `test-pdf-${Date.now()}-${suffix}.pdf`);
}

afterEach(() => {
  if (outputPath && fs.existsSync(outputPath)) {
    fs.rmSync(outputPath);
  }
  outputPath = '';
});

describe('generatePdf', () => {
  it('creates a non-empty PDF file at the given output path', async () => {
    outputPath = tempPath('basic');

    await generatePdf('# Hello\n\nThis is a test summary.', outputPath);

    expect(fs.existsSync(outputPath)).toBe(true);
    expect(fs.statSync(outputPath).size).toBeGreaterThan(0);
  });

  it('renders Korean text without error and produces a non-empty file', async () => {
    outputPath = tempPath('korean');
    // Verifies the pipeline does not throw — not a guarantee of legible glyph rendering,
    // which depends on CJK fonts being installed in the environment.
    await generatePdf(
      '# 제목\n\n한국어 텍스트 테스트입니다. 머신러닝과 딥러닝에 관한 영상입니다.',
      outputPath,
    );

    expect(fs.existsSync(outputPath)).toBe(true);
    expect(fs.statSync(outputPath).size).toBeGreaterThan(0);
  });

  it('throws with wrapped message when output path parent directory does not exist', async () => {
    outputPath = ''; // nothing to clean up
    const badPath = path.join(tmpDir, 'nonexistent-subdir', 'out.pdf');

    const err = await generatePdf('# Hello', badPath).catch((e) => e);

    expect(err.message).toMatch(/PDF generation failed/);
    expect((err.cause as NodeJS.ErrnoException).code).toBe('ENOENT');
  });

  it('renders ASCII art code blocks without error and produces a non-empty file', async () => {
    outputPath = tempPath('ascii');
    const content = [
      '# Deep Dive',
      '',
      '```',
      '+-------+    +-------+',
      '| Input | -> | Output|',
      '+-------+    +-------+',
      '```',
    ].join('\n');

    await generatePdf(content, outputPath);

    expect(fs.existsSync(outputPath)).toBe(true);
    expect(fs.statSync(outputPath).size).toBeGreaterThan(0);
  });
});
