export interface Ratings {
  usefulness: number;
  depth: number;
  originality: number;
  recency: number;
  completeness: number;
}

export interface Video {
  id: string;
  title: string;
  youtubeUrl: string;
  language: 'en' | 'ko';
  durationSeconds: number;
  archived: boolean;
  ratings: Ratings;
  overallScore: number;
  summaryMd: string | null;
  summaryPdf: string | null;
  deepDiveMd: string | null;
  deepDivePdf: string | null;
  processedAt: string;
}

export interface PlaylistIndex {
  playlistUrl: string;
  outputFolder: string;
  videos: Video[];
}

export type ProgressEventType = 'start' | 'step' | 'done' | 'error';

export interface ProgressEvent {
  type: ProgressEventType;
  videoId?: string;
  title?: string;
  step?: string;
  current?: number;
  total?: number;
  log?: string;
}

export type SortColumn =
  | 'name'
  | 'overall'
  | 'usefulness'
  | 'depth'
  | 'originality'
  | 'recency'
  | 'completeness';

export type SortOrder = 'asc' | 'desc';
