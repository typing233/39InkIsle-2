import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { readerApi } from '@/api/reader';
import { useReaderStore } from '@/store';
import { getDeviceId } from '@/lib/progressSync';
import { PdfInfo } from '@/types/reader';
import { ChevronLeft, ChevronRight, ArrowLeft, Columns, FileText } from 'lucide-react';

const DEVICE_ID = getDeviceId();

type ViewMode = 'paginated' | 'stream';

export default function PdfReader() {
  const { bookId } = useParams<{ bookId: string }>();
  const navigate = useNavigate();
  const { settings } = useReaderStore();
  const streamContainerRef = useRef<HTMLDivElement>(null);
  const pdfDocRef = useRef<any>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const renderedPages = useRef<Set<number>>(new Set());
  const pageCanvasRefs = useRef<Map<number, HTMLCanvasElement>>(new Map());

  const [pdfInfo, setPdfInfo] = useState<PdfInfo | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>('paginated');
  const [loading, setLoading] = useState(true);
  const [pdfLoaded, setPdfLoaded] = useState(false);
  const currentPageRef = useRef(0);

  // Keep ref in sync for use in observer callbacks
  useEffect(() => { currentPageRef.current = currentPage; }, [currentPage]);

  // Load pdf.js and the PDF document
  useEffect(() => {
    if (!bookId) return;

    let cancelled = false;

    const loadPdf = async () => {
      const pdfjsLib = await import('pdfjs-dist');
      pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

      const token = localStorage.getItem('access_token') || '';
      const loadingTask = pdfjsLib.getDocument({
        url: readerApi.getPdfStreamUrl(bookId),
        httpHeaders: { Authorization: `Bearer ${token}` },
      });

      const doc = await loadingTask.promise;
      if (cancelled) return;

      pdfDocRef.current = doc;
      setPdfInfo({ page_count: doc.numPages, metadata: {} });
      setPdfLoaded(true);
      setLoading(false);
    };

    loadPdf().catch(() => setLoading(false));

    readerApi.getProgress(bookId).then(({ data }) => {
      if (data.length > 0) {
        const latest = data.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())[0];
        if (latest.chapter_index != null) {
          setCurrentPage(latest.chapter_index);
          currentPageRef.current = latest.chapter_index;
        }
      }
    }).catch(() => {});

    return () => { cancelled = true; };
  }, [bookId]);

  const syncProgress = useCallback((page: number) => {
    if (!bookId || !pdfInfo) return;
    const percent = ((page + 1) / pdfInfo.page_count) * 100;
    readerApi.updateProgress(bookId, {
      chapter_index: page,
      progress_percent: Math.round(percent * 100) / 100,
      device_id: DEVICE_ID,
    }).catch(() => {});
  }, [bookId, pdfInfo]);

  const goToPage = useCallback((page: number) => {
    if (!pdfInfo) return;
    const clamped = Math.max(0, Math.min(page, pdfInfo.page_count - 1));
    setCurrentPage(clamped);
    syncProgress(clamped);
  }, [pdfInfo, syncProgress]);

  // Render a page to a given canvas element
  const renderPage = useCallback(async (pageNum: number, canvas: HTMLCanvasElement) => {
    const doc = pdfDocRef.current;
    if (!doc) return;

    const page = await doc.getPage(pageNum + 1);
    const scale = 1.5;
    const viewport = page.getViewport({ scale });

    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext('2d')!;
    await page.render({ canvasContext: ctx, viewport }).promise;
  }, []);

  // Paginated mode: render only the current page
  const paginatedCanvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (viewMode !== 'paginated' || !pdfLoaded) return;
    const canvas = paginatedCanvasRef.current;
    if (!canvas) return;
    renderPage(currentPage, canvas);
  }, [currentPage, viewMode, pdfLoaded, renderPage]);

  // Stream mode: set up IntersectionObserver for lazy rendering
  useEffect(() => {
    if (viewMode !== 'stream' || !pdfLoaded || !pdfInfo) return;

    renderedPages.current.clear();

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const pageNum = parseInt(entry.target.getAttribute('data-page') || '0', 10);
          if (entry.isIntersecting) {
            const canvas = entry.target as HTMLCanvasElement;
            if (!renderedPages.current.has(pageNum)) {
              renderedPages.current.add(pageNum);
              renderPage(pageNum, canvas);
            }
            if (entry.intersectionRatio >= 0.5) {
              setCurrentPage(pageNum);
            }
          }
        }
      },
      { root: streamContainerRef.current, rootMargin: '300px', threshold: [0, 0.5] }
    );
    observerRef.current = observer;

    pageCanvasRefs.current.forEach((canvas) => {
      observer.observe(canvas);
    });

    return () => observer.disconnect();
  }, [viewMode, pdfLoaded, pdfInfo, renderPage]);

  // Sync progress when page changes in stream mode (debounced)
  useEffect(() => {
    if (viewMode !== 'stream' || !pdfInfo) return;
    const timer = setTimeout(() => syncProgress(currentPage), 1000);
    return () => clearTimeout(timer);
  }, [currentPage, viewMode, pdfInfo, syncProgress]);

  // Scroll to current page when switching to stream mode
  const scrollToCurrentInStream = useCallback(() => {
    const canvas = pageCanvasRefs.current.get(currentPageRef.current);
    if (canvas) {
      canvas.scrollIntoView({ behavior: 'instant', block: 'start' });
    }
  }, []);

  useEffect(() => {
    if (viewMode === 'stream' && pdfLoaded) {
      // Slight delay so DOM has rendered all canvas elements
      requestAnimationFrame(() => {
        scrollToCurrentInStream();
      });
    }
  }, [viewMode, pdfLoaded, scrollToCurrentInStream]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (viewMode === 'paginated') {
        if (e.key === 'ArrowLeft') goToPage(currentPage - 1);
        if (e.key === 'ArrowRight') goToPage(currentPage + 1);
      }
      if (e.key === 'Escape') navigate('/');
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [currentPage, goToPage, navigate, viewMode]);

  const handleModeSwitch = () => {
    renderedPages.current.clear();
    setViewMode(viewMode === 'paginated' ? 'stream' : 'paginated');
  };

  const bgClass = settings.theme === 'night' ? 'bg-[#1a1a2e]' : settings.theme === 'sepia' ? 'bg-[#f5ead6]' : 'bg-gray-100';
  const textClass = settings.theme === 'night' ? 'text-gray-200' : settings.theme === 'sepia' ? 'text-[#5c4a2a]' : 'text-gray-900';
  const progress = pdfInfo ? ((currentPage + 1) / pdfInfo.page_count) * 100 : 0;

  if (loading) {
    return <div className="fixed inset-0 flex items-center justify-center bg-gray-100"><div className="animate-pulse text-gray-500">Loading PDF...</div></div>;
  }

  return (
    <div className={`fixed inset-0 ${bgClass} ${textClass} flex flex-col`}>
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 h-12 bg-black/5 backdrop-blur shrink-0">
        <button onClick={() => navigate('/')} className="p-2 hover:bg-black/10 rounded">
          <ArrowLeft size={20} />
        </button>
        <span className="text-sm opacity-70">
          Page {currentPage + 1} / {pdfInfo?.page_count ?? '...'}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={handleModeSwitch}
            className="p-2 hover:bg-black/10 rounded"
            title={viewMode === 'paginated' ? 'Switch to scroll mode' : 'Switch to page mode'}
          >
            {viewMode === 'paginated' ? <Columns size={18} /> : <FileText size={18} />}
          </button>
        </div>
      </div>

      {/* Reader area */}
      <div className="flex-1 relative overflow-hidden">
        {viewMode === 'paginated' ? (
          <div className="absolute inset-0 flex items-center justify-center p-4">
            <canvas
              ref={paginatedCanvasRef}
              className="max-w-full max-h-full object-contain shadow-lg"
              style={{ width: 'auto', height: '100%' }}
            />
            <button
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage === 0}
              className="absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/10 hover:bg-black/20 disabled:opacity-30 z-20"
            >
              <ChevronLeft size={24} />
            </button>
            <button
              onClick={() => goToPage(currentPage + 1)}
              disabled={!pdfInfo || currentPage >= pdfInfo.page_count - 1}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/10 hover:bg-black/20 disabled:opacity-30 z-20"
            >
              <ChevronRight size={24} />
            </button>
          </div>
        ) : (
          <div
            ref={streamContainerRef}
            className="absolute inset-0 overflow-y-auto flex flex-col items-center gap-4 py-4"
          >
            {pdfInfo && Array.from({ length: pdfInfo.page_count }, (_, i) => (
              <canvas
                key={`stream-page-${i}`}
                data-page={i}
                ref={(el) => {
                  if (el) {
                    pageCanvasRefs.current.set(i, el);
                    observerRef.current?.observe(el);
                  }
                }}
                className="max-w-full shadow-md bg-white"
                style={{ minHeight: '600px', width: '90%' }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-8 px-4 flex items-center gap-3 bg-black/5 shrink-0">
        <div className="flex-1 h-1 bg-gray-300 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} />
        </div>
        <span className="text-xs opacity-70 whitespace-nowrap">{progress.toFixed(1)}%</span>
      </div>
    </div>
  );
}
