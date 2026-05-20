/** @jest-environment jsdom */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import SortBar, { COLUMNS } from '@/components/SortBar';
import type { SortColumn, SortOrder } from '@/types';

function renderSortBar(
  activeColumn: SortColumn | null = null,
  order: SortOrder = 'asc',
  onSort = jest.fn(),
) {
  const result = render(<SortBar activeColumn={activeColumn} order={order} onSort={onSort} />);
  return { onSort, rerender: result.rerender };
}

describe('SortBar', () => {
  describe('rendering', () => {
    it('renders all 7 column labels', () => {
      renderSortBar();
      for (const { label } of COLUMNS) {
        expect(screen.getByText(new RegExp(label))).toBeInTheDocument();
      }
    });

    it('renders each column as a button', () => {
      renderSortBar();
      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(7);
    });

    it('renders columns in the correct order: Name USE DPT ORI RCN CMP OVR', () => {
      renderSortBar();
      const labels = screen
        .getAllByRole('button')
        .map((b) => b.textContent?.replace(/[↑↓]/g, '').trim());
      expect(labels).toEqual(['Name', 'USE', 'DPT', 'ORI', 'RCN', 'CMP', 'OVR']);
    });
  });

  describe('active column highlight', () => {
    it('marks active column with aria-pressed=true', () => {
      renderSortBar('usefulness', 'asc');
      expect(screen.getByRole('button', { name: /usefulness/i })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
    });

    it('marks all other columns with aria-pressed=false when one is active', () => {
      renderSortBar('usefulness', 'asc');
      for (const { fullName } of COLUMNS) {
        if (fullName !== 'Usefulness') {
          expect(screen.getByRole('button', { name: new RegExp(fullName, 'i') })).toHaveAttribute(
            'aria-pressed',
            'false',
          );
        }
      }
    });

    it('marks all columns aria-pressed=false when activeColumn is null', () => {
      renderSortBar(null);
      for (const { fullName } of COLUMNS) {
        expect(screen.getByRole('button', { name: new RegExp(fullName, 'i') })).toHaveAttribute(
          'aria-pressed',
          'false',
        );
      }
    });
  });

  describe('directional arrow', () => {
    it('shows ↑ on active column when order is asc', () => {
      renderSortBar('depth', 'asc');
      const btn = screen.getByTitle('Depth');
      expect(btn.textContent).toContain('↑');
    });

    it('shows ↓ on active column when order is desc', () => {
      renderSortBar('depth', 'desc');
      const btn = screen.getByTitle('Depth');
      expect(btn.textContent).toContain('↓');
    });

    it('shows no arrow on non-active columns', () => {
      renderSortBar('depth', 'asc');
      for (const { fullName } of COLUMNS) {
        if (fullName !== 'Depth') {
          const btn = screen.getByTitle(fullName);
          expect(btn.textContent).not.toContain('↑');
          expect(btn.textContent).not.toContain('↓');
        }
      }
    });

    it('shows no arrow on any column when activeColumn is null', () => {
      renderSortBar(null);
      for (const { fullName } of COLUMNS) {
        const btn = screen.getByTitle(fullName);
        expect(btn.textContent).not.toContain('↑');
        expect(btn.textContent).not.toContain('↓');
      }
    });
  });

  describe('accessible direction label', () => {
    it('active asc column has aria-label including "ascending"', () => {
      renderSortBar('depth', 'asc');
      expect(screen.getByTitle('Depth')).toHaveAttribute(
        'aria-label',
        'Depth, sorted ascending',
      );
    });

    it('active desc column has aria-label including "descending"', () => {
      renderSortBar('depth', 'desc');
      expect(screen.getByTitle('Depth')).toHaveAttribute(
        'aria-label',
        'Depth, sorted descending',
      );
    });

    it('non-active columns have aria-label with full name only', () => {
      renderSortBar('depth', 'asc');
      expect(screen.getByTitle('Usefulness')).toHaveAttribute('aria-label', 'Usefulness');
    });

    it('all columns have aria-label when no active column', () => {
      renderSortBar(null);
      for (const { fullName } of COLUMNS) {
        expect(screen.getByTitle(fullName)).toHaveAttribute('aria-label', fullName);
      }
    });
  });

  describe('tooltips', () => {
    it('each column button has a title attribute with the full name', () => {
      renderSortBar();
      for (const { fullName } of COLUMNS) {
        expect(screen.getByTitle(fullName)).toBeInTheDocument();
      }
    });
  });

  describe('onSort callback', () => {
    it('clicking a non-active column calls onSort with (column, asc)', () => {
      const { onSort } = renderSortBar('name', 'asc');
      fireEvent.click(screen.getByRole('button', { name: /usefulness/i }));
      expect(onSort).toHaveBeenCalledWith('usefulness', 'asc');
    });

    it('clicking the active column in asc order calls onSort with (column, desc)', () => {
      const { onSort } = renderSortBar('usefulness', 'asc');
      fireEvent.click(screen.getByRole('button', { name: /usefulness.*ascending/i }));
      expect(onSort).toHaveBeenCalledWith('usefulness', 'desc');
    });

    it('clicking the active column in desc order calls onSort with (column, asc)', () => {
      const { onSort } = renderSortBar('usefulness', 'desc');
      fireEvent.click(screen.getByRole('button', { name: /usefulness.*descending/i }));
      expect(onSort).toHaveBeenCalledWith('usefulness', 'asc');
    });

    it('clicking a column when activeColumn is null calls onSort with (column, asc)', () => {
      const { onSort } = renderSortBar(null);
      fireEvent.click(screen.getByRole('button', { name: /overall/i }));
      expect(onSort).toHaveBeenCalledWith('overall', 'asc');
    });

    it.each(COLUMNS)(
      'clicking $label emits the correct SortColumn value "$column"',
      ({ column, fullName }) => {
        const onSort = jest.fn();
        render(<SortBar activeColumn={null} order="asc" onSort={onSort} />);
        fireEvent.click(screen.getByRole('button', { name: new RegExp(fullName, 'i') }));
        expect(onSort).toHaveBeenCalledWith(column, 'asc');
      },
    );

    it('hover does not call onSort', () => {
      const { onSort } = renderSortBar(null);
      fireEvent.mouseEnter(screen.getByTitle('Depth'));
      expect(onSort).not.toHaveBeenCalled();
    });

    it('does not call onSort more than once per click', () => {
      const { onSort } = renderSortBar(null);
      fireEvent.click(screen.getByRole('button', { name: /^name$/i }));
      expect(onSort).toHaveBeenCalledTimes(1);
    });

    it('toggle sequence: click asc active → rerender desc → click again → emits asc', () => {
      const onSort = jest.fn();
      const { rerender } = render(
        <SortBar activeColumn="usefulness" order="asc" onSort={onSort} />,
      );
      fireEvent.click(screen.getByRole('button', { name: /usefulness.*ascending/i }));
      expect(onSort).toHaveBeenCalledWith('usefulness', 'desc');

      rerender(<SortBar activeColumn="usefulness" order="desc" onSort={onSort} />);
      fireEvent.click(screen.getByRole('button', { name: /usefulness.*descending/i }));
      expect(onSort).toHaveBeenCalledWith('usefulness', 'asc');
    });

    it('rapid double-click before rerender emits the same direction twice (controlled component contract)', () => {
      // As a controlled component, nextOrder is always computed from props.
      // Two clicks before the parent rerenders both see the same order prop → same emission.
      const onSort = jest.fn();
      render(<SortBar activeColumn="usefulness" order="asc" onSort={onSort} />);
      fireEvent.click(screen.getByRole('button', { name: /usefulness.*ascending/i }));
      fireEvent.click(screen.getByRole('button', { name: /usefulness.*ascending/i }));
      expect(onSort).toHaveBeenCalledTimes(2);
      expect(onSort).toHaveBeenNthCalledWith(1, 'usefulness', 'desc');
      expect(onSort).toHaveBeenNthCalledWith(2, 'usefulness', 'desc');
    });
  });
});
