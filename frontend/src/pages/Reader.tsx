import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ePub, { Book, Rendition } from 'epubjs';
import { booksApi } from '@/api/books';
import { readerApi } from '@/api/reader';
import { useReaderStore } from '@/store';
import { TOCItem } from '@/types/reader';
import { ChevronLeft, ChevronRight, List, Settings, ArrowLeft } from 'lucide-react';

const DEVICE_ID = (() => {
  let id = localStorage.getItem('device_id');
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem('device_id', id);
  }
  return id;
})();

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

  const syncProgressToServer = useCallback(async (cfi: string, percent: number) => {
    if (!bookId) return;
    try {
      await readerApi.updateProgress(bookId, {
        cfi,
        progress_percent: Math.round(percent * 100) / 100,
        device_id: DEVICE_ID,
      });
    } catch {
      const queue = JSON.parse(localStorage.getItem('progress_queue') || '[]');
      queue.push({ bookId, cfi, progress_percent: percent, device_id: DEVICE_ID, timestamp: Date.now() });
      localStorage.setItem('progress_queue', JSON.stringify(queue));
    }
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

    readerApi.getProgress(bookId).then(({ data }) => {
      if (data.length > 0) {
        const latest = data.reduce((a, b) =>
          new Date(a.updated_at) > new Date(b.updated_at) ? a : b
        );
        if (latest.cfi) {
          rendition.display(latest.cfi);
          return;
        }
      }
      rendition.display();
    }).catch(() => {
      rendition.display();
    });

    rendition.on('relocated', (location: { start: { cfi: string; percentage: number; displayed: { page: number } }; end: { cfi: string } }) => {
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
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  const bgClass = settings.theme === 'night' ? 'bg-[#1a1a2e]' : settings.theme === 'sepia' ? 'bg-[#f5ead6]' : 'bg-white';

  return (
    <div className={`fixed inset-0 ${bgClass} flex flex-col`}>
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 h-12 bg-black/5 dark:bg-white/5 backdrop-blur">
        <button onClick={() => navigate('/')} className="p-2 hover:bg-black/10 rounded">
          <ArrowLeft size={20} />
        </button>
        <span className="text-sm truncate max-w-[50%] opacity-70">{currentChapter}</span>
        <div className="flex gap-2">
          <button onClick={() => setShowTOC(!showTOC)} className="p-2 hover:bg-black/10 rounded">
            <List size={20} />
          </button>
          <button onClick={() => setShowSettings(!showSettings)} className="p-2 hover:bg-black/10 rounded">
            <Settings size={20} />
          </button>
        </div>
      </div>

      {/* Reader area */}
      <div className="flex-1 relative overflow-hidden">
        <div ref={viewerRef} className="absolute inset-0" />

        {/* Click zones for navigation */}
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
      <div className="h-8 px-4 flex items-center gap-3 bg-black/5">
        <div className="flex-1 h-1 bg-gray-300 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} />
        </div>
        <span className="text-xs opacity-70">{progress.toFixed(1)}%</span>
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
            <label className="text-sm text-gray-600 dark:text-gray-400">Font Size: {settings.fontSize}px</label>
            <input
              type="range"
              min={12}
              max={32}
              value={settings.fontSize}
              onChange={(e) => updateSettings({ fontSize: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>

          <div>
            <label className="text-sm text-gray-600 dark:text-gray-400">Line Height: {settings.lineHeight}</label>
            <input
              type="range"
              min={1.2}
              max={2.5}
              step={0.1}
              value={settings.lineHeight}
              onChange={(e) => updateSettings({ lineHeight: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>

          <div>
            <label className="text-sm text-gray-600 dark:text-gray-400 block mb-2">Font</label>
            <select
              value={settings.fontFamily}
              onChange={(e) => updateSettings({ fontFamily: e.target.value })}
              className="w-full px-2 py-1 rounded border text-sm"
            >
              <option value="Georgia, serif">Georgia</option>
              <option value="'Times New Roman', serif">Times New Roman</option>
              <option value="system-ui, sans-serif">System UI</option>
              <option value="'Noto Serif SC', serif">Noto Serif SC</option>
              <option value="monospace">Monospace</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-gray-600 dark:text-gray-400 block mb-2">Theme</label>
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
            <label className="text-sm text-gray-600 dark:text-gray-400">Padding: {settings.padding}px</label>
            <input
              type="range"
              min={8}
              max={64}
              value={settings.padding}
              onChange={(e) => updateSettings({ padding: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>
        </div>
      )}
    </div>
  );
}
