/** @jest-environment jsdom */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import CorrectionsPanel from '@/components/CorrectionsPanel';
import { ScopeProvider, type Scope } from '@/lib/client/scope';

// T11 dropped the `outputFolder` PROP; the panel reads the scope instead. These existing cases
// keep exercising the LOCAL path, so they get a local ScopeProvider and their assertions are
// unchanged — the payload they check is still { outputFolder, corrections }.
const LOCAL: Scope = { mode: 'local', outputFolder: '/tmp/out', baseOutputFolder: '/tmp' };
const CLOUD: Scope = { mode: 'cloud', playlistId: '11111111-2222-3333-4444-555555555555' };

const VIDEO_ID      = 'abc123';
const OUTPUT_FOLDER = '/tmp/out';

let fetchMock: jest.Mock;

beforeEach(() => {
  fetchMock = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ tldr: 'New TL;DR.', takeaways: ['Point one'], corrections: 'Fix Clawcode' }),
  } as unknown as Response);
  global.fetch = fetchMock as typeof global.fetch;
});

afterEach(() => jest.clearAllMocks());

function renderPanel({
  initialCorrections,
  onClose = jest.fn(),
  onSuccess = jest.fn(),
}: {
  initialCorrections?: string;
  onClose?: jest.Mock;
  onSuccess?: jest.Mock;
} = {}) {
  render(
    <ScopeProvider scope={LOCAL}>
      <CorrectionsPanel
        videoId={VIDEO_ID}
        initialCorrections={initialCorrections}
        onClose={onClose}
        onSuccess={onSuccess}
      />
    </ScopeProvider>,
  );
  return { onClose, onSuccess };
}

describe('CorrectionsPanel', () => {
  describe('rendering', () => {
    it('renders a dialog with textarea and Regenerate button', () => {
      renderPanel();
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /regenerate/i })).toBeInTheDocument();
    });

    it('textarea is pre-filled with initialCorrections', () => {
      renderPanel({ initialCorrections: 'Fix Clawcode' });
      expect(screen.getByRole('textbox')).toHaveValue('Fix Clawcode');
    });

    it('portals the overlay to <body> so it is not an invalid <div> child of <tbody>', () => {
      // Mirrors the real mount site: VideoRow renders this inside VideoList's <table><tbody>.
      render(
        <ScopeProvider scope={LOCAL}>
          <table><tbody data-testid="tbody"><tr><td>
            <CorrectionsPanel
              videoId={VIDEO_ID}
              initialCorrections={undefined}
              onClose={jest.fn()}
              onSuccess={jest.fn()}
            />
          </td></tr></tbody></table>
        </ScopeProvider>,
      );
      const backdrop = screen.getByTestId('corrections-backdrop');
      // Portaled to document.body — NOT nested inside the table (which caused the hydration error).
      expect(backdrop.closest('tbody')).toBeNull();
      expect(backdrop.parentElement).toBe(document.body);
    });

    it('textarea is empty when initialCorrections is undefined', () => {
      renderPanel();
      expect(screen.getByRole('textbox')).toHaveValue('');
    });

    it('textarea receives focus when panel opens', () => {
      renderPanel();
      expect(screen.getByRole('textbox')).toHaveFocus();
    });
  });

  describe('dismissal', () => {
    it('Cancel button calls onClose without calling onSuccess', () => {
      const { onClose, onSuccess } = renderPanel();
      fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
      expect(onClose).toHaveBeenCalledTimes(1);
      expect(onSuccess).not.toHaveBeenCalled();
    });

    it('Escape key calls onClose', () => {
      const { onClose } = renderPanel();
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('clicking backdrop calls onClose', () => {
      const { onClose } = renderPanel();
      fireEvent.click(screen.getByTestId('corrections-backdrop'));
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('regeneration', () => {
    it('Regenerate button posts to the correct API endpoint', async () => {
      renderPanel({ initialCorrections: 'Fix Clawcode' });
      fireEvent.click(screen.getByRole('button', { name: /regenerate/i }));
      await waitFor(() => expect(fetchMock).toHaveBeenCalled());
      const [url, opts] = fetchMock.mock.calls[0];
      expect(url).toBe(`/api/videos/${VIDEO_ID}/regenerate`);
      const body = JSON.parse((opts as RequestInit).body as string);
      expect(body).toMatchObject({ outputFolder: OUTPUT_FOLDER, corrections: 'Fix Clawcode' });
    });

    it('calls onSuccess with tldr, takeaways, corrections, and summaryHtml:null on success', async () => {
      const { onSuccess } = renderPanel({ initialCorrections: 'Fix Clawcode' });
      fireEvent.click(screen.getByRole('button', { name: /regenerate/i }));
      await waitFor(() => expect(onSuccess).toHaveBeenCalledWith({
        corrections: 'Fix Clawcode',
        tldr: 'New TL;DR.',
        takeaways: ['Point one'],
        summaryHtml: null,
      }));
    });

    it('calls onClose after successful regeneration', async () => {
      const { onClose } = renderPanel();
      fireEvent.click(screen.getByRole('button', { name: /regenerate/i }));
      await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    });
  });

  describe('loading state', () => {
    it('Regenerate and Cancel buttons are disabled while regenerating', async () => {
      fetchMock = jest.fn(() => new Promise<Response>(() => {}));
      global.fetch = fetchMock as typeof global.fetch;
      renderPanel();
      act(() => { fireEvent.click(screen.getByRole('button', { name: /regenerate/i })); });
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /regenerating/i })).toBeDisabled();
        expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
      });
    });

    it('Escape and backdrop are no-ops while regenerating', () => {
      fetchMock = jest.fn(() => new Promise<Response>(() => {}));
      global.fetch = fetchMock as typeof global.fetch;
      const { onClose } = renderPanel();
      act(() => { fireEvent.click(screen.getByRole('button', { name: /regenerate/i })); });
      fireEvent.keyDown(window, { key: 'Escape' });
      fireEvent.click(screen.getByTestId('corrections-backdrop'));
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('error handling', () => {
    it('shows error message and keeps panel open when API fails', async () => {
      fetchMock = jest.fn().mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ error: 'Gemini quota exceeded' }),
      } as unknown as Response);
      global.fetch = fetchMock as typeof global.fetch;
      const { onSuccess } = renderPanel();
      fireEvent.click(screen.getByRole('button', { name: /regenerate/i }));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByRole('alert')).toHaveTextContent('Gemini quota exceeded');
      });
      expect(onSuccess).not.toHaveBeenCalled();
    });

    it('shows fallback error message when API returns no error field', async () => {
      fetchMock = jest.fn().mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({}),
      } as unknown as Response);
      global.fetch = fetchMock as typeof global.fetch;
      renderPanel();
      fireEvent.click(screen.getByRole('button', { name: /regenerate/i }));
      await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    });
  });
});

// ── T11: scope-awareness and the §6 outcome discriminator ─────────────────────────────────────
// ⚠ `@testing-library/user-event` IS NOT A DEPENDENCY — verified against package.json 2026-08-24.
// This file's existing idiom (fireEvent inside act) is followed rather than adding one for a
// handful of clicks.
describe('scope-awareness (T11)', () => {
  function renderIn(scope: Scope, initial?: string, onClose = jest.fn()) {
    render(
      <ScopeProvider scope={scope}>
        <CorrectionsPanel videoId="v1" initialCorrections={initial} onClose={onClose} onSuccess={() => {}} />
      </ScopeProvider>,
    );
    return { onClose };
  }

  async function press() {
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: /regenerate/i })); });
  }

  function respond(body: Record<string, unknown>, ok = true, status = 200) {
    fetchMock.mockResolvedValue({ ok, status, json: () => Promise.resolve(body) } as unknown as Response);
  }

  it('posts ?playlist=<uuid> and NO outputFolder in cloud mode', async () => {
    respond({ outcome: 'applied', tldr: 't', takeaways: [] });
    renderIn(CLOUD, 'fix X');
    await press();
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('?playlist=11111111-2222-3333-4444-555555555555');
    expect(JSON.parse(String(init.body))).toEqual({ corrections: 'fix X' });
  });

  it('posts outputFolder and no query string in local mode', async () => {
    respond({ outcome: 'applied', tldr: 't', takeaways: [] });
    renderIn(LOCAL, 'fix X');
    await press();
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).not.toContain('?playlist=');
    expect(JSON.parse(String(init.body))).toEqual({ outputFolder: '/tmp/out', corrections: 'fix X' });
  });

  it('reports no-corrections so a press that changed nothing does not read as a bug', async () => {
    respond({ outcome: 'no-corrections', tldr: 't', takeaways: [] });
    renderIn(CLOUD, '');
    await press();
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/no corrections to apply/i));
  });

  it('KEEPS THE PANEL OPEN on no-corrections — otherwise the discriminator is unreachable', async () => {
    // The plan added the status line and left the unconditional onClose(). The panel would unmount
    // and the message would never render. This asserts the behaviour the message depends on.
    respond({ outcome: 'no-corrections', tldr: 't', takeaways: [] });
    const { onClose } = renderIn(CLOUD, '');
    await press();
    expect(onClose).not.toHaveBeenCalled();
  });

  it('still closes on an applied correction — the changed summary is its own feedback', async () => {
    respond({ outcome: 'applied', tldr: 't', takeaways: [] });
    const { onClose } = renderIn(CLOUD, 'fix X');
    await press();
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });

  it('shows the over-cap message, not a generic failure', async () => {
    respond({ error: 'This summary is too long to correct', code: 'summary-too-large' }, false, 413);
    renderIn(CLOUD, 'fix X');
    await press();
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/too long to correct/i));
  });
});
