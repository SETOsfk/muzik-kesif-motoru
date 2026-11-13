#!/usr/bin/env bash
# Keşif Motoru — tek komutla aç:  ./calistir.sh
#
# Kendi verinle (data/) açar; ilk çalıştırmada sanal ortamı kurar (yalnız
# sunucu bağımlılıkları, torch yok) ve hazır olunca tarayıcıyı açar.
# Kalıcı servis / herkese açık link için: scripts/servis.sh yayinla
set -euo pipefail
cd "$(dirname "$0")"
PORT="${KESIF_PORT:-8800}"

if [[ ! -x .venv/bin/python ]]; then
  echo "İlk kurulum: sanal ortam hazırlanıyor (bir kez, ~1 dk)…"
  python3 -m venv .venv
fi
if ! .venv/bin/python -c "import starlette, uvicorn, jinja2, numpy, pandas, multipart, cryptography" 2>/dev/null; then
  .venv/bin/pip install -q -r requirements-sunucu.txt
fi
[[ -f data/db/ortak.sqlite ]] || echo "Not: data/db/ortak.sqlite yok — boş açılacak; üye olup /basla'dan kütüphane kurabilirsin."

# Zaten çalışıyorsa (ör. servis.sh) ikinci kez başlatma; yalnız aç.
ac() { (command -v open >/dev/null && open "$1") || (command -v xdg-open >/dev/null && xdg-open "$1") || true; }
if curl -fs "http://127.0.0.1:$PORT/saglik" >/dev/null 2>&1; then
  echo "Zaten çalışıyor: http://127.0.0.1:$PORT"; ac "http://127.0.0.1:$PORT"; exit 0
fi
( for _ in $(seq 1 60); do
    curl -fs "http://127.0.0.1:$PORT/saglik" >/dev/null 2>&1 && break; sleep 0.25
  done; ac "http://127.0.0.1:$PORT" ) >/dev/null 2>&1 &
exec .venv/bin/python -m web.sunucu --port "$PORT"
