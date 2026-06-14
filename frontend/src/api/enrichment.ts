import client from './client';

export interface EnrichmentCandidate {
  title?: string;
  authors?: string[];
  description?: string;
  publisher?: string;
  language?: string;
  isbn_13?: string;
  isbn_10?: string;
  published_date?: string;
  external_id?: string;
  thumbnail?: string;
}

export interface EnrichmentCandidatesResponse {
  google_books: EnrichmentCandidate[];
  comicvine: EnrichmentCandidate[];
}

export const enrichmentApi = {
  getCandidates: (bookId: string) =>
    client.get<EnrichmentCandidatesResponse>(`/enrichment/${bookId}/candidates`),

  apply: (bookId: string, provider: string, candidateData: EnrichmentCandidate) =>
    client.post(`/enrichment/${bookId}/apply`, {
      provider,
      candidate_data: candidateData,
    }),

  getMetadata: (bookId: string) =>
    client.get(`/books/${bookId}/metadata`),

  calibrate: (bookId: string, data: Record<string, string>) =>
    client.patch(`/books/${bookId}/metadata`, data),
};
