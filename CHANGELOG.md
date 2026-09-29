# Değişiklik günlüğü

Sürüm numarası `python/__init__.py:__version__` ile aynı tutulur.

## Yayımlanmadı

- Spotify aktarımı önce «Ne kadar geriye gidelim?» diye soruyor: sürgü çekildikçe pencere dışındaki sanatçılar söner, çalma listeleri kaybolur; yalnız pencere içi zevke sayılır. Kendi çalma listelerin de artık okunuyor (yeniden bağlanma gerekebilir). Menüde «Kütüphaneni yeniden aktar».
- Telefon: Keşfet ekrana tam oturuyor (karar düğmeleri alt şeridin arkasında kalmıyor); üst çubuk aşağı kaydırınca çekiliyor; alt sekmeler etkin olanı gösteriyor ve taşınca kenarı soluyor; basılma geri bildirimi; boş sayfalar çizimli.

## 0.2.0 — 2026-09-28 · güçlü kümeleme, pano, çok sesli öneri

- Etkin kümeleme spektral gömmeyle yeniden kuruldu (12 tarz, hepsi bootstrap'ta sağlam); eski PCA çalışması geçersizdi.
- Ses önerisi artık birkaç farklı parçaya dayanıyor (çok sesli kural); ölçümde gizlenen sanatçı iki kat yukarıda.
- Müzisyen önerilerinde ses bağlamı süzgeci (ör. metal davulcuya pop albüm gelmez).
- `scripts/servis.sh yeniden` ve `kanca`: her `git pull`dan sonra sunucu kendiliğinden yenilenir.
- «Senin müziğin» yeniden tasarlandı: kapak mozaiği, renkli tarz kartları, dönem histogramı, rafın yıldızları.
- Kümeleme araması üç yöntemi yarıştırıyor: PCA, spektral gömme, konsensüs; seçim kuralında göreli tolerans.
- Bütün grafikler tek dilde: tarayıcıda, kartın gerçek genişliğinde (Chart.js); yazı ve çizgi her yerde aynı.
- Pano: ses imzası (radar), beğeni oranı seyri, kararlar halkası, tablo görünümü.
- Etkileşimli pano: tarz haritası, tarz seçince bütün grafikler süzülür, tarz paneli.
- Grafikler uygulamanın renkleriyle: her tarzın her yerde aynı rengi var.
- Kümeleme araması (`python -m python.kumeleme.arama`): 220 ayarı ölçüyle kıyaslar.
- «Sayılarla sen» artık bir pano: özet şeridi, tarz netliği, köprüler, keşif karnesi.
- Profilde okunmayan saçılım/ısı haritası yerine «tarzın iki uç arasında nerede» şeritleri.
- Tarz sağlığı: sağlam / karışık / oynak — panoda ve Tarzlar sayfasında uyarı.
- Çevrimdışı sayfası sunucu kapalı mı telefon mu ayırt ediyor, kendiliğinden yeniden deniyor.
- **Sayılarla sen** (`/istatistik`): tarzların netliği ve köprü albümler,
  on yıllar, çeşitlilik, tempo dağılımı, keşif karnesi — her kartta yöntemin adı.
- Gelişmiş sayfalar sekmelerin altına taşındı; menüde yalnız bakım kaldı.
- Müzisyen fotoğrafları (Wikidata/Commons, yoksa Deezer tam ad eşleşmesi).
- Ekranda ham terim kalmadı: «Tekme Payı», Türkçe rol adları, «CLAP» yok.

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
