jest.mock('../../lib/archive');
jest.mock('../../lib/index-store');

import { POST } from '../../app/api/videos/[id]/archive/route';
import * as archive from '../../lib/archive';
import * as indexStore from '../../lib/index-store';

const mockArchiveVideo = jest.mocked(archive.archiveVideo);
const mockUnarchiveVideo = jest.mocked(archive.unarchiveVideo);
const mockAssertOutputFolder = jest.mocked(indexStore.assertOutputFolder);
const mockAssertVideoId = jest.mocked(indexStore.assertVideoId);

const OUTPUT_FOLDER = '/tmp/out';
const VIDEO_ID = 'testVideoId1';

function postArchive(videoId: string, body: object) {
  return POST(
    new Request(`http://localhost/api/videos/${videoId}/archive`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
    { params: Promise.resolve({ id: videoId }) },
  );
}

describe('POST /api/videos/[id]/archive', () => {
  beforeEach(() => {
    mockAssertOutputFolder.mockImplementation(() => {});
    mockAssertVideoId.mockImplementation(() => {});
    mockArchiveVideo.mockResolvedValue(undefined);
    mockUnarchiveVideo.mockResolvedValue(undefined);
  });

  afterEach(() => jest.clearAllMocks());

  it('calls archiveVideo and returns { ok: true } for action: archive', async () => {
    const res = await postArchive(VIDEO_ID, { action: 'archive', outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ ok: true });
    expect(mockArchiveVideo).toHaveBeenCalledWith(OUTPUT_FOLDER, VIDEO_ID);
  });

  it('calls unarchiveVideo and returns { ok: true } for action: unarchive', async () => {
    const res = await postArchive(VIDEO_ID, { action: 'unarchive', outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ ok: true });
    expect(mockUnarchiveVideo).toHaveBeenCalledWith(OUTPUT_FOLDER, VIDEO_ID);
  });

  it('returns 400 for invalid action', async () => {
    const res = await postArchive(VIDEO_ID, { action: 'delete', outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(400);
  });

  it('returns 400 when outputFolder is missing', async () => {
    const res = await postArchive(VIDEO_ID, { action: 'archive' });
    expect(res.status).toBe(400);
  });

  it('returns 400 for invalid videoId', async () => {
    mockAssertVideoId.mockImplementation(() => { throw Object.assign(new Error('invalid videoId'), { statusCode: 400 }); });
    const res = await postArchive('../etc/passwd', { action: 'archive', outputFolder: OUTPUT_FOLDER });
    expect(res.status).toBe(400);
  });
});
