#!/usr/bin/env bash
# Müzik Keşif Motoru — Ücretsiz Cloudflare HTTPS Tüneli
# Telefonda tam ekran PWA ve HTTPS erişimi sağlamak için kullanılır (0 TL).

PORT="${1:-8800}"

echo "=========================================================="
echo " Müzik Keşif Motoru — Güvenli Mobil Tünel (Cloudflare)"
echo "=========================================================="

if ! command -v cloudflared &> /dev/null; then
    echo "cloudflared bulunamadı. Kurmak için:"
    echo "  brew install cloudflared"
    echo ""
    echo "Alternatif: Yerel Mac IP'nizle test edebilirsiniz,"
    echo "ancak iOS PWA/Service Worker için HTTPS zorunludur."
    exit 1
fi

echo "Sunucu adresi: http://127.0.0.1:$PORT"
echo "Tünel başlatılıyor..."
echo "Aşağıdaki 'https://*.trycloudflare.com' adresini telefonunuzda açın,"
echo "ardından Safari'de 'Paylaş -> Ana Ekrana Ekle' seçeneğini kullanın."
echo "=========================================================="

cloudflared tunnel --url "http://127.0.0.1:$PORT"
