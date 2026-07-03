/** Identifies whose data a storage operation targets, and which index.
 *  `id`: local = the fixed sentinel; cloud = the owner user id (auth.uid()).
 *  `indexKey`: the index selector — local = the on-disk data root (path);
 *  cloud = the playlist key (e.g. the YouTube list-id) selecting one index. */
export interface Principal {
  readonly id: string;
  readonly indexKey: string;   // local: on-disk data root; cloud: playlist_key (YouTube list-id)
}

export const LOCAL_PRINCIPAL_ID = 'local';

export function localPrincipal(indexKey: string): Principal {
  return { id: LOCAL_PRINCIPAL_ID, indexKey };
}
