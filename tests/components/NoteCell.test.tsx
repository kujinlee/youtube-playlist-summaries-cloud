/** @jest-environment jsdom */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import NoteCell from '@/components/NoteCell';
import { ScopeProvider, type Scope } from '@/lib/client/scope';
import { saveAnnotation } from '@/lib/client/api';

jest.mock('@/lib/client/api', () => ({
  saveAnnotation: jest.fn(),
}));

const VIDEO_ID = 'abc123';
const LOCAL_SCOPE: Scope = { mode: 'local', outputFolder: '/tmp/out', baseOutputFolder: '/tmp' };

const saveAnnotationMock = saveAnnotation as jest.Mock;

beforeEach(() => {
  saveAnnotationMock.mockReset();
  saveAnnotationMock.mockResolvedValue(undefined);
});

afterEach(() => jest.clearAllMocks());

function renderNote(value?: string, onChange = jest.fn()) {
  render(
    <ScopeProvider scope={LOCAL_SCOPE}>
      <NoteCell videoId={VIDEO_ID} value={value} onChange={onChange} />
    </ScopeProvider>,
  );
  return { onChange };
}

function openPopover(value?: string, onChange = jest.fn()) {
  const result = renderNote(value, onChange);
  fireEvent.click(screen.getByRole('button', { name: /add note|edit note|—|.*/i }));
  return result;
}

describe('NoteCell', () => {
  describe('preview', () => {
    it('shows — when note is undefined', () => {
      renderNote(undefined);
      expect(screen.getByRole('button')).toHaveTextContent('—');
    });

    it('shows note text when note is 25 chars or fewer', () => {
      renderNote('short note');
      expect(screen.getByRole('button')).toHaveTextContent('short note');
    });

    it('shows first 25 chars followed by … when note exceeds 25 chars', () => {
      renderNote('this is a very long note that goes beyond twenty-five characters');
      const btn = screen.getByRole('button');
      expect(btn.textContent).toHaveLength(26); // 25 chars + '…' (1 UTF-16 code unit)
      expect(btn.textContent).toMatch(/…$/);
    });
  });

  describe('popover open', () => {
    it('clicking cell opens a dialog', () => {
      openPopover('my note');
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('popover textarea is pre-filled with existing note', () => {
      openPopover('my note');
      expect(screen.getByRole('textbox')).toHaveValue('my note');
    });

    it('popover textarea is empty when note is undefined', () => {
      openPopover(undefined);
      expect(screen.getByRole('textbox')).toHaveValue('');
    });

    it('textarea receives focus when popover opens', () => {
      openPopover('my note');
      expect(screen.getByRole('textbox')).toHaveFocus();
    });
  });

  describe('cancel / dismiss', () => {
    it('Cancel button closes popover without calling onChange', () => {
      const { onChange } = openPopover('my note');
      fireEvent.change(screen.getByRole('textbox'), { target: { value: 'edited' } });
      fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(onChange).not.toHaveBeenCalled();
    });

    it('Escape key closes popover without calling onChange', () => {
      const { onChange } = openPopover('my note');
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(onChange).not.toHaveBeenCalled();
    });

    it('clicking the backdrop closes popover without calling onChange', () => {
      const { onChange } = openPopover('my note');
      fireEvent.click(screen.getByTestId('note-backdrop'));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe('save', () => {
    it('Save calls onChange with the typed note and closes popover', async () => {
      const { onChange } = openPopover('old note');
      fireEvent.change(screen.getByRole('textbox'), { target: { value: 'new note' } });
      fireEvent.click(screen.getByRole('button', { name: /save/i }));
      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith('new note');
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('Save with empty textarea calls onChange with undefined (clear note)', async () => {
      const { onChange } = openPopover('existing note');
      fireEvent.change(screen.getByRole('textbox'), { target: { value: '' } });
      fireEvent.click(screen.getByRole('button', { name: /save/i }));
      await waitFor(() => expect(onChange).toHaveBeenCalledWith(undefined));
    });
  });

  describe('saving state', () => {
    it('Save and Cancel buttons are disabled while saving', async () => {
      saveAnnotationMock.mockReturnValue(new Promise(() => {}));
      openPopover('note');
      act(() => { fireEvent.click(screen.getByRole('button', { name: /save/i })); });
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled();
        expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
      });
    });

    it('shows inline error and keeps popover open when API call fails', async () => {
      saveAnnotationMock.mockRejectedValue(new Error('internal error'));
      const { onChange } = openPopover('note');
      fireEvent.click(screen.getByRole('button', { name: /save/i }));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument(); // still open
        expect(screen.getByText('internal error')).toBeInTheDocument();
      });
      expect(onChange).not.toHaveBeenCalled();
    });

    it('Escape and backdrop are no-ops while saving', () => {
      saveAnnotationMock.mockReturnValue(new Promise(() => {}));
      openPopover('note');
      act(() => { fireEvent.click(screen.getByRole('button', { name: /save/i })); });
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      fireEvent.click(screen.getByTestId('note-backdrop'));
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  describe('saveAnnotation call', () => {
    it('calls saveAnnotation with the scope, videoId, and personalNote', async () => {
      openPopover('old');
      fireEvent.change(screen.getByRole('textbox'), { target: { value: 'updated note' } });
      fireEvent.click(screen.getByRole('button', { name: /save/i }));
      await waitFor(() => expect(saveAnnotationMock).toHaveBeenCalled());
      expect(saveAnnotationMock).toHaveBeenCalledWith(LOCAL_SCOPE, VIDEO_ID, { personalNote: 'updated note' });
    });

    it('calls saveAnnotation with personalNote: "" when textarea is cleared (triggers deletion)', async () => {
      openPopover('old note');
      fireEvent.change(screen.getByRole('textbox'), { target: { value: '' } });
      fireEvent.click(screen.getByRole('button', { name: /save/i }));
      await waitFor(() => expect(saveAnnotationMock).toHaveBeenCalled());
      expect(saveAnnotationMock).toHaveBeenCalledWith(LOCAL_SCOPE, VIDEO_ID, { personalNote: '' });
    });

    it('does not reject a 500-char note (maxLength enforced by textarea)', async () => {
      const maxNote = 'a'.repeat(500);
      openPopover(undefined);
      fireEvent.change(screen.getByRole('textbox'), { target: { value: maxNote } });
      fireEvent.click(screen.getByRole('button', { name: /save/i }));
      await waitFor(() => expect(saveAnnotationMock).toHaveBeenCalled());
      const patch = saveAnnotationMock.mock.calls[0][2];
      expect(patch.personalNote).toHaveLength(500);
    });
  });
});
