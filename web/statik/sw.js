/* Servis çalışanı — yalnız KABUK önbelleklenir, veri asla.
 *
 * Neden veri önbelleklenmiyor: sayfalar kullanıcıya özel. Bir yanıtı
 * önbelleğe koymak, aynı cihazda başka biri giriş yaptığında ona başkasının
 * kütüphanesini göstermek demek olurdu — web katmanındaki `lru_cache`
 * hatasının (2026-09-15) tarayıcı tarafındaki eşi. O yüzden strateji
 * "önce ağ", ve çevrimdışıyken yalnız statik dosyalar ile bir bilgi sayfası.
 */
const SURUM = "kesif-v1";
const KABUK = [
  "/statik/stil.css",
  "/statik/uygulama.js",
  "/statik/ikon-192.png",
  "/statik/manifest.webmanifest",
];

self.addEventListener("install", (olay) => {
  olay.waitUntil(caches.open(SURUM).then((c) => c.addAll(KABUK)));
  self.skipWaiting();
});

self.addEventListener("activate", (olay) => {
  olay.waitUntil(
    caches.keys().then((adlar) =>
      Promise.all(adlar.filter((a) => a !== SURUM).map((a) => caches.delete(a)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (olay) => {
  const istek = olay.request;
  if (istek.method !== "GET") return;
  const url = new URL(istek.url);
  if (url.origin !== self.location.origin) return;

  // Yalnız statik dosyalar önbellekten karşılanabilir.
  if (url.pathname.startsWith("/statik/")) {
    olay.respondWith(
      caches.match(istek).then((v) => v || fetch(istek).then((y) => {
        const kopya = y.clone();
        caches.open(SURUM).then((c) => c.put(istek, kopya));
        return y;
      }))
    );
    return;
  }

  // Sayfalar: HER ZAMAN ağdan. Çevrimdışıysa açıklayıcı bir yanıt.
  olay.respondWith(
    fetch(istek).catch(() =>
      new Response(
        "<!doctype html><meta charset=utf-8><title>Çevrimdışı</title>" +
        "<body style='background:#0e0f12;color:#e6e6e6;font:15px/1.6 system-ui;" +
        "display:grid;place-items:center;height:100vh;margin:0;text-align:center;padding:2rem'>" +
        "<div><h1 style='font-size:1.3rem'>Bağlantı yok</h1>" +
        "<p style='color:#9aa'>Keşif Motoru sunucuya bağlı çalışıyor — öneriler " +
        "senin kütüphanenden hesaplanıyor ve telefonda saklanmıyor.</p></div>",
        { headers: { "Content-Type": "text/html; charset=utf-8" } }
      )
    )
  );
});
