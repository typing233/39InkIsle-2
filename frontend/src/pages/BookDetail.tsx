import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { booksApi } from '@/api/books';
import { reviewsApi, ReviewData } from '@/api/reviews';
import { useAuthStore } from '@/store';
import { Book } from '@/types/book';
import { StarRating } from '@/components/books/StarRating';
import { EnrichmentPanel } from '@/components/books/EnrichmentPanel';
import { BookOpen } from 'lucide-react';
import toast from 'react-hot-toast';

export default function BookDetail() {
  const { bookId } = useParams<{ bookId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [book, setBook] = useState<Book | null>(null);
  const [reviews, setReviews] = useState<ReviewData[]>([]);
  const [totalReviews, setTotalReviews] = useState(0);
  const [myRating, setMyRating] = useState(0);
  const [myText, setMyText] = useState('');
  const [hasMyReview, setHasMyReview] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!bookId) return;
    booksApi.getById(bookId).then(({ data }) => setBook(data));
    loadReviews();
  }, [bookId]);

  const loadReviews = async () => {
    if (!bookId) return;
    const { data } = await reviewsApi.list(bookId);
    setReviews(data.items);
    setTotalReviews(data.total);
    const mine = data.items.find(r => r.user_id === user?.id);
    if (mine) {
      setMyRating(mine.rating);
      setMyText(mine.review_text || '');
      setHasMyReview(true);
    }
  };

  const handleSubmitReview = async () => {
    if (!bookId || myRating === 0) return;
    setSubmitting(true);
    try {
      if (hasMyReview) {
        await reviewsApi.update(bookId, { rating: myRating, review_text: myText || undefined });
        toast.success('Review updated');
      } else {
        await reviewsApi.create(bookId, { rating: myRating, review_text: myText || undefined });
        toast.success('Review submitted');
        setHasMyReview(true);
      }
      loadReviews();
    } catch {
      toast.error('Failed to submit review');
    }
    setSubmitting(false);
  };

  const handleDeleteReview = async () => {
    if (!bookId) return;
    try {
      await reviewsApi.delete(bookId);
      setMyRating(0);
      setMyText('');
      setHasMyReview(false);
      toast.success('Review deleted');
      loadReviews();
    } catch {
      toast.error('Failed to delete review');
    }
  };

  const openReader = () => {
    if (!book) return;
    if (book.file_format === 'epub') navigate(`/read/${book.id}`);
    else if (book.file_format === 'pdf') navigate(`/read/pdf/${book.id}`);
    else if (book.file_format === 'cbz') navigate(`/read/cbz/${book.id}`);
  };

  const reloadBook = () => {
    if (!bookId) return;
    booksApi.getById(bookId).then(({ data }) => setBook(data));
  };

  if (!book) return <div className="p-8 text-center text-gray-500">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-start gap-6">
        <div className="w-48 shrink-0">
          {book.cover_path ? (
            <img src={booksApi.getCoverUrl(book.id)} alt={book.title} className="w-full rounded-lg shadow-md" />
          ) : (
            <div className="w-full aspect-[2/3] bg-gray-200 rounded-lg flex items-center justify-center text-gray-400 text-2xl">
              {book.file_format.toUpperCase()}
            </div>
          )}
        </div>
        <div className="flex-1 space-y-3">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{book.title}</h1>
          {book.author && <p className="text-lg text-gray-600 dark:text-gray-300">{book.author}</p>}
          <div className="flex items-center gap-2">
            {book.avg_rating != null && (
              <>
                <StarRating rating={book.avg_rating} />
                <span className="text-sm text-gray-500">{book.avg_rating.toFixed(1)} ({book.rating_count})</span>
              </>
            )}
          </div>
          <div className="flex gap-2 text-sm text-gray-500">
            <span className="px-2 py-1 bg-gray-100 rounded">{book.file_format.toUpperCase()}</span>
            {book.language && <span className="px-2 py-1 bg-gray-100 rounded">{book.language}</span>}
            {book.page_count && <span className="px-2 py-1 bg-gray-100 rounded">{book.page_count} pages</span>}
          </div>
          {book.description && <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{book.description}</p>}
          <button onClick={openReader} className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2">
            <BookOpen size={18} /> Read
          </button>
        </div>
      </div>

      {/* My Review */}
      <div className="border-t pt-6">
        <h2 className="text-lg font-semibold mb-4">Your Rating</h2>
        <div className="space-y-3">
          <StarRating rating={myRating} size={24} interactive onChange={setMyRating} />
          <textarea
            value={myText}
            onChange={(e) => setMyText(e.target.value)}
            placeholder="Write a short review (optional)..."
            className="w-full px-3 py-2 border rounded-lg text-sm resize-none h-20 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSubmitReview}
              disabled={myRating === 0 || submitting}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {hasMyReview ? 'Update' : 'Submit'}
            </button>
            {hasMyReview && (
              <button onClick={handleDeleteReview} className="px-4 py-2 text-red-600 text-sm hover:bg-red-50 rounded-lg">
                Delete my review
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Reviews List */}
      <div className="border-t pt-6">
        <h2 className="text-lg font-semibold mb-4">Reviews ({totalReviews})</h2>
        {reviews.length === 0 ? (
          <p className="text-gray-500 text-sm">No reviews yet. Be the first!</p>
        ) : (
          <div className="space-y-4">
            {reviews.map((review) => (
              <div key={review.id} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{review.username || 'User'}</span>
                    <StarRating rating={review.rating} size={14} />
                  </div>
                  <span className="text-xs text-gray-400">{new Date(review.created_at).toLocaleDateString()}</span>
                </div>
                {review.review_text && (
                  <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">{review.review_text}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      {/* Admin: Metadata Enrichment & Calibration */}
      {user?.role === 'admin' && (
        <EnrichmentPanel bookId={book.id} onMetadataUpdated={reloadBook} />
      )}
    </div>
  );
}
