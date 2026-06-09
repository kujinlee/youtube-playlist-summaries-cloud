// Stub normalizeToRoot so the route's behavior is observable without touching fs.
jest.mock('../../lib/output-folder', () => ({
  ...jest.requireActual('../../lib/output-folder'),
  normalizeToRoot: jest.fn(),
}));

import { GET } from '../../app/api/normalize-folder/route';
import * as outputFolder from '../../lib/output-folder';

const mockNormalize = jest.mocked(outputFolder.normalizeToRoot);

function getReq(query: string) {
  return GET(new Request(`http://localhost/api/normalize-folder${query}`));
}

describe('GET /api/normalize-folder', () => {
  beforeEach(() => jest.clearAllMocks());

  it('E7: 400 when path param is missing', async () => {
    const res = await getReq('');
    expect(res.status).toBe(400);
    expect(mockNormalize).not.toHaveBeenCalled();
  });

  it('E7: 400 when path is blank/whitespace', async () => {
    const res = await getReq(`?path=${encodeURIComponent('   ')}`);
    expect(res.status).toBe(400);
    expect(mockNormalize).not.toHaveBeenCalled();
  });

  it('E8: returns { root: normalizeToRoot(path) }', async () => {
    mockNormalize.mockReturnValue('/d');
    const res = await getReq(`?path=${encodeURIComponent('/d/cs146s/raw')}`);
    expect(res.status).toBe(200);
    expect(mockNormalize).toHaveBeenCalledWith('/d/cs146s/raw');
    expect(await res.json()).toEqual({ root: '/d' });
  });

  it('E9: 500 generic when normalizeToRoot throws', async () => {
    mockNormalize.mockImplementation(() => {
      throw new Error('EACCES /secret');
    });
    const res = await getReq(`?path=${encodeURIComponent('/d/x')}`);
    expect(res.status).toBe(500);
    expect(await res.json()).toEqual({ error: 'failed to normalize folder' });
  });
});
