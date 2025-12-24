const cacheName = 'brickify-cache-v1';
const assets = [
  '/',
  '/static/icon-192.png',
  '/static/icon-512.png',
  // Add any other static files you want cached
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(cacheName).then(cache => cache.addAll(assets))
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // If the request is for music or art, try network first, then cache
  if (url.pathname.startsWith('/music/') || url.pathname.startsWith('/art/')) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const resClone = res.clone();
          caches.open(cacheName).then(cache => cache.put(e.request, resClone));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
  } else {
    // For other requests, cache first, then network
    e.respondWith(
      caches.match(e.request).then(r => r || fetch(e.request))
    );
  }
});
