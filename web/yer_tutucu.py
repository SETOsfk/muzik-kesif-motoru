"""Görsel bulunamadığında gösterilen üretken kapak.

## Neden düz bir "resim yok" kutusu değil

Keşfet destesi görsel üzerinden karar verdiriyor; ölçüldü, etkin çalışmada
adayların bir kısmının Deezer'da karşılığı yok (niş Japon fusion, eski
Türk rock). Hepsine aynı gri kutuyu koymak kartları birbirinin kopyası yapıyor
ve kullanıcı arka arkaya gelen iki kartı ayırt edemiyor.

Burada kapak SANATÇI ADINDAN türüyor: aynı sanatçı her yerde aynı kapağı alır
(deste, Listem, Öneriler), farklı sanatçılar farklı. İKİ AY temasında
(2026-09-28) kapak bir kitap kapağı gibi: düz renk alanı, ortada tek bir
nesne — ay ve ufuk, ufuktan doğan plak, kuyu, tarlada bir kapı.

## Tema uyumu

SVG satır içi (inline) basılıyor ve renkleri `style="…var(--kapak-N)…"` ile
CSS değişkenlerinden alıyor — `<img>` olarak yüklenseydi sayfanın
değişkenlerini göremezdi. Renk sayısı stil.css'teki `--kapak-N` tokenlarıyla
aynı (`KAPAK_SAYISI`); biri değişirse öteki de.
"""

from __future__ import annotations

import hashlib
import html
import itertools

from markupsafe import Markup

#: stil.css'teki `--kapak-0` … `--kapak-8`.
KAPAK_SAYISI = 9
#: Koyu zeminler (açık yazı) ve açık zeminler (koyu yazı) — stil.css ile aynı.
_KOYU = (0, 1, 6, 7)
_ACIK = (2, 3, 4, 5, 8)

#: Clip kimlikleri sayfada BENZERSİZ olmalı. Aynı sanatçının kapağı bir
#: sayfada birden çok kez basılabiliyor ve `url(#id)` belgedeki İLK tanımı
#: kullanıyor.
_SAYAC = itertools.count()


def _ozet(sanatci: str) -> bytes:
    return hashlib.sha1((sanatci or "?").lower().encode("utf-8")).digest()


def kapak_sirasi(sanatci: str) -> int:
    """Sanatçının kapak rengi (0 … KAPAK_SAYISI-1). Destede kartın zemini bu."""
    return _ozet(sanatci)[0] % KAPAK_SAYISI


def _yer_tutucu_sirasi(ozet: bytes) -> int:
    """Yer tutucunun rengi kartınkinin KARŞIT parlaklığından: kartın içinde
    kaybolmasın (koyu kartta açık kapak, açık kartta koyu kapak)."""
    grup = _ACIK if ozet[0] % KAPAK_SAYISI in _KOYU else _KOYU
    return grup[ozet[5] % len(grup)]


def _bas_harfler(ad: str) -> str:
    parcalar = [p for p in ad.replace("&", " ").split() if p[:1].isalnum()]
    if not parcalar:
        return "♪"
    if len(parcalar) == 1:
        return parcalar[0][:2].upper()
    return (parcalar[0][0] + parcalar[1][0]).upper()


def _nesne(motif: int, ozet: bytes, clip: str) -> str:
    """Kapaktaki tek nesne. Renkler: `m` yazı rengi, `a` vurgu (koyu zeminde
    ay sarısı, açık zeminde kiremit). `clip` ufkun üstünü kesen yol."""
    x = 150 + ozet[3] % 100
    y = 160 + ozet[4] % 40
    if motif == 0:      # ay ve ufuk
        return (f'<rect y="300" width="400" height="100" style="fill:var(--m);fill-opacity:.14"/>'
                f'<rect y="299" width="400" height="2" style="fill:var(--m);fill-opacity:.6"/>'
                f'<circle cx="{x}" cy="{y}" r="78" style="fill:var(--a)"/>'
                f'<circle cx="{x + 112}" cy="{y - 84}" r="17" style="fill:var(--m);fill-opacity:.55"/>')
    if motif == 1:      # ufuktan doğan plak
        oluk = "".join(f'<circle cx="{x}" cy="300" r="{r}"/>' for r in (104, 88, 72, 56))
        return (f'<g clip-path="url(#yt-{clip})">'
                f'<circle cx="{x}" cy="300" r="120" style="fill:var(--m)"/>'
                f'<g style="fill:none;stroke:var(--z);stroke-opacity:.28;stroke-width:1.5">{oluk}</g>'
                f'<circle cx="{x}" cy="300" r="34" style="fill:var(--a)"/></g>'
                f'<rect y="299" width="400" height="2" style="fill:var(--m);fill-opacity:.6"/>')
    if motif == 2:      # kuyu: karanlık ağız, suda ayın yansıması
        return (f'<circle cx="200" cy="{y + 20}" r="112" style="fill:none;stroke:var(--m);stroke-width:3"/>'
                f'<circle cx="200" cy="{y + 20}" r="96" style="fill:var(--m)"/>'
                f'<circle cx="{170 + ozet[6] % 60}" cy="{y}" r="14" style="fill:var(--a)"/>')
    # tarlada bir kapı
    return (f'<rect y="320" width="400" height="2" style="fill:var(--m);fill-opacity:.6"/>'
            f'<rect x="{x - 50}" y="130" width="100" height="190" style="fill:var(--m)"/>'
            f'<rect x="{x - 38}" y="142" width="76" height="178" style="fill:var(--z);fill-opacity:.18"/>'
            f'<circle cx="{x + 30}" cy="232" r="6" style="fill:var(--a)"/>'
            f'<circle cx="{(x + 170) % 330 + 35}" cy="84" r="20" style="fill:var(--a)"/>')


def yer_tutucu_svg(sanatci: str, eser: str = "", *, sinif: str = "yer-tutucu") -> Markup:
    """Sanatçıya özgü, temaya uyan kare kapak (inline SVG)."""
    ozet = _ozet(sanatci)
    renk = _yer_tutucu_sirasi(ozet)
    aksan = "--ay" if renk in _KOYU else "--vurgu"
    clip = f"{ozet.hex()[:8]}-{next(_SAYAC)}"
    harfler = html.escape(_bas_harfler(sanatci or ""))
    alt = html.escape(f"{sanatci} — {eser}" if eser else sanatci or "")

    svg = (f'<svg class="{sinif}" viewBox="0 0 400 400" role="img" '
           f'aria-label="{alt} (kapak bulunamadı)" preserveAspectRatio="xMidYMid slice" '
           f'style="--z:var(--kapak-{renk});--m:var(--kapak-{renk}-metin);--a:var({aksan})">'
           f'<defs><clipPath id="yt-{clip}"><rect width="400" height="300"/></clipPath></defs>'
           f'<rect width="400" height="400" style="fill:var(--z)"/>'
           f'{_nesne(ozet[2] % 4, ozet, clip)}'
           f'<text x="30" y="58" style="fill:var(--m);font:500 26px var(--font-etiket);'
           f'letter-spacing:.14em">{harfler}</text></svg>')
    return Markup(svg)
