jest.mock('../../lib/index-store');

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as crypto from 'crypto';
import { GET } from '../../app/api/pdf/[id]/route';
import * as indexStore from '../../lib/index-store';

const mockAssertOutputFolder = jest.mocked(indexStore.assertOutputFolder);
const mockAssertVideoId = jest.mocked(indexStore.assertVideoId);

const OUTPUT_FOLDER = '/tmp/out';

function getPdf(videoId: string, params: Record<string, string> = {}) {
  const query = new URLSearchParams({ outputFolder: OUTPUT_FOLDER, ...params }).toString();
  return GET(
    new Request(`http://localhost/api/pdf/${videoId}?${query}`),
    { params: Promise.resolve({ id: videoId }) },
  );
}

describe('GET /api/pdf/[id]', () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = path.join(os.tmpdir(), `pdf-test-${crypto.randomUUID()}`);
    fs.mkdirSync(tempDir, { recursive: true });
    mockAssertOutputFolder.mockImplementation(() => {});
    mockAssertVideoId.mockImplementation(() => {});
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
    jest.clearAllMocks();
  });

  it('returns 404 when PDF file does not exist', async () => {
    const res = await getPdf('vid1', { outputFolder: tempDir });
    expect(res.status).toBe(404);
  });

  it('returns 200 with application/pdf when file exists', async () => {
    const pdfPath = path.join(tempDir, 'vid1.pdf');
    fs.writeFileSync(pdfPath, '%PDF-1.4 fake content');

    const res = await getPdf('vid1', { outputFolder: tempDir });
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('application/pdf');
  });

  it('returns 400 when outputFolder is missing', async () => {
    const res = await GET(
      new Request('http://localhost/api/pdf/vid1'),
      { params: Promise.resolve({ id: 'vid1' }) },
    );
    expect(res.status).toBe(400);
  });

  it('returns 400 for invalid videoId', async () => {
    mockAssertVideoId.mockImplementation(() => { throw Object.assign(new Error('invalid'), { statusCode: 400 }); });
    const res = await getPdf('../etc/passwd', { outputFolder: tempDir });
    expect(res.status).toBe(400);
  });
});
