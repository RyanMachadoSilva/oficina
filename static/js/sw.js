/* Service worker mínimo: permite instalar como app.
   Não guarda páginas em cache para nunca mostrar dado desatualizado. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request).catch(() => new Response(
    '<meta name="viewport" content="width=device-width"><body style="font-family:sans-serif;padding:24px"><h2>Sem conexão</h2><p>Verifique a internet e tente de novo.</p></body>',
    { headers: { 'Content-Type': 'text/html; charset=utf-8' } })));
});
