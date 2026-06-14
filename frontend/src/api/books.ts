import client from './client';
import { Book, BookSearchParams } from '@/types/book';

export const booksApi = {
  search: (params: BookSearchParams) =>
    client.get<Book[]>('/books', { params }),

  getById: (id: string) => client.get<Book>(`/books/${id}`),

  getCoverUrl: (id: string) => `/api/v1/books/${id}/cover`,

  getFileUrl: (id: string) => `/api/v1/books/${id}/file`,

  delete: (id: string) => client.delete(`/books/${id}`),

  getTags: () => client.get('/books/tags/all'),

  addTag: (bookId: string, tagId: string) =>
    client.post(`/books/${bookId}/tags/${tagId}`),

  removeTag: (bookId: string, tagId: string) =>
    client.delete(`/books/${bookId}/tags/${tagId}`),
};
