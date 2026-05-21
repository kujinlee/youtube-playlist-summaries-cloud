'use client';

import type { SortColumn, SortOrder } from '@/types';

interface SortBarProps {
  activeColumn: SortColumn | null;
  order: SortOrder;
  onSort: (column: SortColumn, order: SortOrder) => void;
}

export const COLUMNS: { label: string; column: SortColumn; fullName: string }[] = [
  { label: 'Name', column: 'name', fullName: 'Name' },
  { label: 'USE', column: 'usefulness', fullName: 'Usefulness' },
  { label: 'DPT', column: 'depth', fullName: 'Depth' },
  { label: 'ORI', column: 'originality', fullName: 'Originality' },
  { label: 'RCN', column: 'recency', fullName: 'Recency' },
  { label: 'CMP', column: 'completeness', fullName: 'Completeness' },
  { label: 'OVR', column: 'overall', fullName: 'Overall' },
];

export default function SortBar({ activeColumn, order, onSort }: SortBarProps) {
  function handleClick(column: SortColumn) {
    // Controlled component: nextOrder is computed from current props.
    // Rapid double-clicks before parent rerenders will both emit the same direction.
    const nextOrder: SortOrder =
      column === activeColumn && order === 'asc' ? 'desc' : 'asc';
    onSort(column, nextOrder);
  }

  return (
    <nav aria-label="Sort columns" className="flex flex-wrap gap-1">
      {COLUMNS.map(({ label, column, fullName }) => {
        const isActive = column === activeColumn;
        const arrow = isActive ? (order === 'asc' ? '↑' : '↓') : '';
        const directionLabel = isActive
          ? `, sorted ${order === 'asc' ? 'ascending' : 'descending'}`
          : '';
        return (
          <button
            key={column}
            type="button"
            title={fullName}
            aria-label={`${fullName}${directionLabel}`}
            aria-pressed={isActive}
            onClick={() => handleClick(column)}
            className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
              isActive
                ? 'bg-blue-600 text-white'
                : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'
            }`}
          >
            {label}
            {arrow && <span aria-hidden="true"> {arrow}</span>}
          </button>
        );
      })}
    </nav>
  );
}
