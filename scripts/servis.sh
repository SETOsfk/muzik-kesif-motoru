#!/usr/bin/env bash
# Keşif Motoru — yerel servis (macOS launchd). 0 TL "ayakta tutma".
#
#   scripts/servis.sh kur      oturum açılınca başlasın, çökerse yeniden kalksın
#   scripts/servis.sh kaldir   servisi durdur ve kaldır
#   scripts/servis.sh durum    çalışıyor mu, sağlık ucu ne diyor
#   scripts/servis.sh gunluk   son 50 satır sunucu günlüğü
#   scripts/servis.sh yedek    kullanıcı ve ortak veritabanlarının anlık yedeği
#
# Neden launchd: Mac zaten açık duruyor; ayrı bir sunucu (Oracle, VPS) yayın
# kararı gerektiriyor ve o karar ertelendi (CLAUDE.md, "Yayın"). launchd
# `KeepAlive` ile süreç ölürse yeniden başlatır; `/saglik` veritabanını da
# denetlediği için "süreç ayakta ama DB kilitli" durumu da görünür.
#
# Telefondan erişim için https gerekir (servis çalışanı): scripts/tunnel.sh.
set -euo pipefail

KOK="$(cd "$(dirname "$0")/.." && pwd)"
ETIKET="com.kesif.motoru"
PLIST="$HOME/Library/LaunchAgents/$ETIKET.plist"
PORT="${KESIF_PORT:-8800}"
GUNLUK="$KOK/data/log/sunucu.log"

kur() {
  mkdir -p "$(dirname "$PLIST")" "$(dirname "$GUNLUK")"
  cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$ETIKET</string>
  <key>WorkingDirectory</key><string>$KOK</string>
  <key>ProgramArguments</key>
  <array>
    <string>$KOK/.venv/bin/python</string><string>-m</string><string>web.sunucu</string>
    <string>--host</string><string>127.0.0.1</string>
    <string>--port</string><string>$PORT</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$GUNLUK</string>
  <key>StandardErrorPath</key><string>$GUNLUK</string>
</dict>
</plist>
PLIST
  launchctl bootout "gui/$(id -u)/$ETIKET" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  echo "Kuruldu: http://127.0.0.1:$PORT  (günlük: $GUNLUK)"
}

kaldir() {
  launchctl bootout "gui/$(id -u)/$ETIKET" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Kaldırıldı."
}

durum() {
  if launchctl print "gui/$(id -u)/$ETIKET" >/dev/null 2>&1; then
    echo "launchd: yüklü"
  else
    echo "launchd: yüklü değil"
  fi
  curl -s -m 3 "http://127.0.0.1:$PORT/saglik" && echo || echo "sağlık ucu cevap vermiyor"
}

yedek() {
  # sqlite3 .backup WAL'ı da tutarlı biçimde kopyalar; `cp` yarım yazılmış
  # bir sayfayı kopyalayabilirdi.
  local hedef="$KOK/data/yedek/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$hedef/kullanici"
  sqlite3 "$KOK/data/db/ortak.sqlite" ".backup '$hedef/ortak.sqlite'"
  for db in "$KOK"/data/db/kullanici/*.sqlite; do
    sqlite3 "$db" ".backup '$hedef/kullanici/$(basename "$db")'"
  done
  echo "Yedek: $hedef"
}

case "${1:-}" in
  kur) kur ;;
  kaldir) kaldir ;;
  durum) durum ;;
  gunluk) tail -n 50 "$GUNLUK" ;;
  yedek) yedek ;;
  *) sed -n '2,8p' "$0"; exit 1 ;;
esac
