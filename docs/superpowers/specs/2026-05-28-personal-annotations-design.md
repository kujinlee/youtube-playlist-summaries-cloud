# Personal Annotations Design

**Date:** 2026-05-28
**Status:** Approved

## Problem

The app displays AI-generated ratings and scores for each video, but has no way to capture the user's own judgment about a video's value. The user wants to mark videos with a personal usefulness score and leave brief notes, then filter the list to concentrate on high-value material and skip low-value material.

## Solution

Add two optional personal annotation fields to each video — a 1–5 personal score and a free-text note — stored in `playlist-index.json` alongside existing fields. Expose them as a `My Score` star-rating column and a `Note` column in the video table, and add a `My score ≥` filter to the filter bar.

## Data Model

### `VideoSchema` additions (`types/index.ts`)

```ts
personalScore: z.number().int().min(1).max(5).optional(),
personalNote:  z.string().optional(),
```

Both fields are optional. Existing videos in any index file need no migration — they simply have no personal annotation.

### `FilterState` addition (`types/index.ts`)

```ts
minPersonalScore: number  // 0 = no filter; 1–5 = minimum personal score required
```

`FILTER_DEFAULTS` sets `minPersonalScore: 0`.

### `SortColumn` addition (`types/index.ts`)

```ts
'personalScore'  // added to the union
```

## API Route

**`POST /api/videos/[id]/annotation`**

| Field | Type | Required |
|---|---|---|
| `outputFolder` | `string` | yes |
| `personalScore` | `1 \| 2 \| 3 \| 4 \| 5 \| null` | no |
| `personalNote` | `string` | no |

- `personalScore: null` clears the score (sets it to unscored)
- `personalScore` absent → score field not touched
- `personalNote` absent → note field not touched
- Uses existing `assertOutputFolder` + `assertVideoId` guards
- Calls `updateVideoFields(outputFolder, videoId, fields)` — atomic index write
- Returns `{ ok: true }`

The client sends only the field(s) being updated. Score-only and note-only calls are both valid.

## UI Components

### `StarRating` (`components/StarRating.tsx`)

Renders 5 star icons (★ filled / ☆ empty) up to `personalScore`.

- Click a star → sets `personalScore` to that number; fires `POST /api/videos/[id]/annotation`
- Click the currently-selected star → clears score (sets to unscored); fires API with `personalScore: null`
- Optimistic update: local state updates immediately; API fires in background
- Hover preview: stars up to hovered index light up before click

Props:
```ts
interface StarRatingProps {
  videoId: string;
  outputFolder: string;
  value: number | undefined;          // current personalScore
  onChange: (score: number | undefined) => void;  // optimistic update callback
}
```

### `NoteCell` (`components/NoteCell.tsx`)

Renders in the `Note` table column.

- **No note:** displays `—`
- **Has note:** displays first 40 characters followed by `…` if truncated
- **Click anywhere on cell:** opens an absolutely-positioned popover containing:
  - `<textarea>` pre-filled with current note (empty if none)
  - **Save** button → calls `POST /api/videos/[id]/annotation` with `personalNote`, closes popover
  - **Cancel** button → discards changes, closes popover
  - **Escape key** → same as Cancel
  - **Outside click** → same as Cancel (backdrop div, same pattern as VideoMenu)

Props:
```ts
interface NoteCellProps {
  videoId: string;
  outputFolder: string;
  value: string | undefined;          // current personalNote
  onChange: (note: string) => void;   // optimistic update callback
}
```

### `VideoRow` changes (`components/VideoRow.tsx`)

Two new `<td>` cells added after the existing rating columns:

1. `My Score` cell — renders `<StarRating>`
2. `Note` cell — renders `<NoteCell>`

**Dimming rule:** when `minPersonalScore > 0` and `video.personalScore` is undefined, add `opacity-50` to all data cells (in addition to the existing `archived` opacity logic). This is separate from the `archived` dim — a video can be both unscored-dim and archived-dim simultaneously.

### `VideoList` changes (`components/VideoList.tsx`)

Two new `<th>` column headers added:
- `My Score` — sortable (click cycles asc/desc, same pattern as existing rating headers)
- `Note` — not sortable (free text, no meaningful sort)

### `FilterBar` changes (`components/FilterBar.tsx`)

New dropdown added after the existing `Score` dropdown:

```
My score ≥  [All ▾]
```

Options: `All` (value `0`) / `1+` / `2+` / `3+` / `4+` / `5`

### `app/page.tsx` changes

New filter applied in `filteredVideos` chain:

```ts
.filter((v) => {
  if (filters.minPersonalScore === 0) return true;
  // unscored videos pass through (shown dimmed, not hidden)
  if (v.personalScore === undefined) return true;
  return v.personalScore >= filters.minPersonalScore;
})
```

Dimming prop: `VideoRow` receives `dimUnscored: boolean` (true when `minPersonalScore > 0` and `video.personalScore === undefined`).

### `app/api/videos/route.ts` changes

New sort case for `personalScore`:

```ts
case 'personalScore':
  // nulls always last regardless of sort direction
  if (a.personalScore === undefined) return 1;
  if (b.personalScore === undefined) return -1;
  return dir * (a.personalScore - b.personalScore);
```

## URL Contracts

| Component | Link text | Full URL |
|---|---|---|
| StarRating | (API call, not a link) | `POST /api/videos/{id}/annotation` body: `{ outputFolder, personalScore }` |
| NoteCell | (API call, not a link) | `POST /api/videos/{id}/annotation` body: `{ outputFolder, personalNote }` |

## Overlay Dismissal

| Component | Mechanism | Expected result |
|---|---|---|
| NoteCell popover | Cancel button | Discards textarea changes, closes popover |
| NoteCell popover | Save button | Saves note via API, closes popover |
| NoteCell popover | Escape key | Same as Cancel |
| NoteCell popover | Outside click (backdrop) | Same as Cancel |

## Sorting

| Column | Null/undefined behaviour |
|---|---|
| `personalScore` asc | Unscored videos sort last |
| `personalScore` desc | Unscored videos sort last |

## Filtering

| `minPersonalScore` | `personalScore` present | Result |
|---|---|---|
| 0 | any | Shown normally |
| > 0 | `>= minPersonalScore` | Shown normally |
| > 0 | `< minPersonalScore` | Hidden |
| > 0 | undefined (unscored) | Shown, but cells dimmed (opacity-50) |

## Backward Compatibility

- Existing `playlist-index.json` files need no changes — both fields are optional in the Zod schema
- Re-syncing a playlist preserves `personalScore` and `personalNote` because `reconstructVideo` carries all existing fields forward via the index merge in `runIngestion`

## Out of Scope

- Bulk annotation (setting score/note for multiple videos at once)
- Exporting annotations
- Sharing annotations across devices
- Integration of personal score into the `overallScore` calculation (overallScore remains AI-only)

## Files Changed

| File | Change |
|---|---|
| `types/index.ts` | Add `personalScore`, `personalNote` to `VideoSchema`; add `minPersonalScore` to `FilterState`; add `'personalScore'` to `SortColumn` |
| `app/api/videos/[id]/annotation/route.ts` | New — POST annotation handler |
| `components/StarRating.tsx` | New — 5-star click widget |
| `components/NoteCell.tsx` | New — truncated preview + edit popover |
| `components/VideoRow.tsx` | Add My Score + Note columns; dimming logic |
| `components/VideoList.tsx` | Add My Score + Note column headers |
| `components/FilterBar.tsx` | Add My score ≥ dropdown |
| `app/api/videos/route.ts` | Add `personalScore` sort case (nulls last) |
| `app/page.tsx` | Add `minPersonalScore` filter + `dimUnscored` prop |

## Testing

### `tests/components/StarRating.test.tsx` (new)

| Test | Covers |
|---|---|
| Renders 5 stars, filled up to value | Display |
| Click star N sets score to N | Score set |
| Click active star clears score | Score clear |
| Hover preview lights up stars | Hover state |
| Calls `onChange` with new value on click | Callback |

### `tests/components/NoteCell.test.tsx` (new)

| Test | Covers |
|---|---|
| Shows `—` when note is undefined | Empty state |
| Shows truncated text when note is long | Truncation |
| Click opens popover with textarea | Popover open |
| Cancel closes popover without saving | Cancel |
| Escape closes popover without saving | Escape dismissal |
| Outside click closes popover | Backdrop dismissal |
| Save calls onChange and closes popover | Save |

### `tests/components/VideoRow.test.tsx` (update)

| Test | Change |
|---|---|
| Renders My Score stars | New |
| Renders Note cell | New |
| Applies opacity-50 to cells when unscored and minPersonalScore active | New |

### `tests/api/annotation.test.ts` (new)

| Test | Covers |
|---|---|
| POST with valid score saves to index | Happy path |
| POST with valid note saves to index | Happy path |
| POST with both score and note saves both | Both fields |
| POST with neither field returns 400 | Validation |
| POST with invalid score (0, 6) returns 400 | Validation |
| POST with missing outputFolder returns 400 | Validation |
