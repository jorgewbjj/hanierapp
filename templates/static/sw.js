const CACHE_NAME = 'tingimento-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/pwa-icon-192.png',
  '/static/pwa-icon-512.png',
  '/static/Aviso.svg',
  '/static/Dosar.svg',
  '/static/Encher.svg',
  '/static/Injetar.svg',
  '/static/logo_hanier.svg',
  '/static/Patamar.svg',
  '/static/Soltar.svg',
  '/static/Termoregulação.svg',
  '/static/Transbordo.svg',
  // inclua outros arquivos que queira offline, ex: /static/logo_hanier.svg
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});
