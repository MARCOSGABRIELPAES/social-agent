
const CACHE = 'painel-202608071918';
const ESSENCIAIS = ['./', './index.html', './manifest.json'];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ESSENCIAIS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(
        nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (evento) => {
  if (evento.request.method !== 'GET') return;
  evento.respondWith(
    caches.match(evento.request).then((guardado) => {
      const rede = fetch(evento.request).then((resposta) => {
        if (resposta && resposta.status === 200) {
          const copia = resposta.clone();
          caches.open(CACHE).then((c) => c.put(evento.request, copia));
        }
        return resposta;
      }).catch(() => guardado);
      return guardado || rede;
    })
  );
});
