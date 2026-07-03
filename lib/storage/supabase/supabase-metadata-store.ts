// stub — all methods filled in Task 9
import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore } from '@/lib/storage/metadata-store';

const NI = (): never => { throw new Error('not implemented — stub for Task 7; filled in Task 9'); };

export class SupabaseMetadataStore implements MetadataStore {
  constructor(_client: SupabaseClient) {}
  readIndex = NI as unknown as MetadataStore['readIndex'];
  setPlaylistMeta = NI as unknown as MetadataStore['setPlaylistMeta'];
  claimVideoSlot = NI as unknown as MetadataStore['claimVideoSlot'];
  upsertVideo = NI as unknown as MetadataStore['upsertVideo'];
  updateVideoFields = NI as unknown as MetadataStore['updateVideoFields'];
  bulkUpdateVideoFields = NI as unknown as MetadataStore['bulkUpdateVideoFields'];
  reconcilePlaylistMembership = NI as unknown as MetadataStore['reconcilePlaylistMembership'];
  deleteVideo = NI as unknown as MetadataStore['deleteVideo'];
}
