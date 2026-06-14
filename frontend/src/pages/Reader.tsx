import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ePub, { Book, Rendition } from 'epubjs';
import { booksApi } from '@/api/books';
import { readerApi } from '@/api/reader';
import { useReaderStore } from '@/store';
import { TOCItem, ReadingProgress } from '@/types/reader';
import { resolveProgressConflict, getDeviceId, syncQueuedProgress } from '@/lib/progressSync';
import { ChevronLeft, ChevronRight, List, Settings, ArrowLeft, Wifi, WifiOff, Download } from 'lucide-react';

const DEVICE_ID = getDeviceId();

export default function Reader() {
  const { bookId } = useParams<{ bookId: string }>();
  const navigate = useNavigate();
  const viewerRef = useRef<HTMLDivElement>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const bookRef = useRef<Book | null>(null);

  const { settings, updateSettings } = useReaderStore();
  const [toc, setToc] = useState<TOCItem[]>([]);
  const [showTOC, setShowTOC] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentChapter, setCurrentChapter] = useState('');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [cachedOffline, setCachedOffline] = useState(false);
  const [conflictResolved, setConflictResolved] = useState<string | null>(null);

  // Track online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      syncQueuedProgress();
    };
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Flush any queued progress on mount
  useEffect(() => {
    if (isOnline) syncQueuedProgress();
  }, [isOnline]);

  // Queue progress for offline sync
  const queueProgress = useCallback((cfi: string, percent: number) => {
    if (!bookId) return;
    const queue = JSON.parse(localStorage.getItem('progress_queue') || '[]');
    // Remove older entries for same book+device
    const filtered = queue.filter(
      (item: { bookId: string; device_id: string }) =>
        !(item.bookId === bookId && item.device_id === DEVICE_ID)
    );
    filtered.push({
      bookId,
      cfi,
      progress_percent: Math.round(percent * 100) / 100,
      device_id: DEVICE_ID,
      timestamp: Date.now(),
    });
    localStorage.setItem('progress_queue', JSON.stringify(filtered));
  }, [bookId]);

  const syncProgressToServer = useCallback(async (cfi: string, percent: number) => {
    if (!bookId) return;
    if (!isOnline) {
      queueProgress(cfi, percent);
      return;
    }
    try {
      await readerApi.updateProgress(bookId, {
        cfi,
        progress_percent: Math.round(percent * 100) / 100,
        device_id: DEVICE_ID,
      });
    } catch {
      queueProgress(cfi, percent);
    }
  }, [bookId, isOnline, queueProgress]);

  // Download book for offline
  const handleDownloadOffline = useCallback(async () => {
    if (!bookId) return;
    try {
      const cache = await caches.open('inkisle-books-v1');
      const fileUrl = booksApi.getFileUrl(bookId);
      const token = localStorage.getItem('access_token');
      const response = await fetch(fileUrl, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        await cache.put(fileUrl, response);
        setCachedOffline(true);
      }
    } catch {
      // Silently fail
    }
  }, [bookId]);

  // Check if book is already cached
  useEffect(() => {
    if (!bookId) return;
    caches.open('inkisle-books-v1').then((cache) =>
      cache.match(booksApi.getFileUrl(bookId)).then((r) => {
        if (r) setCachedOffline(true);
      })
    ).catch(() => {});
  }, [bookId]);

  useEffect(() => {
    if (!bookId || !viewerRef.current) return;

    const book = ePub(booksApi.getFileUrl(bookId));
    bookRef.current = book;

    const rendition = book.renderTo(viewerRef.current, {
      width: '100%',
      height: '100%',
      spread: 'none',
      flow: 'paginated',
    });
    renditionRef.current = rendition;

    book.loaded.navigation.then((nav) => {
      const items: TOCItem[] = [];
      const flatten = (tocItems: typeof nav.toc, level = 0) => {
        for (const item of tocItems) {
          items.push({ title: item.label.trim(), href: item.href, level });
          if (item.subitems) flatten(item.subitems, level + 1);
        }
      };
      flatten(nav.toc);
      setToc(items);
    });

    // Cross-device progress conflict resolution
    readerApi.getProgress(bookId).then(({ data }) => {
      if (data.length > 0) {
        const resolvedCfi = resolveProgressConflict(data);
        if (resolvedCfi) {
          setConflictResolved(data.length > 1 ? resolvedCfi : null);
          rendition.display(resolvedCfi);
          return;
        }
      }
      rendition.display();
    }).catch(() => {
      // Offline: try from local queue
      const queue = JSON.parse(localStorage.getItem('progress_queue') || '[]');
      const localProgress = queue.find(
        (item: { bookId: string; device_id: string }) =>
          item.bookId === bookId && item.device_id === DEVICE_ID
      );
      if (localProgress?.cfi) {
        rendition.display(localProgress.cfi);
      } else {
        rendition.display();
      }
    });

    rendition.on('relocated', (location: { start: { cfi: string; percentage: number } }) => {
      const percent = location.start.percentage * 100;
      setProgress(percent);
      syncProgressToServer(location.start.cfi, percent);
    });

    rendition.on('rendered', (_section: unknown, view: { document: Document }) => {
      if (view?.document) {
        const heading = view.document.querySelector('h1, h2, h3');
        if (heading) setCurrentChapter(heading.textContent || '');
      }
    });

    return () => {
      book.destroy();
    };
  }, [bookId, syncProgressToServer]);

  useEffect(() => {
    if (!renditionRef.current) return;
    const r = renditionRef.current;

    r.themes.override('font-size', `${settings.fontSize}px`);
    r.themes.override('font-family', settings.fontFamily);
    r.themes.override('line-height', `${settings.lineHeight}`);
    r.themes.override('padding', `${settings.padding}px`);

    const colors = {
      day: { bg: '#ffffff', text: '#1a1a1a' },
      night: { bg: '#1a1a2e', text: '#e0e0e0' },
      sepia: { bg: '#f5ead6', text: '#5c4a2a' },
    };
    const theme = colors[settings.theme];
    r.themes.override('color', theme.text);
    r.themes.override('background', theme.bg);
  }, [settings]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') renditionRef.current?.prev();
      if (e.key === 'ArrowRight') renditionRef.current?.next();
      if (e.key === 'Escape') {
        setShowTOC(false);
        setShowSettings(false);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  // Touch swipe support
  useEffect(() => {
    const el = viewerRef.current;
    if (!el) return;
    let startX = 0;
    const handleTouchStart = (e: TouchEvent) => { startX = e.touches[0].clientX; };
    const handleTouchEnd = (e: TouchEvent) => {
      const diff = e.changedTouches[0].clientX - startX;
      if (Math.abs(diff) > 50) {
        if (diff > 0) renditionRef.current?.prev();
        else renditionRef.current?.next();
      }
    };
    el.addEventListener('touchstart', handleTouchStart);
    el.addEventListener('touchend', handleTouchEnd);
    return () => {
      el.removeEventListener('touchstart', handleTouchStart);
      el.removeEventListener('touchend', handleTouchEnd);
    };
  }, []);

  const bgClass = settings.theme === 'night' ? 'bg-[#1a1a2e]' : settings.theme === 'sepia' ? 'bg-[#f5ead6]' : 'bg-white';
  const textClass = settings.theme === 'night' ? 'text-gray-200' : settings.theme === 'sepia' ? 'text-[#5c4a2a]' : 'text-gray-900';

  return (
    <div className={`fixed inset-0 ${bgClass} ${textClass} flex flex-col`}>
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 h-12 bg-black/5 backdrop-blur shrink-0">
        <button onClick={() => navigate('/')} className="p-2 hover:bg-black/10 rounded">
          <ArrowLeft size={20} />
        </button>
        <span className="text-sm truncate max-w-[40%] opacity-70">{currentChapter}</span>
        <div className="flex items-center gap-1">
          {isOnline ? <Wifi size={14} className="opacity-50" /> : <WifiOff size={14} className="text-orange-500" />}
          {!cachedOffline && (
            <button onClick={handleDownloadOffline} className="p-2 hover:bg-black/10 rounded" title="Download for offline">
              <Download size={18} />
            </button>
          )}
          <button onClick={() => setShowTOC(!showTOC)} className="p-2 hover:bg-black/10 rounded">
            <List size={20} />
          </button>
          <button onClick={() => setShowSettings(!showSettings)} className="p-2 hover:bg-black/10 rounded">
            <Settings size={20} />
          </button>
        </div>
      </div>

      {/* Conflict notification */}
      {conflictResolved && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/30 text-sm text-blue-700 dark:text-blue-300 text-center shrink-0">
          Progress synced from another device. Resumed from latest position.
          <button onClick={() => setConflictResolved(null)} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {/* Reader area */}
      <div className="flex-1 relative overflow-hidden">
        <div ref={viewerRef} className="absolute inset-0" />

        {/* Click zones */}
        <button
          onClick={() => renditionRef.current?.prev()}
          className="absolute left-0 top-0 w-1/4 h-full opacity-0 cursor-pointer z-10"
          aria-label="Previous page"
        />
        <button
          onClick={() => renditionRef.current?.next()}
          className="absolute right-0 top-0 w-1/4 h-full opacity-0 cursor-pointer z-10"
          aria-label="Next page"
        />

        {/* Page turn buttons */}
        <button
          onClick={() => renditionRef.current?.prev()}
          className="absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/10 hover:bg-black/20 z-20"
        >
          <ChevronLeft size={24} />
        </button>
        <button
          onClick={() => renditionRef.current?.next()}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-black/10 hover:bg-black/20 z-20"
        >
          <ChevronRight size={24} />
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-8 px-4 flex items-center gap-3 bg-black/5 shrink-0">
        <div className="flex-1 h-1 bg-gray-300 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} />
        </div>
        <span className="text-xs opacity-70 whitespace-nowrap">{progress.toFixed(1)}%</span>
      </div>

      {/* TOC Drawer */}
      {showTOC && (
        <div className="absolute top-12 left-0 bottom-8 w-80 bg-white dark:bg-gray-800 shadow-xl z-30 overflow-y-auto border-r">
          <div className="p-4">
            <h3 className="font-semibold mb-3">Table of Contents</h3>
            <ul className="space-y-1">
              {toc.map((item, i) => (
                <li key={i}>
                  <button
                    onClick={() => {
                      renditionRef.current?.display(item.href);
                      setShowTOC(false);
                    }}
                    className="w-full text-left px-2 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded truncate"
                    style={{ paddingLeft: `${item.level * 16 + 8}px` }}
                  >
                    {item.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Settings panel */}
      {showSettings && (
        <div className="absolute top-12 right-0 bottom-8 w-72 bg-white dark:bg-gray-800 shadow-xl z-30 overflow-y-auto border-l p-4 space-y-5">
          <h3 className="font-semibold">Reading Settings</h3>

          <div>
            <label className="text-sm opacity-70">Font Size: {settings.fontSize}px</label>
            <input
              type="range" min={12} max={32} value={settings.fontSize}
              onChange={(e) => updateSettings({ fontSize: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>

          <div>
            <label className="text-sm opacity-70">Line Height: {settings.lineHeight}</label>
            <input
              type="range" min={1.2} max={2.5} step={0.1} value={settings.lineHeight}
              onChange={(e) => updateSettings({ lineHeight: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>

          <div>
            <label className="text-sm opacity-70 block mb-2">Font</label>
            <select
              value={settings.fontFamily}
              onChange={(e) => updateSettings({ fontFamily: e.target.value })}
              className="w-full px-2 py-1 rounded border text-sm bg-white dark:bg-gray-700"
            >
              <option value="Georgia, serif">Georgia</option>
              <option value="'Times New Roman', serif">Times New Roman</option>
              <option value="system-ui, sans-serif">System UI</option>
              <option value="'Noto Serif SC', serif">Noto Serif SC</option>
              <option value="monospace">Monospace</option>
            </select>
          </div>

          <div>
            <label className="text-sm opacity-70 block mb-2">Theme</label>
            <div className="flex gap-2">
              {(['day', 'night', 'sepia'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => updateSettings({ theme: t })}
                  className={`flex-1 py-2 rounded border text-sm capitalize ${
                    settings.theme === t ? 'ring-2 ring-blue-500' : ''
                  } ${t === 'day' ? 'bg-white text-black' : t === 'night' ? 'bg-[#1a1a2e] text-white' : 'bg-[#f5ead6] text-[#5c4a2a]'}`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm opacity-70">Padding: {settings.padding}px</label>
            <input
              type="range" min={8} max={64} value={settings.padding}
              onChange={(e) => updateSettings({ padding: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>

          <div className="border-t pt-4">
            <p className="text-xs opacity-50">
              {cachedOffline ? '✓ Book cached for offline' : 'Not cached offline'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
