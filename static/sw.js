const CACHE_NAME = 'alsalfa-v2';
const ASSETS = [
  '/',
  '/static/manifest.json',
  'https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap',
  'https://cdn-icons-png.flaticon.com/512/8030/8030198.png'
];

// تثبيت الـ Service Worker وحفظ الملفات الأساسية
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

// تفعيل وتحديث الكاش القديم
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// التعامل مع الطلبات وتخزين الصور والبيانات تلقائياً
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // التحقق مما إذا كان الطلب صورة أو رابط من سوبا بيس أو طلب API للفئات
  const isImage = event.request.destination === 'image' ||
                  url.pathname.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i) ||
                  url.host.includes('supabase.co');

  const isDataApi = url.pathname.includes('/api/categories');

  if (isImage || isDataApi) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(event.request).then((cachedResponse) => {
          // استراتيجية Stale-while-revalidate
          // نعيد الكاش فوراً إذا وجد، ونحدثه في الخلفية
          const fetchPromise = fetch(event.request).then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              cache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          }).catch(() => cachedResponse);

          return cachedResponse || fetchPromise;
        });
      })
    );
  } else {
    // للملفات الأخرى، نستخدم الشبكة أولاً مع الرجوع للكاش في حال الانقطاع (Network First)
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request);
      })
    );
  }
});
