import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { readerApi } from '@/api/reader';
import { useReaderStore } from '@/store';
import { getDeviceId } from '@/lib/progressSync';
import { CbzInfo } from '@/types/reader';
import { ChevronLeft, ChevronRight, ArrowLeft } from 'lucide-react';

const DEVICE_ID = getDeviceId();

export default function CbzReader() {
  const { bookId } = useParams<{ bookId: string }>();
  const navigate = useNavigate();
  const { settings } = useReaderStore();

  const [cbzInfo, setCbzInfo] = useState<CbzInfo | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!bookId) return;
    readerApi.getCbzInfo(bookId).then(({ data }) => {
      setCbzInfo(data);
      setLoading(false);
    });
    readerApi.getProgress(bookId).then(({ data }) => {
      if (data.length > 0) {
        const latest = data.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())[0];
        if (latest.chapter_index != null) setCurrentPage(latest.chapter_index);
      }
    }).catch(() => {});
  }, [bookId]);

  const syncProgress = useCallback((page: number) => {
    if (!bookId || !cbzInfo) return;
    const percent = ((page + 1) / cbzInfo.page_count) * 100;
    readerApi.updateProgress(bookId, {
      chapter_index: page,
      progress_percent: Math.round(percent * 100) / 100,
      device_id: DEVICE_ID,
    }).catch(() => {});
  }, [bookId, cbzInfo]);

  const goToPage = useCallback((page: number) => {
    if (!cbzInfo) return;
    const clamped = Math.max(0, Math.min(page, cbzInfo.page_count - 1));
    setCurrentPage(clamped);
    syncProgress(clamped);
  }, [cbzInfo, syncProgress]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') goToPage(currentPage - 1);
      if (e.key === 'ArrowRight') goToPage(currentPage + 1);
      if (e.key === 'Escape') navigate('/');
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [currentPage, goToPage, navigate]);

  // Preload adjacent pages
  useEffect(() => {
    if (!bookId || !cbzInfo) return;
    const preload = [currentPage - 1, currentPage + 1].filter(p => p >= 0 && p < cbzInfo.page_count);
    preload.forEach(p => {
      const img = new Image();
      img.src = readerApi.getCbzPageUrl(bookId, p);
    });
  }, [bookId, currentPage, cbzInfo]);

  const bgClass = settings.theme === 'night' ? 'bg-[#1a1a2e]' : settings.theme === 'sepia' ? 'bg-[#f5ead6]' : 'bg-gray-900';
  const textClass = settings.theme === 'night' ? 'text-gray-200' : 'text-gray-100';
  const progress = cbzInfo ? ((currentPage + 1) / cbzInfo.page_count) * 100 : 0;

  if (loading) {
    return <div className="fixed inset-0 flex items-center justify-center bg-gray-900"><div className="animate-pulse text-gray-400">Loading CBZ...</div></div>;
  }

  return (
    <div className={`fixed inset-0 ${bgClass} ${textClass} flex flex-col`}>
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 h-12 bg-black/30 backdrop-blur shrink-0">
        <button onClick={() => navigate('/')} className="p-2 hover:bg-white/10 rounded">
          <ArrowLeft size={20} />
        </button>
        <span className="text-sm opacity-70">
          {currentPage + 1} / {cbzInfo?.page_count ?? '...'}
        </span>
        <div className="w-10" />
      </div>

      {/* Image area */}
      <div className="flex-1 relative overflow-hidden flex items-center justify-center">
        {bookId && (
          <img
            key={currentPage}
            src={readerApi.getCbzPageUrl(bookId, currentPage)}
            alt={`Page ${currentPage + 1}`}
            className="max-w-full max-h-full object-contain"
          />
        )}

        {/* Click zones */}
        <button
          onClick={() => goToPage(currentPage - 1)}
          className="absolute left-0 top-0 w-1/3 h-full opacity-0 cursor-pointer z-10"
          aria-label="Previous page"
        />
        <button
          onClick={() => goToPage(currentPage + 1)}
          className="absolute right-0 top-0 w-1/3 h-full opacity-0 cursor-pointer z-10"
          aria-label="Next page"
        />

        <button onClick={() => goToPage(currentPage - 1)} className="absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/30 hover:bg-black/50 text-white z-20">
          <ChevronLeft size={24} />
        </button>
        <button onClick={() => goToPage(currentPage + 1)} className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/30 hover:bg-black/50 text-white z-20">
          <ChevronRight size={24} />
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-8 px-4 flex items-center gap-3 bg-black/30 shrink-0">
        <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} />
        </div>
        <span className="text-xs opacity-70 whitespace-nowrap">{progress.toFixed(1)}%</span>
      </div>
    </div>
  );
}
