#!/usr/bin/env bash
# Veriyi bulut oturumunun (Claude Code web) okuyabileceği biçimde Drive'a koy.
#
#   scripts/bulut_paketi.sh [hedef-klasör]
#
# Neden: bulut oturumu Drive'ı okuyabiliyor ama dosya başına 10 MB sınırı var
# (ölçüldü 2026-11-13: ortak.sqlite 28 MB, 1.sqlite 12 MB — ikisi de reddedildi).
# Bu betik yayın paketini (`yayin_paketi.sh`: veritabanları + CLAP gömüleri,
# tutarlı anlık kopya) 9 MB'lık parçalara böler. Birleştirme: cat parca-* > x.tar.gz
#
# Paket KİŞİSEL VERİ içerir; yalnız kendi Drive'ına yazılır.
set -euo pipefail
KOK="$(cd "$(dirname "$0")/.." && pwd)"
HEDEF="${1:-}"
if [[ -z "$HEDEF" ]]; then
  for kok in "$HOME"/Library/CloudStorage/GoogleDrive-*/"My Drive" \
             "$HOME"/Library/CloudStorage/GoogleDrive-*/"Drive'ım"; do
    [[ -d "$kok" ]] && { HEDEF="$kok/Kesif-bulut"; break; }
  done
fi
[[ -n "$HEDEF" ]] || { echo "Drive klasörü bulunamadı; hedefi elle ver: $0 /yol" >&2; exit 1; }
GECICI="$(mktemp -d)"
trap 'rm -rf "$GECICI"' EXIT
"$KOK/scripts/yayin_paketi.sh" "$GECICI/veri.tar.gz"
mkdir -p "$HEDEF"
rm -f "$HEDEF"/kesif-veri-parca-*
split -b 9m "$GECICI/veri.tar.gz" "$HEDEF/kesif-veri-parca-"
echo "Hazır: $HEDEF ($(ls "$HEDEF" | wc -l | tr -d ' ') parça). Drive eşitlenince bulut oturumuna «veri Drive'da» de."
