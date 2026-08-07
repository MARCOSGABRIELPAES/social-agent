
const CACHE = 'painel-202608071925';
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

function ehDocumento(requisicao) {
  return requisicao.mode === 'navigate' ||
    (requisicao.headers.get('accept') || '').includes('text/html');
}

self.addEventListener('fetch', (evento) => {
  if (evento.request.method !== 'GET') return;
  const requisicao = evento.request;

  if (ehDocumento(requisicao)) {
    evento.respondWith(
      fetch(requisicao).then((resposta) => {
        const copia = resposta.clone();
        caches.open(CACHE).then((c) => c.put('./index.html', copia));
        return resposta;
      }).catch(() => caches.match('./index.html').then(
        (guardado) => guardado || caches.match('./')))
    );
    return;
  }

  evento.respondWith(
    caches.match(requisicao).then((guardado) => guardado || fetch(requisicao).then(
      (resposta) => {
        if (resposta && resposta.status === 200) {
          const copia = resposta.clone();
          caches.open(CACHE).then((c) => c.put(requisicao, copia));
        }
        return resposta;
      }))
  );
});
