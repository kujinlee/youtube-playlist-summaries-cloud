'use client';

import { useState } from 'react';
import type { FilterState } from '@/types';

interface FilterBarProps {
  filters: FilterState;
  onChange: (patch: Partial<FilterState>) => void;
  backfillCount?: number;
  onBackfill?: () => void;
}

const SELECT_CLASS =
  'rounded bg-zinc-800 border border-zinc-700 px-2 py-1.5 text-xs text-zinc-300 ' +
  'focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer';

export default function FilterBar({ filters, onChange, backfillCount = 0, onBackfill }: FilterBarProps) {
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const showBanner = backfillCount > 0 && !bannerDismissed;

  return (
    <div className="space-y-2">
      {showBanner && (
        <div className="flex items-center gap-2 rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300">
          <span>⚡ {backfillCount} video{backfillCount !== 1 ? 's' : ''} missing Quick Reference.</span>
          <button
            type="button"
            onClick={onBackfill}
            className="font-medium text-blue-400 hover:text-blue-300 underline"
            aria-label="Generate all"
          >
            Generate all
          </button>
          <button
            type="button"
            onClick={() => setBannerDismissed(true)}
            className="ml-auto text-zinc-500 hover:text-zinc-200"
            aria-label="Dismiss backfill"
          >
            ✕
          </button>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          placeholder="Search title or channel…"
          value={filters.searchText}
          onChange={(e) => onChange({ searchText: e.target.value })}
          className="rounded bg-zinc-800 border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
        />
        <select
          aria-label="Language"
          value={filters.language}
          onChange={(e) => onChange({ language: e.target.value as FilterState['language'] })}
          className={SELECT_CLASS}
        >
          <option value="all">All languages</option>
          <option value="en">EN</option>
          <option value="ko">KO</option>
        </select>
        <select
          aria-label="Type"
          value={filters.videoType}
          onChange={(e) => onChange({ videoType: e.target.value as FilterState['videoType'] })}
          className={SELECT_CLASS}
        >
          <option value="all">All types</option>
          <option value="Tutorial">Tutorial</option>
          <option value="Analysis">Analysis</option>
          <option value="Case Study">Case Study</option>
          <option value="Framework">Framework</option>
          <option value="Demo">Demo</option>
          <option value="Interview">Interview</option>
        </select>
        <select
          aria-label="Audience"
          value={filters.audience}
          onChange={(e) => onChange({ audience: e.target.value as FilterState['audience'] })}
          className={SELECT_CLASS}
        >
          <option value="all">All audiences</option>
          <option value="Beginner">Beginner</option>
          <option value="Intermediate">Intermediate</option>
          <option value="Advanced">Advanced</option>
        </select>
        <select
          aria-label="AI score ≥"
          value={String(filters.minScore)}
          onChange={(e) => onChange({ minScore: parseFloat(e.target.value) })}
          className={SELECT_CLASS}
        >
          <option value="0">All scores</option>
          <option value="3.5">3.5+</option>
          <option value="4">4.0+</option>
          <option value="4.5">4.5+</option>
        </select>
        <select
          aria-label="My score ≥"
          value={String(filters.minPersonalScore)}
          onChange={(e) => onChange({ minPersonalScore: parseInt(e.target.value, 10) })}
          className={SELECT_CLASS}
        >
          <option value="0">All</option>
          <option value="1">1+</option>
          <option value="2">2+</option>
          <option value="3">3+</option>
          <option value="4">4+</option>
          <option value="5">5</option>
        </select>
      </div>
    </div>
  );
}
