/* Servis çalışanı — yalnız KABUK önbelleklenir, veri asla.
 *
 * Neden veri önbelleklenmiyor: sayfalar kullanıcıya özel. Bir yanıtı
 * önbelleğe koymak, aynı cihazda başka biri giriş yaptığında ona başkasının
 * kütüphanesini göstermek demek olurdu — web katmanındaki `lru_cache`
 * hatasının (2026-09-15) tarayıcı tarafındaki eşi. O yüzden strateji
 * "önce ağ", ve çevrimdışıyken yalnız statik dosyalar ile bir bilgi sayfası.
 */
// SURUM değişince eski önbellek `activate`'te silinir. v1 statik dosyaları
// ÖNCE ÖNBELLEKTEN veriyordu ve hiç tazelemiyordu: SW'yi bir kez kurmuş
// telefon uygulama.js/stil.css'in eski hâlinde sonsuza dek kalıyordu
// (2026-09-21'de aktarım ekranı ve eşleştirme denetimi eklenince fark edildi).
// v3 (2026-09-23): tema sistemi, Keşfet destesi (`kesfet.js`) kabuğa girdi.
// v4 (2026-09-28): İKİ AY teması; eski yazı dosyaları önbellekten silinsin.
// v5 (2026-09-28): çevrimdışı sayfası açıklayıcı ve kendiliğinden yeniden deniyor.
const SURUM = "kesif-v5";
const KABUK = [
  "/statik/stil.css",
  "/statik/uygulama.js",
  "/statik/kesfet.js",
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

  // Statik dosyalar: ÖNCE AĞ, bağlantı yoksa önbellek. "Önce önbellek"
  // bayat dosyayı sonsuza dek sunuyordu; "bayatken sun, arkada tazele"
  // ise yeni HTML'i eski JS ile eşleştirebiliyor. Dosyalar küçük ve sunucu
  // yerel — ağ turunun bedeli önemsiz, tutarlılık önemli.
  if (url.pathname.startsWith("/statik/")) {
    olay.respondWith(
      fetch(istek).then((y) => {
        if (y.ok) {
          const kopya = y.clone();
          caches.open(SURUM).then((c) => c.put(istek, kopya));
        }
        return y;
      // Önce BİREBİR (en son ağdan alınan `?v=<mtime>` kopyası), yoksa
      // sürümsüz kabuk. Doğrudan ignoreSearch ilk eşleşeni, yani kurulumda
      // önbelleklenen ESKİ kabuğu döndürüyordu (sahte SW ortamında ölçüldü).
      }).catch(() => caches.match(istek).then(
        (v) => v || caches.match(istek, { ignoreSearch: true })))
    );
    return;
  }

  // Sayfalar: HER ZAMAN ağdan. Ulaşılamazsa açıklayıcı bir sayfa.
  // Bu sayfa telefonun interneti yokken DE, sunucu (Mac) kapalı ya da
  // uykudayken DE çıkar; ikisini ayırt etmek için `navigator.onLine`
  // sayfanın içinde okunur. Sayfa 15 sn'de bir kendiliğinden yeniden dener.
  olay.respondWith(fetch(istek).catch(() => cevrimdisi()));
});

function cevrimdisi() {
  const govde = `<!doctype html><html lang="tr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Keşif — ulaşılamıyor</title>
<body style="background:#f3efe7;color:#20232c;font:16px/1.6 Georgia,serif;display:grid;
place-items:center;min-height:100vh;margin:0;padding:24px;box-sizing:border-box;text-align:center">
<div style="max-width:26rem">
<h1 style="font-weight:400;font-size:1.5rem;margin:0 0 .6rem" id="b">Sunucuya ulaşılamıyor</h1>
<p id="m" style="color:#4d515c">Keşif Motoru bir bilgisayarda çalışıyor; o bilgisayar şu an uykuda ya da kapalı olabilir. Birkaç dakika içinde kendiliğinden yeniden denenecek.</p>
<p><button onclick="location.reload()" style="font:inherit;background:#bb4628;color:#fff;border:0;
border-radius:999px;padding:.6rem 1.4rem;cursor:pointer">Tekrar dene</button></p>
<p style="color:#6c6f7a;font-size:.9rem" id="e">Server unreachable — the computer running it may be asleep. Retrying automatically.</p>
</div>
<script>
if (!navigator.onLine) {
  document.getElementById("b").textContent = "İnternet bağlantın yok";
  document.getElementById("m").textContent = "Telefonun internete bağlı değil. Bağlanınca sayfa kendiliğinden açılacak.";
  document.getElementById("e").textContent = "You're offline. The page will reload once you're connected.";
  addEventListener("online", () => location.reload());
}
setTimeout(() => location.reload(), 15000);
</script>`;
  return new Response(govde, {
    status: 503, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}
