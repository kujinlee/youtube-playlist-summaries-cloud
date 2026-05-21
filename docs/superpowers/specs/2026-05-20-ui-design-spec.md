# UI Design Spec — YouTube Playlist Viewer

**Date:** 2026-05-20  
**Status:** Approved

---

## Overview

Full UI design pass on the existing bare-HTML frontend. Adds Tailwind CSS styling and two new Gemini-classified fields (`videoType`, `audience`) with colored badges in the video table.

---

## Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Color theme | Dark (`zinc-950` base) | Data-heavy tool; suits extended use |
| List layout | Dense table | Many videos, scan-optimized |
| Accent color | Blue (`blue-500/600`) | Neutral, professional |
| Layout structure | Stack (single column) | Matches existing component flow |

---

## Wireframe

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║  HEADER (bg-zinc-900, border-b border-zinc-800, px-6 py-4)                         ║
║  ┌──────────────────────────────────────┐ ┌─────────────────┐ ┌────────────────┐   ║
║  │ https://youtube.com/playlist?list=… │ │ ~/data/output   │ │ Fetch & Summ.. │   ║
║  └──────────────────────────────────────┘ └─────────────────┘ └────────────────┘   ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║  INGEST PROGRESS (conditional — only when running, bg-zinc-900 px-6 py-3)          ║
║  ██████████████████░░░░░░░░░░░  63%  Generating summary: "Video title…"            ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║  STATS BAR (px-6 py-4, bg-zinc-950)                                                ║
║  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                    ║
║  │  134            │  │  4.13           │  │  37             │                    ║
║  │  Total videos   │  │  Avg score      │  │  Korean         │                    ║
║  └─────────────────┘  └─────────────────┘  └─────────────────┘                    ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║  CONTROLS ROW (px-6 py-2, border-b border-zinc-800)                                ║
║  [Name ↑] [USE] [DPT] [ORI] [RCN] [CMP] [OVR]              [☐ Show Archive]       ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║  VIDEO TABLE                                                                        ║
║   #  Title                                      Lang    Type          Audience     USE DPT ORI RCN CMP OVR ║
║  ─────────────────────────────────────────────────────────────────────────────────║
║   1  How DPT, Claude and Gemini are trained… ☰  [EN]  [Analysis]    [Advanced]      5   5   4   5   5  4.8 ║
║   2  Deep Dive into LMs like ChatGPT… ☰         [KO]  [Tutorial]    [Intermediate]  4   5   3   4   5  4.2 ║
║   3  Build Self-Improving Code Skills… ☰        [EN]  [Framework]   [Advanced]      5   4   4   4   4  4.2 ║
║   4  (archived, opacity-40) ☰                   [EN]  [Case Study]  [Beginner]      3   3   3   3   3  3.0 ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

DEEP DIVE OVERLAY (fixed inset backdrop, centered modal)
  ┌────────────────────────────────────────────┐
  │  Deep Dive  "Video Title"              [✕] │
  │  ─────────────────────────────────────────│
  │  ████████████████░░░░░░░  65%              │
  │  Generating analysis…                      │
  │                                            │
  │  (on error) ⚠ Error message   [Show logs] │
  └────────────────────────────────────────────┘
```

---

## Design Tokens

### Colors

| Role | Tailwind class |
|---|---|
| Page background | `bg-zinc-950` |
| Surface (header, overlay, cards) | `bg-zinc-900` |
| Border | `border-zinc-800` |
| Text primary | `text-zinc-50` |
| Text secondary | `text-zinc-400` |
| Accent (button, active sort, progress) | `bg-blue-600` / `text-blue-400` |
| Hover state | `hover:bg-zinc-800` |
| Archived row | `opacity-40` |

### Language badges

| Badge | Class |
|---|---|
| `[EN]` | `bg-blue-700 text-white` |
| `[KO]` | `bg-violet-700 text-white` |

### Type badges

| Badge | Class |
|---|---|
| `[Tutorial]` | `bg-green-700 text-white` |
| `[Analysis]` | `bg-sky-700 text-white` |
| `[Case Study]` | `bg-amber-700 text-white` |
| `[Framework]` | `bg-purple-700 text-white` |
| `[Demo]` | `bg-teal-700 text-white` |
| `[Interview]` | `bg-orange-700 text-white` |

### Audience badges

| Badge | Class |
|---|---|
| `[Beginner]` | `bg-green-700 text-white` |
| `[Intermediate]` | `bg-yellow-700 text-white` |
| `[Advanced]` | `bg-red-700 text-white` |

### Typography

| Role | Class |
|---|---|
| Rating numbers | `font-mono tabular-nums text-sm` |
| Row number | `text-zinc-500 text-sm` |
| Table header | `text-xs font-medium text-zinc-400 uppercase` |
| Body text | `text-sm text-zinc-200` |

---

## New Fields

### VideoType enum

```
"Tutorial" | "Analysis" | "Case Study" | "Framework" | "Demo" | "Interview"
```

### Audience enum

```
"Beginner" | "Intermediate" | "Advanced"
```

### Schema impact

- `types/index.ts`: Add `VideoTypeSchema` and `AudienceSchema` (Zod enums); extend `VideoSchema` with both fields as **`.optional()`** — backward compatible with existing `playlist-index.json` entries that were processed before this change
- `lib/gemini.ts`: Extend `generateSummary` prompt + response parsing; fields optional in `GeminiSummaryResponse` (Gemini may omit on rare failure)
- `lib/pipeline.ts`: Pass `videoType` + `audience` through to `upsertVideo` when present
- Test fixtures for `Video` objects do **not** need new fields (optional) — but new tests should exercise the fields when present

---

## Stats Bar

Computed client-side from `videos` state in `app/page.tsx`. No API change.

| Metric | Computation |
|---|---|
| Total videos | `videos.length` |
| Avg score | `mean(videos.map(v => v.overallScore))`, rounded to 2 dp |
| Korean | `videos.filter(v => v.language === 'ko').length` |

---

## Menu Button Placement

`☰` sits immediately after the title text (inline), before the badge columns. Clicking opens the contextual menu (Deep Dive, Archive, PDF, Obsidian).

---

## Out of Scope

- Text search / filter dropdowns (follow-on task)
- Sort by videoType or audience
- Any changes to API route query params
