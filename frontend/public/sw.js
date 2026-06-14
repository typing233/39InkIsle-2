const CACHE_NAME = 'inkisle-v1';
const BOOK_CACHE = 'inkisle-books-v1';
const PROGRESS_QUEUE_KEY = 'inkisle-progress-queue';

const STATIC_ASSETS = ['/', '/index.html'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME && k !== BOOK_CACHE)
          .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Cache book file downloads for offline reading
  if (url.pathname.match(/\/api\/v1\/books\/[^/]+\/file$/)) {
    event.respondWith(
      caches.open(BOOK_CACHE).then((cache) =>
        cache.match(event.request).then((cached) => {
          if (cached) return cached;
          return fetch(event.request).then((response) => {
            if (response.ok) {
              cache.put(event.request, response.clone());
            }
            return response;
          });
        })
      )
    );
    return;
  }

  // Cache chapter content for offline EPUB reading
  if (url.pathname.match(/\/api\/v1\/reader\/[^/]+\/content\/\d+$/)) {
    event.respondWith(
      caches.open(BOOK_CACHE).then((cache) =>
        cache.match(event.request).then((cached) => {
          if (cached) return cached;
          return fetch(event.request).then((response) => {
            if (response.ok) {
              cache.put(event.request, response.clone());
            }
            return response;
          }).catch(() => {
            return new Response('Offline - content not cached', { status: 503 });
          });
        })
      )
    );
    return;
  }

  // Cache TOC
  if (url.pathname.match(/\/api\/v1\/reader\/[^/]+\/toc$/)) {
    event.respondWith(
      caches.open(BOOK_CACHE).then((cache) =>
        cache.match(event.request).then((cached) => {
          if (cached) return cached;
          return fetch(event.request).then((response) => {
            if (response.ok) cache.put(event.request, response.clone());
            return response;
          }).catch(() => cached || new Response('[]', { headers: { 'Content-Type': 'application/json' } }));
        })
      )
    );
    return;
  }

  // Queue progress updates when offline
  if (url.pathname.match(/\/api\/v1\/reader\/[^/]+\/progress$/) && event.request.method === 'PUT') {
    event.respondWith(
      fetch(event.request.clone()).catch(async () => {
        // Offline: queue the progress update for later sync
        const body = await event.request.json();
        const clients = await self.clients.matchAll();
        clients.forEach((client) => {
          client.postMessage({ type: 'PROGRESS_QUEUED', data: body });
        });
        return new Response(JSON.stringify({ queued: true }), {
          status: 202,
          headers: { 'Content-Type': 'application/json' },
        });
      })
    );
    return;
  }

  // App shell: serve cached for navigation requests
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Static assets: cache-first
  if (event.request.method === 'GET' && !url.pathname.startsWith('/api/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((response) => {
          if (response.ok && (url.pathname.endsWith('.js') || url.pathname.endsWith('.css'))) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        });
      })
    );
    return;
  }
});

// Background sync: flush queued progress when back online
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-progress') {
    event.waitUntil(syncQueuedProgress());
  }
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'CACHE_BOOK') {
    // Pre-cache a book for offline reading
    const { fileUrl, bookId } = event.data;
    event.waitUntil(
      caches.open(BOOK_CACHE).then((cache) =>
        cache.add(new Request(fileUrl, { headers: { Authorization: event.data.token } }))
      ).catch(() => {})
    );
  }

  if (event.data && event.data.type === 'FLUSH_PROGRESS') {
    event.waitUntil(syncQueuedProgress());
  }
});

async function syncQueuedProgress() {
  // Progress sync is handled client-side via localStorage queue
  // This is a no-op placeholder for the SW; the real sync is in progressSync.ts
}
