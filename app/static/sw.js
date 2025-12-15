/*const CACHE_NAME = "cegonha-v1.2";
const ASSETS_TO_CACHE = [
  "./",
  "./index.html",
  "./css/style.css",
  "./js/main.js",
  "./js/api.js",
  "./assets/logo2.webp",
  "./assets/favicon.webp",
  "./assets/burger_classic.png",
  // Adicione aqui outras imagens principais se quiser que carreguem offline
];

// 1. Instalação: Cacheia os arquivos estáticos
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("Arquivos cacheados com sucesso!");
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// 2. Ativação: Limpa caches antigos se mudar a versão
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// 3. Interceptação (Fetch): Serve o cache primeiro, depois a rede
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      // Se tiver no cache, retorna. Se não, busca na rede.
      return response || fetch(event.request);
    })
  );
});*/
