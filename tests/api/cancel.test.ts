jest.mock('../../lib/job-registry');

import { POST } from '../../app/api/ingest/cancel/route';
import * as jobRegistry from '../../lib/job-registry';

const mockCancelJob = jest.mocked(jobRegistry.cancelJob);

function postCancel(body: object) {
  return POST(new Request('http://localhost/api/ingest/cancel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }));
}

describe('POST /api/ingest/cancel', () => {
  afterEach(() => jest.clearAllMocks());

  it('returns 200 and cancels a running job', async () => {
    mockCancelJob.mockReturnValue(true);
    const res = await postCancel({ jobId: 'job-1' });
    expect(res.status).toBe(200);
    expect(mockCancelJob).toHaveBeenCalledWith('job-1');
  });

  it('returns 404 when the job is not found', async () => {
    mockCancelJob.mockReturnValue(false);
    const res = await postCancel({ jobId: 'unknown-job' });
    expect(res.status).toBe(404);
  });

  it('returns 400 when jobId is missing', async () => {
    const res = await postCancel({});
    expect(res.status).toBe(400);
  });
});
