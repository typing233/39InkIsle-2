export interface Book {
  id: string;
  title: string;
  author: string | null;
  description: string | null;
  cover_path: string | null;
  file_format: 'epub' | 'pdf' | 'cbz';
  file_size: number | null;
  language: string | null;
  publisher: string | null;
  publish_date: string | null;
  isbn: string | null;
  page_count: number | null;
  avg_rating: number | null;
  rating_count: number;
  is_available: boolean;
  created_at: string;
  tags: Tag[];
}

export interface Tag {
  id: string;
  name: string;
}

export interface BookSearchParams {
  q?: string;
  q_fuzzy?: boolean;
  author?: string;
  tag?: string;
  tags?: string[];
  format?: string;
  series?: string;
  language?: string;
  rating_min?: number;
  rating_max?: number;
  publish_date_from?: string;
  publish_date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}
