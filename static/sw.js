const CACHE_NAME = 'alsalfa-v1';
const DYNAMIC_CACHE = 'alsalfa-dynamic-v1';
const ASSETS = [
  '/',
  '/static/manifest.json',
  'https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap',
  'https://cdn-icons-png.flaticon.com/512/8030/8030198.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
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
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  const shouldCacheImages = request.destination === 'image';
  const shouldCacheApi = url.origin === self.location.origin && (
    url.pathname === '/api/categories' ||
    url.pathname.startsWith('/api/')
  );
  const shouldCacheDynamically = shouldCacheImages || shouldCacheApi;

  if (shouldCacheDynamically) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        const networkFetch = fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(DYNAMIC_CACHE).then((cache) => cache.put(request, networkResponse.clone()));
          }
          return networkResponse.clone ? networkResponse.clone() : networkResponse;
        }).catch(() => null);

        return cachedResponse || networkFetch;
      })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((response) => response || fetch(request))
  );
});
