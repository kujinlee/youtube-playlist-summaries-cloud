/** @jest-environment jsdom */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import VideoQuickView from '@/components/VideoQuickView';
import { ScopeProvider, type Scope } from '@/lib/client/scope';
import { getQuickView, UnauthorizedError } from '@/lib/client/api';

jest.mock('@/lib/client/api', () => ({
  getQuickView: jest.fn(),
  UnauthorizedError: class UnauthorizedError extends Error {},
}));

const mockRouterReplace = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockRouterReplace }),
}));

const VIDEO_ID = 'abc123XYZ01';
const LOCAL_SCOPE: Scope = { mode: 'local', outputFolder: '/tmp/vault', baseOutputFolder: '/tmp' };
const CLOUD_SCOPE: Scope = { mode: 'cloud', playlistId: 'pl-1' };

const getQuickViewMock = getQuickView as jest.Mock;

function renderQuickView(
  props: Omit<React.ComponentProps<typeof VideoQuickView>, 'videoId'> = {},
  scope: Scope = LOCAL_SCOPE,
) {
  return render(
    <ScopeProvider scope={scope}>
      <VideoQuickView videoId={VIDEO_ID} {...props} />
    </ScopeProvider>,
  );
}

describe('VideoQuickView', () => {
  beforeEach(() => {
    getQuickViewMock.mockReset();
    mockRouterReplace.mockReset();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders TL;DR, takeaways, and concept pills immediately when data provided', () => {
    renderQuickView({
      tldr: 'This video teaches RAG pipelines.',
      takeaways: ['Chunk documents first', 'Embed then retrieve'],
      tags: ['rag', 'llm'],
    });
    expect(screen.getByText('This video teaches RAG pipelines.')).toBeInTheDocument();
    expect(screen.getByText('Chunk documents first')).toBeInTheDocument();
    expect(screen.getByText('Embed then retrieve')).toBeInTheDocument();
    expect(screen.getByText('rag')).toBeInTheDocument();
    expect(screen.getByText('llm')).toBeInTheDocument();
    expect(getQuickViewMock).not.toHaveBeenCalled();
  });

  it('shows loading state when tldr is absent', () => {
    getQuickViewMock.mockReturnValue(new Promise(() => {})); // never resolves
    renderQuickView();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows error message when the API call rejects', async () => {
    getQuickViewMock.mockRejectedValue(new Error('not found'));
    renderQuickView();
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('alert').textContent).toContain('not yet generated');
  });

  it('shows data after a successful call when tldr is absent', async () => {
    getQuickViewMock.mockResolvedValue({
      tldr: 'This video explains RAG.',
      takeaways: ['Point one'],
      tags: ['rag'],
    });
    renderQuickView();
    await waitFor(() => expect(screen.getByText('This video explains RAG.')).toBeInTheDocument());
    expect(screen.getByText('Point one')).toBeInTheDocument();
    expect(screen.getByText('rag')).toBeInTheDocument();
    expect(getQuickViewMock).toHaveBeenCalledWith(LOCAL_SCOPE, VIDEO_ID);
  });

  it('renders without concept pills when tags are empty', () => {
    renderQuickView({
      tldr: 'This video teaches X.',
      takeaways: ['Point one'],
      tags: [],
    });
    expect(screen.queryByText('Key Takeaways')).not.toBeNull();
    // Concepts section absent when tags are empty — assert no tag text rendered
    expect(screen.queryByText('rag')).not.toBeInTheDocument();
    expect(screen.queryByText('llm')).not.toBeInTheDocument();
  });

  describe('unauthorized (cloud mode)', () => {
    it('redirects to /login on UnauthorizedError instead of showing the "not yet generated" alert', async () => {
      getQuickViewMock.mockRejectedValue(new UnauthorizedError('unauthorized'));
      renderQuickView({}, CLOUD_SCOPE);
      await waitFor(() => expect(mockRouterReplace).toHaveBeenCalledWith('/login'));
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });
});
