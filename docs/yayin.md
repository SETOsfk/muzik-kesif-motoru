# Yayın rehberi — v0.1.0

Amaç: uygulamayı bir sunucuda HTTPS ile açmak ve bağlantıyı paylaşmak.
Maliyet 0 TL (K2). Sunucu hesabını açmak kullanıcının işi; geri kalan her
adım aşağıda.

## 1. Sunucu

**Önerilen: Oracle Cloud Always Free — Ampere A1 (ARM), 4 çekirdek, 24 GB.**
Kalıcı disk var (her 👍/👎 SQLite'a yazılıyor; ücretsiz konteyner
platformlarının geçici diski bunu siliyordu — karar günlüğü 2026-09-15).
Aktarım süreci CLAP için ~2 GB bellek istiyor; 24 GB iki eşzamanlı aktarıma
rahat yeter.

- Görüntü: Ubuntu 24.04 (aarch64).
- Güvenlik listesinde 80 ve 443 numaralı bağlantı noktalarını aç.
- Alan adın yoksa IP'yle çalışan ücretsiz ad: `203-0-113-7.sslip.io`
  (IP'ndeki noktalar tire olur).

**Alternatif: kendi Mac'in.** `scripts/servis.sh kur` + `scripts/tunnel.sh`.
Mac kapalıyken uygulama da kapalıdır; hızlı tünelin adresi her açılışta değişir.

## 2. Veriyi paketle (Mac'te)

```bash
scripts/yayin_paketi.sh          # → yayin-verisi.tar.gz (~50 MB)
scp yayin-verisi.tar.gz ubuntu@SUNUCU:~
```

Paket yalnız sunmak için gerekenleri içerir: `ortak.sqlite`, kullanıcı
veritabanları, CLAP gömüleri. Kişisel veri içerir — başka yere yükleme.

Paketsiz de açılır: boş bir sunucuda ilk kullanıcılar kendi listeleriyle
başlar, çalma listesi havuzu onların sanatçılarıyla kurulur. Ses benzerliği
havuzu (`clap_parca`) o zaman boş kalır ve öneriler çalma listesinden gelir.

## 3. Sunucuda kur

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER && newgrp docker

git clone https://github.com/SETOsfk/muzik-kesif-motoru.git && cd muzik-kesif-motoru
tar -xzf ~/yayin-verisi.tar.gz && sudo chown -R 1000:1000 data

cp .env.ornek .env
# .env içinde doldur: ALAN_ADI, KESIF_JETON_ANAHTARI (üretme komutu dosyada yazılı)
docker compose up -d --build
```

İlk derleme ~5–10 dk (torch CPU). Sonra `https://ALAN_ADI` açılır; Caddy
sertifikayı kendisi alır.

Denetim: `curl https://ALAN_ADI/saglik` → `{"durum":"ayakta","surum":"0.1.0"}`

## 4. Spotify (isteğe bağlı)

Spotify panelinde Redirect URI: `https://ALAN_ADI/giris/spotify/donus`.
`.env`: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`,
`KESIF_SPOTIFY_DONUS=https://ALAN_ADI/giris/spotify/donus`.
Development Mode en çok 5 davetli hesap taşır; diğer herkes sanatçı listesiyle
başlar (`/basla`).

## 5. İşletim

| İş | Komut |
|---|---|
| Günlük | `docker compose logs -f kesif` |
| Güncelle | `git pull && docker compose up -d --build` |
| Yedek | `tar -czf yedek-$(date +%F).tar.gz data/db` |
| Hesaplar | `docker compose exec kesif python -m python.hesap listele` |
| Hesap sil | `docker compose exec kesif python -m python.hesap sil --id N` |

Kullanıcılar hesaplarını `/gizlilik` sayfasından kendileri de silebilir.

## 6. Yayından sonra denetim

1. Yeni hesap aç → `/basla` → 15–20 sanatçı yaz → aktarım bitip Keşfet
   destesine geçiyor mu? (Ölçüm: 52 albüm 3,5 dk; 20 sanatçı ≈ 40 albüm.)
2. Kartta 30 sn önizleme çalıyor mu, sağa kaydırınca Listem'e düşüyor mu?
3. Telefonda «Ana ekrana ekle» → tam ekran açılıyor mu (servis çalışanı
   yalnız HTTPS'te kaydolur)?
4. `/gizlilik` → hesabı sil → aynı e-postayla yeniden üye olunabiliyor mu?

## Ortam değişkenleri

| Değişken | Varsayılan | Anlamı |
|---|---|---|
| `ALAN_ADI` | — | Caddy'nin sertifika alacağı ad |
| `KESIF_JETON_ANAHTARI` | — | Spotify jetonlarının şifre anahtarı |
| `KESIF_AZAMI_KULLANICI` | 5 | Hesap tavanı (örnek dosyada 25) |
| `KESIF_ES_ZAMANLI_AKTARIM` | 2 | Aynı anda en çok kaç aktarım |
| `KESIF_ILETISIM` | — | Gizlilik sayfasındaki iletişim adresi |
| `KESIF_HTTPS` | compose'da 1 | `secure` çerez; vekil başlığına güven |
