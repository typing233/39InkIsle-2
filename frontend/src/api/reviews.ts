import client from './client';

export interface ReviewData {
  id: string;
  user_id: string;
  book_id: string;
  rating: number;
  review_text: string | null;
  is_visible: boolean;
  username: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedReviews {
  items: ReviewData[];
  total: number;
  page: number;
  page_size: number;
}

export const reviewsApi = {
  list: (bookId: string, page = 1) =>
    client.get<PaginatedReviews>(`/reviews/${bookId}?page=${page}`),

  create: (bookId: string, data: { rating: number; review_text?: string }) =>
    client.post<ReviewData>(`/reviews/${bookId}`, data),

  update: (bookId: string, data: { rating?: number; review_text?: string }) =>
    client.put<ReviewData>(`/reviews/${bookId}`, data),

  delete: (bookId: string) =>
    client.delete(`/reviews/${bookId}`),

  adminDelete: (bookId: string, reviewId: string) =>
    client.delete(`/reviews/${bookId}/${reviewId}`),

  myReviews: () =>
    client.get<ReviewData[]>('/reviews/my/all'),
};
