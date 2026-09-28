#!/usr/bin/env bash
# Keşif Motoru — Mac'te yayın: uygulama Mac'te, link Tailscale'den, yedek Drive'da.
#
#   scripts/servis.sh yayinla    hepsini kur: sunucu + herkese açık link + Drive yedeği
#   scripts/servis.sh durum      çalışıyor mu, link ne, son yedek ne zaman
#   scripts/servis.sh yedek      şimdi yedek al (Drive klasörüne)
#   scripts/servis.sh drivea-tasi büyük arşivleri Drive'a taşı, Mac'te yer aç
#   scripts/servis.sh gunluk     son 50 satır sunucu günlüğü
#   scripts/servis.sh kaldir     her şeyi durdur ve kaldır
#
# Neden bu düzen (karar günlüğü 2026-09-28 (3)): Hugging Face ücretsiz Docker
# barındırmayı kapattı; kullanıcı Mac'i sunucu, Drive'ı depolama olarak seçti.
# Canlı veritabanı Drive'a KONMAZ: Drive yazılmakta olan SQLite dosyasını
# eşitlerse bozabilir. Veri Mac'te, tutarlı anlık kopyası Drive'da.
set -euo pipefail

KOK="$(cd "$(dirname "$0")/.." && pwd)"
ETIKET="com.kesif.motoru"
YEDEK_ETIKET="com.kesif.yedek"
AJANLAR="$HOME/Library/LaunchAgents"
PORT="${KESIF_PORT:-8800}"
GUNLUK="$KOK/data/log/sunucu.log"
GENEL_ADRES=""
#: Drive'da en çok bu kadar yedek tutulur (6 saatte bir → ~1 hafta).
SAKLA=28

# --- Google Drive klasörü -----------------------------------------------------
# "Google Drive for desktop" klasörü: ~/Library/CloudStorage/GoogleDrive-<e-posta>/
# altında "My Drive" (Türkçe arayüzde "Drive'ım"). KESIF_YEDEK_KLASOR ile ezilebilir.
yedek_klasoru() {
  if [[ -n "${KESIF_YEDEK_KLASOR:-}" ]]; then echo "$KESIF_YEDEK_KLASOR"; return; fi
  local kok
  for kok in "$HOME"/Library/CloudStorage/GoogleDrive-*/"My Drive" \
             "$HOME"/Library/CloudStorage/GoogleDrive-*/"Drive'ım"; do
    [[ -d "$kok" ]] && { echo "$kok/Kesif-yedek"; return; }
  done
  echo ""
}

# --- Tailscale ----------------------------------------------------------------
tailscale_cli() {
  if command -v tailscale >/dev/null 2>&1; then echo tailscale
  elif [[ -x /Applications/Tailscale.app/Contents/MacOS/Tailscale ]]; then
    echo /Applications/Tailscale.app/Contents/MacOS/Tailscale
  else echo ""; fi
}

# launchd'de bir ajanı yeniden yükle. `bootout` EŞZAMANSIZ: eski ajan
# kapanmadan `bootstrap` çağrılırsa "Bootstrap failed: 5: Input/output error"
# (ölçüldü 2026-09-28, ikinci `yayinla`). Kapanmasını bekle, gerekirse yeniden dene.
ajan_yukle() {
  local etiket="$1" plist="$2" alan="gui/$(id -u)"
  launchctl bootout "$alan/$etiket" 2>/dev/null || true
  for _ in $(seq 1 40); do
    launchctl print "$alan/$etiket" >/dev/null 2>&1 || break
    sleep 0.25
  done
  for _ in 1 2 3 4 5; do
    launchctl bootstrap "$alan" "$plist" 2>/dev/null && return 0
    sleep 1
  done
  launchctl bootstrap "$alan" "$plist"   # son deneme: hatayı göster
}

sunucu_kur() {
  mkdir -p "$AJANLAR" "$(dirname "$GUNLUK")"
  # Link biliniyorsa Spotify dönüş adresi ona; bilinmiyorsa .env'deki kalır
  # (boş bir değer yazmak .env'dekini ezerdi).
  local SPOTIFY_SATIRI=""
  if [[ -n "$GENEL_ADRES" ]]; then
    SPOTIFY_SATIRI="    <key>KESIF_SPOTIFY_DONUS</key><string>$GENEL_ADRES/giris/spotify/donus</string>"
  fi
  # caffeinate -i -s: Mac boşta uyumasın (pilde de), şarjdayken hiç uyumasın.
  # Kapak kapalıyken yine uyur — o zaman link «sunucuya ulaşılamıyor» der.
  # KESIF_HTTPS=1: link HTTPS; oturum çerezi yalnız şifreli bağlantıda gider.
  cat > "$AJANLAR/$ETIKET.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$ETIKET</string>
  <key>WorkingDirectory</key><string>$KOK</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/caffeinate</string><string>-i</string><string>-s</string>
    <string>$KOK/.venv/bin/python</string><string>-m</string><string>web.sunucu</string>
    <string>--host</string><string>127.0.0.1</string>
    <string>--port</string><string>$PORT</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>KESIF_HTTPS</key><string>1</string>
    <key>KESIF_AZAMI_KULLANICI</key><string>${KESIF_AZAMI_KULLANICI:-25}</string>
$SPOTIFY_SATIRI
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$GUNLUK</string>
  <key>StandardErrorPath</key><string>$GUNLUK</string>
</dict>
</plist>
PLIST
  ajan_yukle "$ETIKET" "$AJANLAR/$ETIKET.plist"
  for _ in $(seq 1 40); do
    curl -s -m 1 "http://127.0.0.1:$PORT/saglik" | grep -q ayakta && { echo "✓ Uygulama çalışıyor"; return; }
    sleep 0.5
  done
  echo "✗ Uygulama açılmadı. Günlük: scripts/servis.sh gunluk" >&2
  exit 1
}

yedek_kur() {
  local klasor
  klasor="$(yedek_klasoru)"
  if [[ -z "$klasor" ]]; then
    echo "✗ Google Drive klasörü bulunamadı. 'Google Drive for desktop' kurulu ve açık mı?" >&2
    echo "  Başka bir klasör için: KESIF_YEDEK_KLASOR=/yol scripts/servis.sh yayinla" >&2
    exit 1
  fi
  cat > "$AJANLAR/$YEDEK_ETIKET.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$YEDEK_ETIKET</string>
  <key>ProgramArguments</key>
  <array><string>$KOK/scripts/servis.sh</string><string>yedek</string></array>
  <key>EnvironmentVariables</key>
  <dict><key>KESIF_YEDEK_KLASOR</key><string>$klasor</string></dict>
  <key>StartInterval</key><integer>21600</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$KOK/data/log/yedek.log</string>
  <key>StandardErrorPath</key><string>$KOK/data/log/yedek.log</string>
</dict>
</plist>
PLIST
  ajan_yukle "$YEDEK_ETIKET" "$AJANLAR/$YEDEK_ETIKET.plist"
  echo "✓ Yedek 6 saatte bir: $klasor"
}

link_ac() {
  local ts
  ts="$(tailscale_cli)"
  if [[ -z "$ts" ]]; then
    echo "✗ Tailscale bulunamadı. App Store'dan 'Tailscale'i kur, aç ve giriş yap." >&2
    exit 1
  fi
  # İlk seferde Tailscale "Funnel'ı etkinleştir" bağlantısı yazdırabilir:
  # çıktı gizlenmiyor, bağlantıya tıklayıp onayladıktan sonra komutu yeniden çalıştır.
  "$ts" funnel --bg "$PORT"
  local ad
  ad="$("$ts" status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
  GENEL_ADRES="https://$ad"
  echo "✓ Link: $GENEL_ADRES"
}

yayinla() {
  # Önce link: Spotify'ın dönüş adresi herkese açık adresten kuruluyor.
  # Eskiden varsayılan http://127.0.0.1:8800/... kalıyordu ve telefondan
  # "Allow"a basan kullanıcı kendi cihazına gönderilip siyah ekran görüyordu.
  link_ac
  sunucu_kur
  yedek_kur
  echo
  echo "Bu linki paylaşabilirsin. Mac şarjda ve kapağı açıkken uygulama açık kalır."
  echo
  echo "Spotify girişi için Spotify panelinde (developer.spotify.com/dashboard →"
  echo "uygulaman → Settings → Redirect URIs) şu adres ekli olmalı:"
  echo "  $GENEL_ADRES/giris/spotify/donus"
}

yedek() {
  local klasor
  klasor="$(yedek_klasoru)"
  [[ -n "$klasor" ]] || klasor="$KOK/data/yedek"
  # sqlite3 .backup WAL'ı da tutarlı biçimde kopyalar; `cp` yarım yazılmış
  # bir sayfayı kopyalayabilirdi. Önce geçici klasöre, bitince yerine:
  # Drive yarım bir yedeği eşitlemesin.
  # Anlık kopya özel karaktersiz geçici klasörde alınır: Türkçe Drive
  # klasörü "Drive'ım" içindeki kesme işareti `.backup '...'` tırnağını bozuyordu.
  local ad gecici
  ad="$(date +%Y%m%d-%H%M%S)"
  gecici="$(mktemp -d)"
  mkdir -p "$gecici/$ad/kullanici" "$klasor"
  sqlite3 "$KOK/data/db/ortak.sqlite" ".backup '$gecici/$ad/ortak.sqlite'"
  for db in "$KOK"/data/db/kullanici/*.sqlite; do
    sqlite3 "$db" ".backup '$gecici/$ad/kullanici/$(basename "$db")'"
  done
  mv "$gecici/$ad" "$klasor/$ad"
  rmdir "$gecici"
  # Aynı zamanlanmış işte: kartlar açılmadan kapak ve sanatçı fotoğraflarını
  # çöz (her kullanıcının son çalışması). Ağ yoksa sessizce geçer.
  (cd "$KOK" && "$KOK/.venv/bin/python" -m python.medya --tum-kullanicilar --limit 300) || true
  # Eskileri sil: en yeni $SAKLA yedek kalsın.
  # (macOS bash 3.2 / BSD araçları: `head -n -N` yok, ters sıralayıp kuyruğu al.)
  ls -1d "$klasor"/20*/ 2>/dev/null | sort -r | tail -n "+$((SAKLA + 1))" | while read -r eski; do rm -rf "$eski"; done
  echo "$(date '+%F %T') yedek: $klasor/$ad"
}

#: Uygulamanın çalışırken HİÇ okumadığı büyük klasörler (ölçüldü 2026-09-15:
#: stemler 1,1 GB, FMA 1,5 GB). Çevrimdışı hat onları yeniden isterse Drive'dan
#: kısayolla okur. Canlı veritabanı (~30 MB) ve gömüler (~18 MB) Mac'te kalır.
ARSIVLER="data/cache/stemler data/dis data/yedek data/cache/onizleme data/raporlar"

drivea_tasi() {
  local drive arsiv
  drive="$(yedek_klasoru)"
  [[ -n "$drive" ]] || { echo "✗ Google Drive klasörü bulunamadı." >&2; exit 1; }
  arsiv="$(dirname "$drive")/Kesif-arsiv"
  mkdir -p "$arsiv"
  echo "Önce: $(du -sh "$KOK/data" | cut -f1) (data/)"
  local yol
  for yol in $ARSIVLER; do
    [[ -d "$KOK/$yol" && ! -L "$KOK/$yol" ]] || continue
    mkdir -p "$arsiv/$(dirname "$yol")"
    echo "  taşınıyor: $yol ($(du -sh "$KOK/$yol" | cut -f1))"
    mv "$KOK/$yol" "$arsiv/$yol"
    ln -s "$arsiv/$yol" "$KOK/$yol"   # kod aynı yolu okumaya devam eder
  done
  # Eski elle yedekler (1.sqlite.mbid-oncesi gibi); -wal/-shm'ye dokunulmaz.
  mkdir -p "$arsiv/eski-veritabanlari"
  find "$KOK/data/db" -name "*.sqlite.*" -type f -exec mv {} "$arsiv/eski-veritabanlari/" \;
  echo "Sonra: $(du -sh "$KOK/data" | cut -f1) (data/) — arşiv: $arsiv"
  echo "İpucu: Drive ayarlarında 'Dosyaları akış olarak aktar' (Stream) seçiliyse"
  echo "arşiv Mac'te yer kaplamaz, yalnız bulutta durur."
}

durum() {
  curl -s -m 3 "http://127.0.0.1:$PORT/saglik" | grep -q ayakta && echo "Uygulama: çalışıyor" || echo "Uygulama: KAPALI"
  local ts
  ts="$(tailscale_cli)"
  if [[ -n "$ts" ]]; then
    "$ts" funnel status 2>/dev/null | head -3
    local genel
    genel="$("$ts" funnel status 2>/dev/null | grep -o 'https://[^ ]*' | head -1)"
    if [[ -n "$genel" ]]; then
      curl -s -m 8 "${genel%/}/saglik" | grep -q ayakta \
        && echo "Genel link: ulaşılıyor ($genel)" \
        || echo "Genel link: ULAŞILAMIYOR — Tailscale açık mı? 'scripts/servis.sh yayinla' yeniden kurar."
    else
      echo "Genel link: Funnel kapalı — 'scripts/servis.sh yayinla'"
    fi
  else
    echo "Tailscale bulunamadı — uygulamayı açıp giriş yap."
  fi
  local klasor
  klasor="$(yedek_klasoru)"
  [[ -n "$klasor" ]] && echo "Son yedek: $(ls -1d "$klasor"/20*/ 2>/dev/null | sort | tail -1)"
}

kaldir() {
  local ts
  ts="$(tailscale_cli)"
  [[ -n "$ts" ]] && "$ts" funnel reset >/dev/null 2>&1 || true
  for e in "$ETIKET" "$YEDEK_ETIKET"; do
    launchctl bootout "gui/$(id -u)/$e" 2>/dev/null || true
    rm -f "$AJANLAR/$e.plist"
  done
  echo "Kaldırıldı (veri ve yedekler yerinde)."
}

case "${1:-}" in
  yayinla) yayinla ;;
  kur) sunucu_kur ;;
  durum) durum ;;
  yedek) yedek ;;
  drivea-tasi) drivea_tasi ;;
  gunluk) tail -n 50 "$GUNLUK" ;;
  kaldir) kaldir ;;
  *) sed -n '2,8p' "$0"; exit 1 ;;
esac
