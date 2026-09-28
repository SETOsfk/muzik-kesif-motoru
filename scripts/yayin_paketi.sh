#!/usr/bin/env bash
# Sunucuya taşınacak veriyi paketle — yalnız SUNMAK için gerekenler.
#
#   scripts/yayin_paketi.sh              → yayin-verisi.tar.gz
#
# Ölçüldü (2026-09-15): sunum için ~47 MB yetiyor. Stem önbelleği (1,1 GB)
# ve FMA meta verisi (1,5 GB) çevrimdışı hattın malı, sunucuya gitmez.
# Paket kişisel veri içerir (kullanıcı veritabanları): yalnız kendi
# sunucuna kopyala, başka yere yükleme.
set -euo pipefail

KOK="$(cd "$(dirname "$0")/.." && pwd)"
CIKTI="${1:-$KOK/yayin-verisi.tar.gz}"
cd "$KOK"

for gerekli in data/db/ortak.sqlite data/db/kullanici; do
  [[ -e "$gerekli" ]] || { echo "Eksik: $gerekli" >&2; exit 1; }
done

# Tutarlı anlık kopya: SQLite dosyası yazılırken kopyalanırsa bozuk gelebilir.
GECICI="$(mktemp -d)"
trap 'rm -rf "$GECICI"' EXIT
mkdir -p "$GECICI/data/db/kullanici" "$GECICI/data/cache"
sqlite3 data/db/ortak.sqlite ".backup '$GECICI/data/db/ortak.sqlite'"
for db in data/db/kullanici/*.sqlite; do
  sqlite3 "$db" ".backup '$GECICI/$db'"
done
for klasor in clap clap_parca; do
  [[ -d "data/cache/$klasor" ]] && cp -R "data/cache/$klasor" "$GECICI/data/cache/"
done

tar -czf "$CIKTI" -C "$GECICI" data
echo "Hazır: $CIKTI ($(du -h "$CIKTI" | cut -f1))"
echo "Sunucuda: tar -xzf $(basename "$CIKTI") && sudo chown -R 1000:1000 data"
