/** @jest-environment jsdom */
import { render, screen, fireEvent } from '@testing-library/react';
import VideoMenu from '../../components/VideoMenu';
import { ScopeProvider, type Scope } from '@/lib/client/scope';

const LOCAL_SCOPE: Scope = { mode: 'local', outputFolder: '/o', baseOutputFolder: '/o' };
const CLOUD_SCOPE: Scope = { mode: 'cloud', playlistId: '11111111-1111-1111-1111-111111111111' };

function renderMenu(ui: React.ReactElement, scope: Scope = LOCAL_SCOPE) {
  return render(<ScopeProvider scope={scope}>{ui}</ScopeProvider>);
}

const base = {
  id: 'vid11111111', title: 'T', youtubeUrl: 'https://youtu.be/x', language: 'en',
  durationSeconds: 5, archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: 'base.md', processedAt: '2026-01-01T00:00:00.000Z',
};
const props = { outputFolder: '/o', baseOutputFolder: '/o', onArchive() {}, onEditCorrections() {}, onGenerateHtml() {}, onClose() {}, busy: false };

// ── HTML doc (existing tests, unchanged — now rendered under a local ScopeProvider) ─────────

it('shows a single "HTML doc" item — a direct link when current (html + docVersion 3.3)', () => {
  renderMenu(<VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html', docVersion: { major: 3, minor: 3 } } as any} />);
  const el = screen.getByRole('link', { name: /HTML doc/i });
  expect(el).toHaveAttribute('href', expect.stringContaining('/api/html/'));
  expect(screen.queryByText(/Generate HTML doc|Regenerate HTML doc|View HTML doc/)).toBeNull();
});

it('renders a button when stale (pre-feature: no docVersion)', () => {
  renderMenu(<VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html' } as any} />);
  expect(screen.getByRole('button', { name: /HTML doc/i })).toBeInTheDocument();
});

it('disables the item while busy', () => {
  renderMenu(<VideoMenu {...props} busy video={{ ...base, summaryHtml: 'htmls/base.html', docVersion: { major: 3, minor: 3 } } as any} />);
  expect(screen.getByText(/HTML doc/i).closest('a,button,span')).toHaveAttribute('aria-disabled', 'true');
});

it('does not render PDF menu items (PDF generation removed)', () => {
  renderMenu(<VideoMenu {...props} video={base as any} />);
  expect(screen.queryByText('View Summary PDF')).not.toBeInTheDocument();
  expect(screen.queryByText('View Deep Dive PDF')).not.toBeInTheDocument();
});

// ── Re-summarize (Stage 3) ───────────────────────────────────────────────────

it('renders a "Re-summarize" button and calls onResummarize(id) + onClose on click', () => {
  const onResummarize = jest.fn();
  const onClose = jest.fn();
  renderMenu(<VideoMenu {...props} onResummarize={onResummarize} onClose={onClose} video={base as any} />);
  const btn = screen.getByRole('button', { name: /Re-summarize/i });
  fireEvent.click(btn);
  expect(onResummarize).toHaveBeenCalledWith('vid11111111');
  expect(onClose).toHaveBeenCalled();
});

it('disables Re-summarize (⏳, no button) while busy', () => {
  renderMenu(<VideoMenu {...props} busy video={base as any} />);
  const el = screen.getByText(/Re-summarize/i).closest('a,button,span');
  expect(el).toHaveAttribute('aria-disabled', 'true');
  expect(screen.queryByRole('button', { name: /Re-summarize/i })).toBeNull();
});

it('omits Re-summarize when there is no summary', () => {
  renderMenu(<VideoMenu {...props} video={{ ...base, summaryMd: null } as any} />);
  expect(screen.queryByText(/Re-summarize/i)).toBeNull();
});

// ── Save PDF (auto PDF export) ───────────────────────────────────────────────

it('shows "Save summary PDF" only when summaryHtml is present', () => {
  const { rerender } = render(<ScopeProvider scope={LOCAL_SCOPE}><VideoMenu {...props} video={base as any} /></ScopeProvider>);
  expect(screen.queryByText(/Save summary PDF/i)).toBeNull(); // summaryMd only, no summaryHtml
  rerender(<ScopeProvider scope={LOCAL_SCOPE}><VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html' } as any} /></ScopeProvider>);
  expect(screen.getByRole('button', { name: /Save summary PDF/i })).toBeInTheDocument();
});

it('shows "Save dig-deeper PDF" only when digDeeperMd is present', () => {
  const { rerender } = render(<ScopeProvider scope={LOCAL_SCOPE}><VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html' } as any} /></ScopeProvider>);
  expect(screen.queryByText(/Save dig-deeper PDF/i)).toBeNull();
  rerender(<ScopeProvider scope={LOCAL_SCOPE}><VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html', digDeeperMd: 'base-dig-deeper.md' } as any} /></ScopeProvider>);
  expect(screen.getByRole('button', { name: /Save dig-deeper PDF/i })).toBeInTheDocument();
});

it('calls onSavePdf(id, type) + onClose on click', () => {
  const onSavePdf = jest.fn();
  const onClose = jest.fn();
  renderMenu(<VideoMenu {...props} onSavePdf={onSavePdf} onClose={onClose}
    video={{ ...base, summaryHtml: 'htmls/base.html', digDeeperMd: 'base-dig-deeper.md' } as any} />);
  fireEvent.click(screen.getByRole('button', { name: /Save summary PDF/i }));
  expect(onSavePdf).toHaveBeenCalledWith('vid11111111', 'summary');
  fireEvent.click(screen.getByRole('button', { name: /Save dig-deeper PDF/i }));
  expect(onSavePdf).toHaveBeenCalledWith('vid11111111', 'dig-deeper');
  expect(onClose).toHaveBeenCalledTimes(2);
});

it('disables Save PDF items while busy', () => {
  renderMenu(<VideoMenu {...props} busy video={{ ...base, summaryHtml: 'htmls/base.html' } as any} />);
  expect(screen.getByText(/Save summary PDF/i).closest('a,button,span')).toHaveAttribute('aria-disabled', 'true');
});

// ── Cloud mode allowlist (Stage 2a T15b) ─────────────────────────────────────
// In cloud scope, only "Watch on YouTube" + Archive/Unarchive render; everything that depends
// on the local filesystem pipeline (doc/HTML/PDF/deep-dive/corrections/Obsidian/Ask-Gemini) is
// hidden. Local mode (tests above) is unchanged.

const fullVideo = {
  ...base,
  summaryHtml: 'htmls/base.html',
  digDeeperMd: 'base-dig-deeper.md',
  docVersion: { major: 3, minor: 3 },
};

it('cloud mode: shows only "Watch on YouTube" and Archive/Unarchive', () => {
  renderMenu(<VideoMenu {...props} video={fullVideo as any} />, CLOUD_SCOPE);

  expect(screen.getByRole('link', { name: /Watch on YouTube/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /^Archive$/i })).toBeInTheDocument();

  expect(screen.queryByText(/Ask Gemini/i)).toBeNull();
  expect(screen.queryByText(/Open in Obsidian/i)).toBeNull();
  expect(screen.queryByText(/HTML doc/i)).toBeNull();
  expect(screen.queryByText(/Re-summarize/i)).toBeNull();
  expect(screen.queryByText(/Save summary PDF/i)).toBeNull();
  expect(screen.queryByText(/Save dig-deeper PDF/i)).toBeNull();
  expect(screen.queryByText(/Edit corrections/i)).toBeNull();
});

it('cloud mode: Archive/Unarchive still calls onArchive + onClose', () => {
  const onArchive = jest.fn();
  const onClose = jest.fn();
  renderMenu(<VideoMenu {...props} onArchive={onArchive} onClose={onClose} video={fullVideo as any} />, CLOUD_SCOPE);
  fireEvent.click(screen.getByRole('button', { name: /^Archive$/i }));
  expect(onArchive).toHaveBeenCalledWith('vid11111111', 'archive');
  expect(onClose).toHaveBeenCalled();
});

it('local mode: full menu still renders (doc/PDF/Obsidian/Ask-Gemini/corrections present)', () => {
  renderMenu(<VideoMenu {...props} video={fullVideo as any} />, LOCAL_SCOPE);

  expect(screen.getByRole('link', { name: /Watch on YouTube/i })).toBeInTheDocument();
  expect(screen.getByText(/Ask Gemini/i)).toBeInTheDocument();
  expect(screen.getByText(/Open in Obsidian/i)).toBeInTheDocument();
  expect(screen.getByText(/HTML doc/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Re-summarize/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Save summary PDF/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Save dig-deeper PDF/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Edit corrections/i })).toBeInTheDocument();
});
