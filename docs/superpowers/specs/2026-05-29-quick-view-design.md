# Design Spec: Video Quick-View (TL;DR + Takeaways + Concepts)

**Date:** 2026-05-29  
**Status:** Approved

---

## Problem

Video summaries are generated as 3–6 prose H2 sections viewed only via Obsidian or PDF.
Users experience a "wall of text" and cannot quickly grasp what a video is about without reading the full summary.

## Goal

Add a **Quick Reference** layer surfaced in two places:

1. **Obsidian** — an `[!summary]` callout block at the top of every new `.md` file
2. **Browser** — an expandable inline row card in the video list table

The card contains: **TL;DR** (1 sentence) · **Key Takeaways** (3–5 bullets) · **Concepts** (existing `tags[]` as pills)

---

## Approach

**Approach 1 — Gemini at ingest + lazy backfill**

- New videos: `tldr` + `takeaways` generated at ingest time, stored in `playlist-index.json`, embedded in `.md`
- Existing videos: first row-expand triggers `GET /api/videos/[id]/quick-view` → Gemini extracts from `.md` → cached in index
- Zero latency for new videos; ~2s on first expand for old videos (instant thereafter)

---

## Data Model

**File:** `types/index.ts` — `Video` interface

```typescript
tldr?: string        // 1-sentence description, ≤25 words
takeaways?: string[] // 3–5 learnable insights, each ≤20 words
```

`tags[]` (already exists) is reused for the "Concepts" pills — no new field.

---

## Gemini Prompt Changes

**File:** `lib/gemini.ts`

### `generateSummary()` — additional JSON response fields

```json
{
  "tldr": "One sentence (≤25 words) describing the core idea of this video.",
  "takeaways": [
    "Learnable insight 1 (≤20 words)",
    "Learnable insight 2",
    "Learnable insight 3"
  ]
}
```

Prompt constraints:
- `tldr`: single sentence, ≤25 words, phrased as "This video teaches/shows/demonstrates X"
- `takeaways`: 3–5 items; each is a concrete learnable insight or action — not a topic label

### New function: `extractQuickView(summaryMarkdown: string)`

Used for the backfill path. Sends the existing `.md` body to Gemini with an extraction-only prompt
asking for `{ tldr, takeaways }` in the same JSON shape. No ratings or classification needed.

---

## Markdown Template (Obsidian)

**File:** `lib/pipeline.ts`

Insert a Quick Reference callout block between the metadata line and the first `---` divider:

```markdown
# Video Title

**Channel:** … | **Duration:** … | **URL:** …

> [!summary] Quick Reference
> **TL;DR:** One sentence description of the video.
>
> **Key Takeaways:**
> - First learnable point
> - Second learnable point
> - Third learnable point
>
> **Concepts:** concept1 · concept2 · concept3

---

## 1. First Section
…
```

- `> [!summary]` is an Obsidian callout — renders as a styled card
- Concepts line: `tags[]` joined with ` · `
- Only new summaries get this block; existing `.md` files are NOT modified

---

## New API Endpoint

**File:** `app/api/videos/[id]/quick-view/route.ts`

### `GET /api/videos/[id]/quick-view?outputFolder=<path>`

| Step | Condition | Action |
|------|-----------|--------|
| 1 | Video not found | 404 |
| 2 | `tldr` present in index | Return `{ tldr, takeaways, tags }` immediately |
| 3 | `tldr` absent, `summaryMd` null | 404 (no summary file to extract from) |
| 4 | `tldr` absent, `summaryMd` present | Read `.md` → call `extractQuickView()` → write `{ tldr, takeaways }` to index → return `{ tldr, takeaways, tags }` |
| 5 | Gemini fails | 500 with error message |

---

## Browser UI

### New Component: `components/VideoQuickView.tsx`

**Props:**
```typescript
interface VideoQuickViewProps {
  videoId: string
  tldr?: string        // pre-loaded from index if available
  takeaways?: string[]
  tags?: string[]
  outputFolder: string
  colSpan: number      // spans all table columns
}
```

**Render states:**

| State | Trigger | Display |
|-------|---------|---------|
| Instant | `tldr` prop provided | Card immediately |
| Loading | `tldr` absent, fetch pending | Spinner row spanning all columns |
| Error | fetch failed | "Could not generate quick view" + Retry button |
| Success | fetch complete | Card |

**Card layout:**
```
┌──────────────────────────────────────────────────────────┐
│  TL;DR: One sentence about what this video teaches.      │
│                                                          │
│  Key Takeaways                                           │
│  • First learnable point from this video                 │
│  • Second learnable point                                │
│  • Third learnable point                                 │
│                                                          │
│  Concepts:  [tag1]  [tag2]  [tag3]  [tag4]              │
└──────────────────────────────────────────────────────────┘
```

Uses existing `Badge` component for concept pills.
Fetches `GET /api/videos/[id]/quick-view?outputFolder=...` when `tldr` is absent.

---

### Updated Component: `components/VideoRow.tsx`

Changes:
- New leftmost cell: `▶` (collapsed) / `▼` (expanded) chevron button
- Local `useState<boolean>(false)` for `isExpanded` — per-row, not lifted
- Click chevron **or** click title → toggle `isExpanded`
- When `isExpanded`: render `<VideoQuickView>` in a `<tr>` beneath the data row

---

## URL Contracts

| Component | Endpoint | Full URL |
|-----------|----------|---------|
| `VideoQuickView` (fetch path) | `GET /api/videos/[id]/quick-view` | `/api/videos/[id]/quick-view?outputFolder=<path>` |

---

## Expansion / Dismissal

| Component | Mechanism | Expected result |
|-----------|-----------|-----------------|
| `VideoRow` expanded | Click chevron (`▼→▶`) | Row collapses, `VideoQuickView` unmounts |
| `VideoRow` expanded | Click title cell | Row collapses, `VideoQuickView` unmounts |

---

## Files to Create / Modify

| File | Action |
|------|--------|
| `types/index.ts` | Add `tldr?`, `takeaways?` to `Video` |
| `lib/gemini.ts` | Add fields to `generateSummary` schema; add `extractQuickView()` |
| `lib/pipeline.ts` | Embed Quick Reference callout in `.md` template |
| `app/api/videos/[id]/quick-view/route.ts` | Create backfill endpoint |
| `components/VideoQuickView.tsx` | Create quick-view card component |
| `components/VideoRow.tsx` | Add chevron, expand state, render `VideoQuickView` |

---

## Testing

### Unit
- `lib/gemini.ts` — `extractQuickView()`: mock Gemini call, assert `{ tldr: string, takeaways: string[] }` shape
- `lib/pipeline.ts` — markdown builder: assert Quick Reference callout present when `tldr`/`takeaways` provided; absent when missing

### Component
- `VideoQuickView`: instant render, loading state, error+retry state
- `VideoRow`: chevron renders; click toggles expand; click title toggles expand; pre-loaded data renders without fetch

### E2E
- Expand row with pre-loaded `tldr` → card appears immediately
- Expand row without `tldr` → loading → card appears (mock API)
- Collapse: expand → click chevron → card disappears

---

## Backward Compatibility

- Existing `.md` files: **not modified** — only new summaries get the callout block
- Backfill writes only to the index, not to existing `.md` files
- Videos without a `summaryMd` file: quick-view endpoint returns 404; row shows error state
