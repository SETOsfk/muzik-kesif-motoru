"""Grafik paleti — tek kaynak.

Grafikler 2026-09-28'den beri SUNUCUDA ÇİZİLMİYOR. Önceden burada elle SVG
üretiliyordu (K15); SVG viewBox'la ölçeklendiği için aynı yazı bir kartta
9, ötekinde 17 piksel çıkıyor, çizgi kalınlıkları grafikten grafiğe
değişiyordu. Artık sunucu yalnız JSON TANIMI üretir (`web/sunucu.py`) ve
`web/statik/grafikler.js` onu Chart.js ile kartın gerçek genişliğinde çizer
(kütüphane `web/statik/vendor/`, MIT; dış sunucuya bağlanmaz).

Burada kalan: renkler. Tanımlara buradan girer; nötrler (metin, ızgara)
grafikler.js'te doğrudan stil.css tokenlarından okunur.
"""

from __future__ import annotations

#: stil.css'teki İKİ AY tokenlarıyla AYNI (SVG sayfanın değişkenlerini `fill`
#: özniteliğinde okuyamıyor; bkz. modül başlığı). Biri değişirse öteki de.
PALET = {
    "vurgu": "#bb4628",      # --vurgu (eylem)
    "ikincil": "#2e3a66",    # --ikincil (ölçüm)
    "mor": "#6a5a86",
    "yesil": "#3b6b50",
    "kirmizi": "#973131",
    "kenar": "#dcd4c6",
    "izgara": "#eae4d8",
    "metin": "#20232c",
    "soluk": "#4d515c",
    "cok_soluk": "#6c6f7a",
}

#: Tarz renkleri — İKİ AY kapak tonlarının grafik için ayarlanmış akrabaları
#: (gece, kiremit, çam, hardal, erik, gök, zeytin, gül). OKLCH'de açıklık
#: 0,45–0,74, doygunluk ≥ 0,11; sıra komşu iki rengin renk körlüğünde de
#: ayrışacağı biçimde (dataviz doğrulayıcısı, 2026-09-28: CVD ΔE ≥ 8,1,
#: normal görüş ΔE ≥ 22,9). Hardal ve gülün kâğıt üstünde karşıtlığı 3:1'in
#: altında — bu yüzden her renkli işaretin yanında yazılı etiket var.
#: Renk tarzın BÜYÜKLÜK sırasından gelir ve bir çalışma boyunca sabittir;
#: süzgeç değişince yeniden boyanmaz. Dokuzuncu tarz ve sonrası «diğer» gri.
TARZ_RENKLERI = [
    "#3a5095", "#d26b46", "#006e4a", "#c69f32",
    "#884783", "#0097b1", "#495800", "#dc7d94",
]
DIGER = "#9a9ca3"
KATEGORIK = TARZ_RENKLERI


def tarz_rengi(sira: int | None) -> str:
    return TARZ_RENKLERI[sira] if sira is not None and 0 <= sira < len(TARZ_RENKLERI) else DIGER
