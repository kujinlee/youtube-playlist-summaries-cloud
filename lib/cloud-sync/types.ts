import type { Video } from '@/types';

/** The generated-content (Class A) signals for one video on one replica (§5.1). */
export interface ClassASignals {
  summaryMdKey: string | null;    // the blob KEY (video.summaryMd) — NOT the body
  mdHash: string | null;          // SHA-256 of the MD BODY (read from the blob by the caller); null when no MD
  docVersionMajor: number;        // 1 when docVersion absent (pre-feature)
  mdGeneratedAt: string | null;   // tie-break only
  mdCorrectionsHash: string | null;
  backfilled: boolean;            // mdGeneratedAt is provisional (§5.5)
}

/** The companion scalars carried verbatim with a winning MD (§4.1). */
export type CompanionScalars = Pick<
  Video,
  'ratings' | 'overallScore' | 'videoType' | 'audience' | 'tags' | 'tldr' | 'takeaways'
>;

export type HumanField = 'personalNote' | 'personalScore' | 'corrections';

/** One human field's (value, per-field timestamp) state (§5.4). Absence-as-value: value===undefined is a clear. */
export interface FieldState<T = string | number> {
  value: T | undefined;
  editedAt: string | undefined;   // per-field annotationsEditedAt
  backfilled: boolean;            // editedAt is provisional (§5.5)
}

export type HumanSnapshot = Record<HumanField, FieldState<string | number>>;

/** Manifest baseline for one video (§8). */
export interface VideoBaseline {
  classA: { docVersionMajor: number; mdGeneratedAt: string | null; mdCorrectionsHash: string | null; mdHash: string | null };
  classB: Record<HumanField, { value: string | number | undefined; editedAt: string | undefined }>;
}
