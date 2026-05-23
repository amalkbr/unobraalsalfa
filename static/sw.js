const CACHE_NAME = 'alsalfa-v1';
const ASSETS = [
  '/',
  '/static/manifest.json',
  'https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap',
  'https://cdn-icons-png.flaticon.com/512/8030/8030198.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Cache strategy: Stale-While-Revalidate for images and API calls
  if (event.request.destination === 'image' || url.pathname.startsWith('/api/')) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(event.request).then((cachedResponse) => {
          const fetchedResponse = fetch(event.request).then((networkResponse) => {
            cache.put(event.request, networkResponse.clone());
            return networkResponse;
          });
          return cachedResponse || fetchedResponse;
        });
      })
    );
  } else {
    event.respondWith(
      caches.match(event.request).then((response) => {
        return response || fetch(event.request);
      })
    );
  }
});
