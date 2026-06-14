import client from './client';

export interface CollectionData {
  id: string;
  name: string;
  collection_type: string;
  is_system: boolean;
  item_count: number;
  created_at: string;
}

export const collectionsApi = {
  list: () => client.get<CollectionData[]>('/collections'),

  create: (name: string) => client.post<CollectionData>('/collections', { name }),

  update: (id: string, name: string) => client.put<CollectionData>(`/collections/${id}`, { name }),

  delete: (id: string) => client.delete(`/collections/${id}`),

  getBooks: (id: string, page = 1) =>
    client.get(`/collections/${id}/books?page=${page}`),

  addBook: (collectionId: string, bookId: string, deviceId?: string) =>
    client.post(`/collections/${collectionId}/books/${bookId}${deviceId ? `?device_id=${deviceId}` : ''}`),

  removeBook: (collectionId: string, bookId: string) =>
    client.delete(`/collections/${collectionId}/books/${bookId}`),

  checkFavorite: (bookId: string) =>
    client.get<{ is_favorite: boolean }>(`/collections/favorites/check/${bookId}`),
};
