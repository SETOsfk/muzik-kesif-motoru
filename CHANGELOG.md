# Değişiklik günlüğü

Sürüm numarası `python/__init__.py:__version__` ile aynı tutulur.

## 0.1.0 — 2026-09-28 · ilk yayın sürümü

Herkesin kullanabileceği ilk sürüm: hesap aç, sevdiğin sanatçıları yaz,
kaydırarak keşfet.

**Yeni**
- **Spotify'sız başlangıç.** `/basla`da satır başına bir sanatçı (ya da
  «Sanatçı — Albüm»); her sanatçının en bilinen iki albümü sesten dinlenir.
  Spotify Development Mode'un beş hesap sınırı artık giriş kapısı değil.
- **Gizlilik sayfası** (`/gizlilik`, oturumsuz açık): ne saklanıyor, ne
  dışarı gidiyor. Kullanıcı hesabını ve kişisel verisini tek adımda siler.
- **Dağıtım paketi:** `Dockerfile`, `docker-compose.yml` + Caddy (otomatik
  HTTPS), `scripts/yayin_paketi.sh`, rehber `docs/yayin.md`.
- Hesap tavanı ve eşzamanlı aktarım sayısı ortam değişkeniyle
  (`KESIF_AZAMI_KULLANICI`, `KESIF_ES_ZAMANLI_AKTARIM`).
- Sürüm `/saglik` yanıtında ve sistem menüsünde.

**Düzeltmeler**
- Temiz kurulumda testler düşüyordu: `python-multipart` (form ayrıştırma) ve
  `httpx` (test istemcisi) bağımlılıklarda yoktu.
- Deezer'a ulaşılamazken aktarım her sanatçıda ~30 sn sessizce bekliyordu;
  art arda üç hatada açık bir mesajla duruyor.
- Ölen aktarım süreci zombi kalıp "çalışıyor" sayılıyordu (bellek yetmezliğinde
  kullanıcı sonsuza dek bekler, eşzamanlılık yuvası dolu kalırdı); artık biçiliyor.
- Aktarım başlatıldığı an durum yazılıyor: dönüşte form değil ilerleme görünüyor,
  çift tıklama ikinci süreç açmıyor.
- Temsilci seçimi testi FCM küme numarasına bağlıydı (numpy sürümüne göre
  düşüyordu); küme artık ölçülerek seçiliyor.

**Sınırlar (bilinen)**
- Liste ya da Spotify ile gelen kütüphanede eksenler yalnız sesten çıkar;
  kredi grafiği ve icra ölçümü yerel FLAC kütüphanesi ister.
- Aktarım mesajları yalnız Türkçe.

285 test geçiyor.
