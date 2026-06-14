import { Book } from '@/types/book';
import { useNavigate } from 'react-router-dom';
import { booksApi } from '@/api/books';

interface Props {
  book: Book;
}

export function BookCard({ book }: Props) {
  const navigate = useNavigate();

  const handleClick = () => {
    if (book.file_format === 'epub') {
      navigate(`/read/${book.id}`);
    }
  };

  return (
    <div
      onClick={handleClick}
      className="group cursor-pointer rounded-lg overflow-hidden bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="aspect-[2/3] bg-gray-200 dark:bg-gray-700 overflow-hidden">
        {book.cover_path ? (
          <img
            src={booksApi.getCoverUrl(book.id)}
            alt={book.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <span className="text-4xl">{book.file_format.toUpperCase()}</span>
          </div>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-medium text-sm text-gray-900 dark:text-white truncate">{book.title}</h3>
        {book.author && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">{book.author}</p>
        )}
        <div className="flex gap-1 mt-2">
          {book.tags.slice(0, 2).map((tag) => (
            <span key={tag.id} className="text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">
              {tag.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
