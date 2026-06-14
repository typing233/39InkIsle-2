import client from './client';
import { getDeviceId } from '@/lib/progressSync';

export interface CollectionData {
  id: string;
  name: string;
  collection_type: string;
  is_system: boolean;
  item_count: number;
  vector_clock: Record<string, number>;
  created_at: string;
}

export interface CollectionBookItem {
  id: string;
  book_id: string;
  position: number;
  added_at: string;
}

export interface SyncResponse {
  merged_book_ids: string[];
  vector_clock: Record<string, number>;
  conflicts_resolved: number;
}

export const collectionsApi = {
  list: () => client.get<CollectionData[]>('/collections'),

  create: (name: string) => client.post<CollectionData>('/collections', { name }),

  update: (id: string, name: string) => client.put<CollectionData>(`/collections/${id}`, { name }),

  delete: (id: string) => client.delete(`/collections/${id}`),

  getBooks: (id: string, page = 1, pageSize = 100) =>
    client.get<{ items: CollectionBookItem[]; total: number; page: number; page_size: number }>(
      `/collections/${id}/books?page=${page}&page_size=${pageSize}`
    ),

  addBook: (collectionId: string, bookId: string, deviceId?: string) =>
    client.post(`/collections/${collectionId}/books/${bookId}${deviceId ? `?device_id=${deviceId}` : ''}`),

  removeBook: (collectionId: string, bookId: string) =>
    client.delete(`/collections/${collectionId}/books/${bookId}`),

  checkFavorite: (bookId: string) =>
    client.get<{ is_favorite: boolean }>(`/collections/favorites/check/${bookId}`),

  sync: (collectionId: string, bookIds: string[], vectorClock: Record<string, number>) =>
    client.post<SyncResponse>('/collections/sync', {
      collection_id: collectionId,
      device_id: getDeviceId(),
      vector_clock: vectorClock,
      book_ids: bookIds,
    }),
};
