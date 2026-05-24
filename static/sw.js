const CACHE_NAME = 'alsalfa-v2';
const DYNAMIC_CACHE = 'alsalfa-dynamic-v2';
const ASSETS = [
  '/',
  '/manifest.json',
  'https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap',
  'https://cdn-icons-png.flaticon.com/512/8030/8030198.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return Promise.allSettled(
        ASSETS.map(asset => cache.add(asset).catch(() => null))
      );
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME && key !== DYNAMIC_CACHE)
            .map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // 1. Static Assets: Cache First
  if (ASSETS.some(asset => request.url.endsWith(asset))) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request))
    );
    return;
  }

  // 2. Images: Network First, then Cache (to ensure they show up immediately)
  if (request.destination === 'image') {
    event.respondWith(
      fetch(request)
        .then(networkResponse => {
          if (networkResponse && networkResponse.status === 200) {
            const cacheCopy = networkResponse.clone();
            caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, cacheCopy));
          }
          return networkResponse;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // 3. API & Others: Network with Cache Fallback
  event.respondWith(
    fetch(request)
      .then(networkResponse => {
        if (networkResponse && networkResponse.status === 200 && url.pathname.startsWith('/api/')) {
          const cacheCopy = networkResponse.clone();
          caches.open(DYNAMIC_CACHE).then(cache => cache.put(request, cacheCopy));
        }
        return networkResponse;
      })
      .catch(() => caches.match(request))
  );
});
