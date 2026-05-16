# Implementation Plan

## Sub-Project 1 — Backend

### Task 1: Project Scaffold
**Output:** Working Next.js + TypeScript + Tailwind app

- `npx create-next-app@latest` with TypeScript + Tailwind + App Router
- Install dependencies: `@google/generative-ai`, `youtube-transcript`, `md-to-pdf`, `googleapis`
- Install dev dependencies: `jest`, `ts-jest`, `@testing-library/react`, `@playwright/test`
- Configure `jest.config.ts`, `tsconfig.json`
- Create `.env.local` with placeholder keys
- **Tests:** Jest config runs, `npm run dev` starts without error

---

### Task 2: Shared Types
**File:** `types/index.ts`

- Define `Ratings`, `Video`, `PlaylistIndex`, `ProgressEvent` interfaces
- Export all types
- **Tests:** Type-only — validated by TypeScript compiler, no runtime tests needed

---

### Task 3: Index Store
**File:** `lib/index-store.ts`

- `readIndex(outputFolder): PlaylistIndex` — read and parse `playlist-index.json`; return empty index if file missing
- `writeIndex(outputFolder, index): void` — atomic write (write to temp, rename)
- `upsertVideo(outputFolder, video): void` — add or replace video entry by ID
- `updateVideoFields(outputFolder, id, fields): void` — partial update of a video entry
- **Tests (TDD):** `tests/lib/index-store.test.ts`
  - Read returns empty index when file missing
  - Write + read round-trip preserves all fields
  - Upsert adds new video, replaces existing by ID
  - Partial update merges fields without losing others

---

### Task 4: YouTube Client
**File:** `lib/youtube.ts`

- `fetchPlaylistVideos(playlistUrl, apiKey): VideoMeta[]` — calls YouTube Data API v3 `playlistItems.list` + `videos.list`, returns id/title/url/durationSeconds
- `fetchTranscript(videoId): string` — calls `youtube-transcript`, returns full transcript text
- `detectLanguage(transcript: string): 'en' | 'ko'` — heuristic detection from transcript content
- **Tests (TDD):** `tests/lib/youtube.test.ts` — YouTube API mocked
  - Playlist fetch returns correct VideoMeta shape
  - Duration parsed from ISO 8601 (PT1H23M45S → 5025)
  - Language detection: Korean characters → 'ko', otherwise → 'en'
  - Transcript fetch failure throws with message

---

### Task 5: Gemini Client
**File:** `lib/gemini.ts`

- `generateSummary(transcript, language): Promise<{ summary: string; ratings: Ratings }>` — calls `gemini-2.5-flash`, prompt returns JSON
- `generateDeepDive(youtubeUrl, language): Promise<string>` — calls `gemini-2.5-pro` with YouTube URL via `fileData.fileUri`, ASCII art prompt
- All Gemini SDK calls contained here — Vertex AI swap = change this file only
- **Tests (TDD):** `tests/lib/gemini.test.ts` — Gemini SDK mocked
  - Summary returns valid Ratings shape with values 1–5
  - overallScore computed correctly as average
  - Deep-dive prompt includes language instruction
  - Error on invalid API key propagates with clear message

---

### Task 6: PDF Generator
**File:** `lib/pdf.ts`

- `generatePdf(mdContent: string, outputPath: string): Promise<void>` — wraps `md-to-pdf`, monospace font config for ASCII art
- **Tests (TDD):** `tests/lib/pdf.test.ts`
  - Output file exists and is non-zero bytes after call
  - Korean text renders without error

---

### Task 7: Archive Manager
**File:** `lib/archive.ts`

- `archiveVideo(outputFolder, videoId): Promise<void>` — move all `{videoId}.*` files to `archived/`, update index
- `unarchiveVideo(outputFolder, videoId): Promise<void>` — move back to root, update index
- **Tests (TDD):** `tests/lib/archive.test.ts`
  - Archive moves all related files (md, pdf, deep-dive md/pdf if present)
  - Unarchive restores files to root
  - Index updated correctly after both operations
  - No-op if file doesn't exist (no error thrown)

---

### Task 8: Ingestion Pipeline
**File:** `lib/pipeline.ts`

- `runIngestion(playlistUrl, outputFolder, onProgress): Promise<void>`
  1. `fetchPlaylistVideos` → video list
  2. For each: `fetchTranscript` → `detectLanguage` → `generateSummary` → write MD → `generatePdf` → `upsertVideo`
  3. Call `onProgress(event)` at each step
  4. Continue on per-video error, emit error event
- **Tests (TDD):** `tests/lib/pipeline.test.ts` — all lib deps mocked
  - Progress events emitted in correct sequence
  - Error on one video does not stop pipeline
  - Index contains all successfully processed videos
  - overallScore stored as average of 5 ratings

---

### Task 9: Deep-Dive Pipeline
**File:** `lib/deep-dive.ts`

- `runDeepDive(videoId, outputFolder, onProgress): Promise<void>`
  1. Read video from index
  2. `generateDeepDive(youtubeUrl, language)`
  3. Fallback to transcript-only on failure, log mode used
  4. Write `{videoId}-deep-dive.md` → `generatePdf` → `updateVideoFields`
  5. Call `onProgress(event)` throughout
- **Tests (TDD):** `tests/lib/deep-dive.test.ts` — all lib deps mocked
  - Progress events: start → step → done
  - Fallback triggered on Gemini URL failure
  - Index updated with deepDiveMd + deepDivePdf after success

---

### Task 10: API Routes
**Files:** `app/api/*/route.ts`

Implement all routes per design spec:
- `GET /api/videos` — read index, sort/filter by query params
- `POST /api/ingest` — validate body, start pipeline
- `GET /api/ingest/stream` — SSE stream
- `POST /api/videos/[id]/deep-dive` — trigger deep-dive
- `GET /api/videos/[id]/deep-dive/stream` — SSE stream
- `POST /api/videos/[id]/archive` — call archive/unarchive
- `GET /api/pdf/[id]` — serve PDF file with correct Content-Type
- `GET|POST /api/settings` — read/write outputFolder setting

- **Tests (TDD):** `tests/api/*.test.ts` — lib functions mocked
  - Sort: each column sorts correctly asc/desc
  - Archive toggle: action:'archive' calls archiveVideo, action:'unarchive' calls unarchiveVideo
  - PDF route returns 404 for missing file
  - Settings persist across GET/POST round-trip

---

## Sub-Project 2 — Frontend

### Task 1: Header Component
**File:** `components/Header.tsx`

- Playlist URL input, output folder input (defaulted from settings), Fetch & Summarize button
- Emits `onIngest(playlistUrl, outputFolder)` callback
- **Tests:** `tests/components/Header.test.tsx`
  - Button disabled when URL input is empty
  - Calls onIngest with correct values on submit

---

### Task 2: Sort Bar Component
**File:** `components/SortBar.tsx`

- Columns: Name | USE | DPT | ORI | RCN | CMP | OVR
- Active column highlighted with ↑↓ arrow
- Tooltip on hover shows full name
- Emits `onSort(column, order)` callback
- **Tests:** `tests/components/SortBar.test.tsx`
  - Click column → toggles order asc/desc
  - Active column highlighted

---

### Task 3: Video Menu Component
**Files:** `components/VideoRow.tsx`, `components/VideoMenu.tsx`

- Row: title, language badge, ratings display
- Menu: all 6 actions per design spec
- Deep Dive + Open Deep Dive + View Deep Dive PDF disabled when deepDiveMd is null
- Archive label switches based on `video.archived`
- Obsidian URI constructed correctly
- **Tests:** `tests/components/VideoRow.test.tsx`
  - Deep dive items disabled when no deep-dive file
  - Archive shows "Unarchive" for archived videos
  - Obsidian href contains correct vault + file params

---

### Task 4: Video List Component
**File:** `components/VideoList.tsx`

- Renders VideoRow per video
- Archived rows greyed when showArchive=true, hidden when false
- **Tests:** `tests/components/VideoList.test.tsx`
  - Archived rows hidden by default
  - Archived rows visible and greyed with showArchive=true

---

### Task 5: Deep Dive Overlay
**File:** `components/DeepDiveOverlay.tsx`

- Progress bar + step label fed by SSE stream
- Done state: ✓ message
- Error state: error message + Show Logs button → expandable log panel
- **Tests:** `tests/components/DeepDiveOverlay.test.tsx`
  - Progress bar advances with SSE events
  - Error state shows message and log button
  - Log panel expands on button click

---

### Task 6: Main Page Integration
**File:** `app/page.tsx`

- Wire Header → ingest SSE → refresh video list
- Wire sort bar → re-fetch with sort params
- Wire Show Archive checkbox
- Wire deep dive menu → open overlay → SSE stream
- Wire archive menu → POST → refresh list
- Wire Obsidian + PDF links
- **Tests:** Integration — mocked API routes

---

### Task 7: E2E Tests
**File:** `tests/e2e/playlist-viewer.spec.ts`

Playwright tests against dev server (API routes mocked):
- Paste playlist URL → click Fetch & Summarize → progress bar visible → video list populated
- Sort by OVR → list reorders
- ☰ → Deep Dive → overlay progress → done state
- ☰ → Archive → row greyed with Show Archive checked
- ☰ → View Summary PDF → new tab opens
- Obsidian link href contains correct obsidian:// scheme

---

## Review Process Per Task

After implementing each task:

```
1. Run tests  →  all pass
2. Claude code review  →  requesting-code-review skill
3. Codex adversarial review  →  openai/codex-plugin-cc
4. Address feedback
5. Mark task complete
```

After all tasks in a sub-project:

```
1. verification-before-completion skill
2. Step through design-spec.md verification checklist
3. finishing-a-development-branch skill  →  commit + PR
```
