"""Görsel bulunamadığında gösterilen üretken kapak.

## Neden düz bir "resim yok" kutusu değil

Keşfet destesi görsel üzerinden karar verdiriyor; ölçüldü, etkin çalışmada
adayların bir kısmının Deezer'da karşılığı yok (niş Japon fusion, eski
Türk rock). Hepsine aynı gri kutuyu koymak kartları birbirinin kopyası yapıyor
ve kullanıcı arka arkaya gelen iki kartı ayırt edemiyor.

Burada kapak SANATÇI ADINDAN türüyor: aynı sanatçı her yerde aynı kapağı alır
(deste, Listem, Öneriler), farklı sanatçılar farklı. Motif müzikten: bir dalga
formu (çubuk yükseklikleri addan) ve plak halkaları.

## Tema uyumu

SVG satır içi (inline) basılıyor ve renkleri `style="…var(--vurgu)…"` ile
CSS değişkenlerinden alıyor — `<img>` olarak yüklenseydi sayfanın
değişkenlerini göremezdi. Böylece Neon'da macenta/camgöbeği, Kâğıt'ta
mürekkep kırmızısı çıkar; tema değişince kapak da değişir.
"""

from __future__ import annotations

import hashlib
import html
import itertools

from markupsafe import Markup

#: Renk çiftleri — tema değişkenleri. Addan biri seçilir.
_CIFTLER = (
    ("--vurgu", "--ikincil"),
    ("--mor", "--vurgu"),
    ("--ikincil", "--yesil"),
    ("--vurgu-2", "--mor"),
    ("--yesil", "--ikincil"),
)


#: Gradyan kimlikleri sayfada BENZERSİZ olmalı. Aynı sanatçının kapağı bir
#: sayfada birden çok kez basılabiliyor (Görünüm sayfası altı kez) ve
#: `url(#id)` belgedeki İLK tanımı kullanıyor: tanım ilk temanın bölümünde
#: durduğu için altı önizlemenin altısı da ilk temanın renklerini alıyordu.
_SAYAC = itertools.count()


def _bas_harfler(ad: str) -> str:
    parcalar = [p for p in ad.replace("&", " ").split() if p[:1].isalnum()]
    if not parcalar:
        return "♪"
    if len(parcalar) == 1:
        return parcalar[0][:2].upper()
    return (parcalar[0][0] + parcalar[1][0]).upper()


def yer_tutucu_svg(sanatci: str, eser: str = "", *, sinif: str = "yer-tutucu") -> Markup:
    """Sanatçıya özgü, temaya uyan kare kapak (inline SVG)."""
    ozet = hashlib.sha1((sanatci or "?").lower().encode("utf-8")).digest()
    a, b = _CIFTLER[ozet[0] % len(_CIFTLER)]
    aci = (ozet[1] % 8) * 45
    kimlik = f"{ozet.hex()[:8]}-{next(_SAYAC)}"

    # Dalga formu: 28 çubuk, yükseklikler addan. Kenarlara doğru sönümlü —
    # gerçek bir parçanın zarfı gibi, düz bir çubuk grafik gibi değil.
    cubuklar = []
    for i in range(28):
        bayt = ozet[(i + 2) % len(ozet)] ^ ozet[(i * 7) % len(ozet)]
        zarf = 1 - abs(i - 13.5) / 16
        h = 18 + (bayt / 255) * 120 * zarf
        x = 22 + i * 12.6
        cubuklar.append(
            f'<rect x="{x:.1f}" y="{300 - h / 2:.1f}" width="6.4" height="{h:.1f}" rx="3.2"/>'
        )

    halka_x = 110 + ozet[3] % 180
    halka_y = 90 + ozet[4] % 70
    harfler = html.escape(_bas_harfler(sanatci or ""))
    alt = html.escape(f"{sanatci} — {eser}" if eser else sanatci or "")

    svg = f"""<svg class="{sinif}" viewBox="0 0 400 400" role="img" aria-label="{alt} (kapak bulunamadı)" preserveAspectRatio="xMidYMid slice">
<defs>
<linearGradient id="yt-{kimlik}" gradientTransform="rotate({aci} .5 .5)">
<stop offset="0" style="stop-color:var({a})"/><stop offset="1" style="stop-color:var({b})"/>
</linearGradient>
<radialGradient id="yk-{kimlik}" cx=".5" cy=".5" r=".5">
<stop offset="0" style="stop-color:var(--zemin);stop-opacity:.0"/>
<stop offset="1" style="stop-color:var(--zemin);stop-opacity:.85"/>
</radialGradient>
</defs>
<rect width="400" height="400" style="fill:var(--zemin-2)"/>
<rect width="400" height="400" fill="url(#yt-{kimlik})" opacity=".55"/>
<g style="fill:none;stroke:var(--metin);stroke-opacity:.14">
<circle cx="{halka_x}" cy="{halka_y}" r="150"/><circle cx="{halka_x}" cy="{halka_y}" r="118"/>
<circle cx="{halka_x}" cy="{halka_y}" r="86"/><circle cx="{halka_x}" cy="{halka_y}" r="54"/>
</g>
<circle cx="{halka_x}" cy="{halka_y}" r="18" style="fill:var(--zemin);fill-opacity:.7"/>
<rect width="400" height="400" fill="url(#yk-{kimlik})"/>
<g style="fill:var(--metin);fill-opacity:.82">{''.join(cubuklar)}</g>
<text x="24" y="376" style="fill:var(--metin);font:700 44px var(--font-baslik);letter-spacing:.02em">{harfler}</text>
</svg>"""
    return Markup(svg)
