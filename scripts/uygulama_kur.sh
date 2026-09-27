#!/usr/bin/env bash
# Keşif.app — tek tıkla açılan macOS uygulaması (2026-09-23).
#
#   scripts/uygulama_kur.sh          ~/Applications/Keşif.app kur (ya da güncelle)
#   scripts/uygulama_kur.sh kaldir   uygulamayı sil
#
# Uygulama ne yapar: sunucu ayakta mı bakar (`/saglik`), değilse launchd
# servisini başlatır ve hazır olmasını bekler; sonra Keşfet'i Chrome'un adres
# çubuğu olmayan uygulama penceresinde açar (Chrome yoksa varsayılan
# tarayıcıda). Dock'a sürüklenebilir, Spotlight'ta "Keşif" diye bulunur.
#
# İkon `scripts/ikon_uret.py`den (Neon). Kod imzası yok: yerelde üretildiği
# için karantina bayrağı taşımaz ve Gatekeeper sormaz.
set -euo pipefail

KOK="$(cd "$(dirname "$0")/.." && pwd)"
UYGULAMA="$HOME/Applications/Keşif.app"
PORT="${KESIF_PORT:-8800}"

if [[ "${1:-}" == "kaldir" ]]; then
  rm -rf "$UYGULAMA" && echo "Kaldırıldı: $UYGULAMA"
  exit 0
fi

# --- ikon ------------------------------------------------------------------
IKON_PNG="$KOK/data/ikon/ikon-1024-mac.png"
[[ -f "$IKON_PNG" ]] || "$KOK/.venv/bin/python" "$KOK/scripts/ikon_uret.py"
GECICI="$(mktemp -d)"
trap 'rm -rf "$GECICI"' EXIT
SET="$GECICI/AppIcon.iconset"
mkdir -p "$SET"
for b in 16 32 128 256 512; do
  sips -z "$b" "$b" "$IKON_PNG" --out "$SET/icon_${b}x${b}.png" >/dev/null
  sips -z $((b * 2)) $((b * 2)) "$IKON_PNG" --out "$SET/icon_${b}x${b}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o "$GECICI/AppIcon.icns"

# --- paket -----------------------------------------------------------------
rm -rf "$UYGULAMA"
mkdir -p "$UYGULAMA/Contents/MacOS" "$UYGULAMA/Contents/Resources"
cp "$GECICI/AppIcon.icns" "$UYGULAMA/Contents/Resources/AppIcon.icns"

cat > "$UYGULAMA/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Keşif</string>
  <key>CFBundleDisplayName</key><string>Keşif</string>
  <key>CFBundleIdentifier</key><string>com.kesif.motoru.uygulama</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>kesif</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

# Başlatıcı. Mutlak yollar: Finder'dan açılan uygulamanın PATH'i kısıtlı.
cat > "$UYGULAMA/Contents/MacOS/kesif" <<BETIK
#!/bin/bash
PORT=$PORT
KOK="$KOK"
URL="http://127.0.0.1:\$PORT/kesfet"
saglikli() { /usr/bin/curl -s -m 1 "http://127.0.0.1:\$PORT/saglik" | /usr/bin/grep -q ayakta; }

if ! saglikli; then
  # Servis kuruluysa yeniden başlat, değilse kur; en çok ~10 sn bekle.
  /bin/launchctl kickstart -k "gui/\$(/usr/bin/id -u)/com.kesif.motoru" 2>/dev/null \\
    || "\$KOK/scripts/servis.sh" kur >/dev/null 2>&1
  for _ in \$(/usr/bin/seq 1 40); do saglikli && break; /bin/sleep 0.25; done
fi

if saglikli; then
  if [ -d "/Applications/Google Chrome.app" ]; then
    exec /usr/bin/open -na "Google Chrome" --args --app="\$URL"
  fi
  exec /usr/bin/open "\$URL"
fi
/usr/bin/osascript -e 'display alert "Keşif açılamadı" message "Sunucu başlatılamadı. Günlüğe bak: data/log/sunucu.log" as critical' >/dev/null
BETIK
chmod +x "$UYGULAMA/Contents/MacOS/kesif"

# Spotlight ve Finder ikonu hemen görsün.
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$UYGULAMA" 2>/dev/null || true
touch "$UYGULAMA"
echo "Kuruldu: $UYGULAMA"
