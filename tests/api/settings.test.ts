jest.mock('../../lib/settings-store');
jest.mock('../../lib/index-store');

import { GET, POST } from '../../app/api/settings/route';
import * as settingsStore from '../../lib/settings-store';
import * as indexStore from '../../lib/index-store';

const mockAssertOutputFolder = jest.mocked(indexStore.assertOutputFolder);

const mockReadSettings = jest.mocked(settingsStore.readSettings);
const mockWriteSettings = jest.mocked(settingsStore.writeSettings);

describe('GET /api/settings', () => {
  beforeEach(() => {
    mockAssertOutputFolder.mockImplementation(() => {});
  });

  afterEach(() => jest.clearAllMocks());

  it('returns current outputFolder', async () => {
    mockReadSettings.mockReturnValue({ outputFolder: '/home/user/data' });

    const res = await GET(new Request('http://localhost/api/settings'));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.outputFolder).toBe('/home/user/data');
  });

  it('returns baseOutputFolder when stored', async () => {
    mockReadSettings.mockReturnValue({ outputFolder: '/home/user/data', baseOutputFolder: '/home/user/data' });
    const res = await GET(new Request('http://localhost/api/settings'));
    const body = await res.json();
    expect(body.baseOutputFolder).toBe('/home/user/data');
  });

  it('returns outputFolder as baseOutputFolder when baseOutputFolder not stored', async () => {
    mockReadSettings.mockReturnValue({ outputFolder: '/home/user/data' });
    const res = await GET(new Request('http://localhost/api/settings'));
    const body = await res.json();
    expect(body.baseOutputFolder).toBe('/home/user/data');
  });
});

describe('POST /api/settings', () => {
  beforeEach(() => {
    mockAssertOutputFolder.mockImplementation(() => {});
  });

  afterEach(() => jest.clearAllMocks());

  it('saves outputFolder and returns { ok: true }', async () => {
    mockWriteSettings.mockImplementation(() => {});

    const res = await POST(new Request('http://localhost/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outputFolder: '/home/user/newdata' }),
    }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ ok: true });
    expect(mockWriteSettings).toHaveBeenCalledWith({ outputFolder: '/home/user/newdata' });
  });

  it('saves baseOutputFolder when provided alongside outputFolder', async () => {
    mockWriteSettings.mockImplementation(() => {});
    const res = await POST(new Request('http://localhost/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outputFolder: '/home/user/data', baseOutputFolder: '/home/user/data' }),
    }));
    expect(res.status).toBe(200);
    expect(mockWriteSettings).toHaveBeenCalledWith({
      outputFolder: '/home/user/data',
      baseOutputFolder: '/home/user/data',
    });
  });

  it('returns 400 when outputFolder is missing from body', async () => {
    const res = await POST(new Request('http://localhost/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    }));
    expect(res.status).toBe(400);
  });

  it('returns 400 when outputFolder is outside homedir', async () => {
    mockAssertOutputFolder.mockImplementation(() => {
      throw Object.assign(new Error('outputFolder outside home directory'), { statusCode: 400 });
    });
    const res = await POST(new Request('http://localhost/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outputFolder: '/etc/passwd' }),
    }));
    expect(res.status).toBe(400);
    expect(mockWriteSettings).not.toHaveBeenCalled();
  });

  it('returns 400 when outputFolder is not a string', async () => {
    const res = await POST(new Request('http://localhost/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outputFolder: 42 }),
    }));
    expect(res.status).toBe(400);
    expect(mockWriteSettings).not.toHaveBeenCalled();
  });
});
