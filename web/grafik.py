"""Grafikler — elle üretilmiş SVG.

## Neden Altair/Vega değil

Streamlit'ten çıkarken grafik katmanı da yeniden seçildi. Üç seçenek vardı:

1. **Vega-Lite + vega-embed** — Altair zaten spec üretiyor, tarayıcıda çizilir.
   Bedeli: ~350 KB JS, ve Vega'nın kendi tipografi/renk varsayımları temanın
   üstüne biniyor. Streamlit'te bunu `altair_temasi()` ile bastırmak zorunda
   kaldık; aynı savaşı tekrar vermek anlamsız.
2. **vl-convert / matplotlib ile sunucuda PNG** — yeni bağımlılık, ve PNG
   yakınlaştırıldığında bulanıklaşıyor.
3. **Elle SVG.** Seçilen. Bağımlılık sıfır, çıktı her ölçekte keskin, her
   pikselin denetimi bizde ve `<title>` ile ipucu bedava geliyor.

Burada çizilen dört grafik türü de basit geometri: yatay çubuk, saçılım, ısı
haritası ve aralık. Karmaşık bir çizim kütüphanesine ihtiyaç duyacak bir şey yok.

## Ortak kurallar

- Tüm ölçüler `viewBox` içinde; sayfa CSS'i genişliği belirler, grafik uyar.
- Renkler `stil.css`teki değişkenlerden gelmez (SVG `currentColor` dışında CSS
  değişkeni miras almıyor); `PALET` burada tekrar tanımlı ve CSS ile aynı.
- Metin `text-anchor` ile hizalanır, `<tspan>` kullanılmaz — kısa etiketler.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass

PALET = {
    "vurgu": "#e0654a",
    "ikincil": "#5b9dbf",
    "mor": "#a97fc4",
    "yesil": "#5fb08c",
    "kirmizi": "#c9576b",
    "kenar": "#2a2f3a",
    "izgara": "#232833",
    "metin": "#e8e9ed",
    "soluk": "#9aa0ae",
    "cok_soluk": "#666c7a",
}

KATEGORIK = [
    "#e0654a", "#5b9dbf", "#e0a34a", "#7fa85f", "#a97fc4", "#d97fa8",
    "#4fb0a5", "#c4a55f", "#7f8fc4", "#c47f7f", "#5f9ec4", "#b0a04f",
]


def _k(metin) -> str:
    """XML kaçışı. Sanatçı adlarında & ve < gerçekten geçiyor."""
    return html.escape(str(metin), quote=True)


def _sayi(deger: float, basamak: int = 2) -> str:
    if deger is None or (isinstance(deger, float) and math.isnan(deger)):
        return "—"
    metin = f"{deger:.{basamak}f}"
    return metin.rstrip("0").rstrip(".") if "." in metin else metin


@dataclass
class Cizim:
    """SVG gövdesi + boyut. Şablon `{{ cizim.svg }}` ile gömer."""

    svg: str

    def __html__(self) -> str:  # Jinja2 autoescape'i atlatır
        return self.svg


def _cerceve(ic: str, genislik: int, yukseklik: int, sinif: str = "") -> Cizim:
    return Cizim(
        f'<svg viewBox="0 0 {genislik} {yukseklik}" class="grafik {sinif}" '
        f'preserveAspectRatio="xMidYMid meet" role="img">{ic}</svg>'
    )


# --------------------------------------------------------------------------- #
# Yatay çubuk
# --------------------------------------------------------------------------- #

def yatay_cubuk(
    satirlar: list[tuple[str, float]],
    *,
    birim: str = "",
    renk: str = PALET["ikincil"],
    basamak: int = 2,
    genislik: int = 640,
) -> Cizim:
    """Etiket + çubuk + değer. En uzun etiket ölçüye göre yer ayırır."""
    if not satirlar:
        return _cerceve("", genislik, 40)

    sira_yuksekligi, ust = 30, 8
    etiket_eni = min(230, max(90, 7 * max(len(a) for a, _ in satirlar)))
    deger_eni = 56
    cubuk_eni = genislik - etiket_eni - deger_eni - 24
    en_buyuk = max((abs(d) for _, d in satirlar if d is not None), default=1) or 1

    parcalar = []
    for i, (etiket, deger) in enumerate(satirlar):
        y = ust + i * sira_yuksekligi
        orta = y + sira_yuksekligi / 2
        uzunluk = 0 if deger is None else abs(deger) / en_buyuk * cubuk_eni
        parcalar.append(
            f'<text x="{etiket_eni}" y="{orta}" text-anchor="end" '
            f'dominant-baseline="central" class="g-etiket">{_k(etiket)}</text>'
            f'<rect x="{etiket_eni + 12}" y="{y + 7}" width="{uzunluk:.1f}" '
            f'height="{sira_yuksekligi - 14}" rx="3" fill="{renk}" opacity="0.85"/>'
            f'<text x="{etiket_eni + 20 + uzunluk:.1f}" y="{orta}" '
            f'dominant-baseline="central" class="g-deger">'
            f"{_sayi(deger, basamak)}{_k(birim)}</text>"
        )
    return _cerceve(
        "".join(parcalar), genislik, ust * 2 + len(satirlar) * sira_yuksekligi
    )


# --------------------------------------------------------------------------- #
# Aralık grafiği (Wilson güven aralıkları)
# --------------------------------------------------------------------------- #

def aralik(
    satirlar: list[tuple[str, float, float, float, str]],
    *,
    genislik: int = 640,
    alan: tuple[float, float] = (0.0, 1.0),
) -> Cizim:
    """(etiket, nokta, alt, üst, ipucu) — oranlar ve belirsizlikleri.

    Nokta tahminini tek başına göstermek yanıltıcı olurdu: 1/1 ile 80/80 aynı
    noktada durur ama biri hiçbir şey söylemez. Aralık genişliği bunu gözle
    görülür kılıyor.
    """
    if not satirlar:
        return _cerceve("", genislik, 40)

    sira, ust, alt_bosluk = 34, 10, 30
    etiket_eni = min(200, max(100, 7.2 * max(len(s[0]) for s in satirlar)))
    # Sağda değer etiketi için yer: "%100" dört karakter ve aralığın üst sınırı
    # 1.0 olduğunda etiket eksenin sağ ucunda başlıyor. Ölçüldü — 40 px ile
    # "%100" kırpılıp "%'" görünüyordu.
    deger_eni = 52
    eksen_eni = genislik - etiket_eni - deger_eni - 24
    a0, a1 = alan
    olcek = lambda d: etiket_eni + 16 + (d - a0) / (a1 - a0) * eksen_eni  # noqa: E731

    parcalar = []
    for pay in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = olcek(a0 + pay * (a1 - a0))
        parcalar.append(
            f'<line x1="{x:.1f}" y1="{ust}" x2="{x:.1f}" '
            f'y2="{ust + len(satirlar) * sira}" stroke="{PALET["izgara"]}"/>'
            f'<text x="{x:.1f}" y="{ust + len(satirlar) * sira + 18}" '
            f'text-anchor="middle" class="g-eksen">%{pay * 100:.0f}</text>'
        )

    for i, (etiket, nokta, alt, ustd, ipucu) in enumerate(satirlar):
        y = ust + i * sira + sira / 2
        parcalar.append(
            f"<g><title>{_k(ipucu)}</title>"
            f'<text x="{etiket_eni}" y="{y}" text-anchor="end" '
            f'dominant-baseline="central" class="g-etiket">{_k(etiket)}</text>'
            f'<line x1="{olcek(alt):.1f}" y1="{y}" x2="{olcek(ustd):.1f}" y2="{y}" '
            f'stroke="{PALET["ikincil"]}" stroke-width="3" opacity="0.4" '
            f'stroke-linecap="round"/>'
            f'<circle cx="{olcek(nokta):.1f}" cy="{y}" r="5.5" '
            f'fill="{PALET["ikincil"]}"/>'
            f'<text x="{min(olcek(ustd) + 10, genislik - deger_eni + 4):.1f}" '
            f'y="{y}" dominant-baseline="central" '
            f'class="g-deger">%{nokta * 100:.0f}</text>'
            f"</g>"
        )
    return _cerceve(
        "".join(parcalar), genislik, ust + len(satirlar) * sira + alt_bosluk
    )


# --------------------------------------------------------------------------- #
# Saçılım
# --------------------------------------------------------------------------- #

def sacilim(
    noktalar: list[tuple[float, float, str, str]],
    *,
    x_baslik: str,
    y_baslik: str,
    genislik: int = 720,
    yukseklik: int = 420,
) -> Cizim:
    """(x, y, grup, ipucu) — grup renklendirir, ipucu `<title>` olur.

    289 nokta SVG'de sorunsuz; Vega'nın canvas'ına gerek yok ve her nokta
    tarayıcının kendi ipucu mekanizmasıyla okunabiliyor.
    """
    if not noktalar:
        return _cerceve("", genislik, 60)

    sol, sag, ustb, altb = 52, 16, 14, 44
    ic_en = genislik - sol - sag
    ic_boy = yukseklik - ustb - altb

    xs = [n[0] for n in noktalar]
    ys = [n[1] for n in noktalar]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    x0, x1 = (x0 - (x1 - x0) * 0.05, x1 + (x1 - x0) * 0.05) if x1 > x0 else (x0 - 1, x1 + 1)
    y0, y1 = (y0 - (y1 - y0) * 0.05, y1 + (y1 - y0) * 0.05) if y1 > y0 else (y0 - 1, y1 + 1)

    kx = lambda v: sol + (v - x0) / (x1 - x0) * ic_en  # noqa: E731
    ky = lambda v: ustb + ic_boy - (v - y0) / (y1 - y0) * ic_boy  # noqa: E731

    gruplar = sorted({n[2] for n in noktalar})
    renk = {g: KATEGORIK[i % len(KATEGORIK)] for i, g in enumerate(gruplar)}

    parcalar = []
    for pay in (0, 0.25, 0.5, 0.75, 1.0):
        gx, gy = kx(x0 + pay * (x1 - x0)), ky(y0 + pay * (y1 - y0))
        parcalar.append(
            f'<line x1="{gx:.1f}" y1="{ustb}" x2="{gx:.1f}" y2="{ustb + ic_boy}" '
            f'stroke="{PALET["izgara"]}"/>'
            f'<text x="{gx:.1f}" y="{ustb + ic_boy + 17}" text-anchor="middle" '
            f'class="g-eksen">{_sayi(x0 + pay * (x1 - x0))}</text>'
            f'<line x1="{sol}" y1="{gy:.1f}" x2="{sol + ic_en}" y2="{gy:.1f}" '
            f'stroke="{PALET["izgara"]}"/>'
            f'<text x="{sol - 8}" y="{gy:.1f}" text-anchor="end" '
            f'dominant-baseline="central" class="g-eksen">'
            f"{_sayi(y0 + pay * (y1 - y0))}</text>"
        )

    for x, y, grup, ipucu in noktalar:
        parcalar.append(
            f'<circle cx="{kx(x):.1f}" cy="{ky(y):.1f}" r="4.5" '
            f'fill="{renk[grup]}" opacity="0.72" class="g-nokta">'
            f"<title>{_k(ipucu)}</title></circle>"
        )

    parcalar.append(
        f'<text x="{sol + ic_en / 2:.0f}" y="{yukseklik - 8}" '
        f'text-anchor="middle" class="g-baslik">{_k(x_baslik)}</text>'
        f'<text x="14" y="{ustb + ic_boy / 2:.0f}" text-anchor="middle" '
        f'class="g-baslik" transform="rotate(-90 14 {ustb + ic_boy / 2:.0f})">'
        f"{_k(y_baslik)}</text>"
    )
    return _cerceve("".join(parcalar), genislik, yukseklik, sinif="genis")


def sacilim_efsanesi(gruplar: list[str]) -> str:
    """Saçılımın renk açıklaması — HTML, SVG değil (metin akışına girsin)."""
    parcalar = []
    for i, grup in enumerate(sorted(gruplar)):
        renk = KATEGORIK[i % len(KATEGORIK)]
        parcalar.append(
            f'<span class="efsane"><i style="background:{renk}"></i>'
            f"{_k(grup)}</span>"
        )
    return "".join(parcalar)


# --------------------------------------------------------------------------- #
# Isı haritası
# --------------------------------------------------------------------------- #

def isi_haritasi(
    satir_adlari: list[str],
    sutun_adlari: list[str],
    degerler: dict[tuple[str, str], float],
    *,
    ipuclari: dict[tuple[str, str], str] | None = None,
    genislik: int = 760,
) -> Cizim:
    """Sapma haritası: sıfırın iki yanı farklı renk.

    Sıralı bir renk skalası burada YANLIŞ olurdu — "kütüphane medyanından
    sapma" iki yönlü bir ölçü ve sıfır anlamlı bir orta nokta.
    """
    if not satir_adlari or not sutun_adlari:
        return _cerceve("", genislik, 40)

    etiket_eni = min(210, max(110, 7.2 * max(len(a) for a in satir_adlari)))
    hucre_boy = 30
    alt_bosluk = 78
    hucre_en = max(34, (genislik - etiket_eni - 70) / len(sutun_adlari))
    ust = 6

    en_buyuk = max((abs(d) for d in degerler.values() if d is not None), default=1) or 1

    def boya(deger: float) -> str:
        yogunluk = min(1.0, abs(deger) / en_buyuk)
        temel = PALET["ikincil"] if deger > 0 else PALET["vurgu"]
        return f"{temel}{int(30 + yogunluk * 200):02x}"

    parcalar = []
    for i, satir in enumerate(satir_adlari):
        y = ust + i * hucre_boy
        parcalar.append(
            f'<text x="{etiket_eni}" y="{y + hucre_boy / 2}" text-anchor="end" '
            f'dominant-baseline="central" class="g-etiket">{_k(satir)}</text>'
        )
        for j, sutun in enumerate(sutun_adlari):
            x = etiket_eni + 10 + j * hucre_en
            deger = degerler.get((satir, sutun))
            if deger is None:
                parcalar.append(
                    f'<rect x="{x:.1f}" y="{y}" width="{hucre_en - 2:.1f}" '
                    f'height="{hucre_boy - 2}" rx="3" fill="{PALET["izgara"]}" '
                    f'opacity="0.35"/>'
                )
                continue
            ipucu = (ipuclari or {}).get((satir, sutun), f"{satir} · {sutun}")
            parcalar.append(
                f'<rect x="{x:.1f}" y="{y}" width="{hucre_en - 2:.1f}" '
                f'height="{hucre_boy - 2}" rx="3" fill="{boya(deger)}">'
                f"<title>{_k(ipucu)}</title></rect>"
            )

    taban = ust + len(satir_adlari) * hucre_boy
    for j, sutun in enumerate(sutun_adlari):
        x = etiket_eni + 10 + j * hucre_en + hucre_en / 2
        parcalar.append(
            f'<text x="{x:.1f}" y="{taban + 12}" class="g-eksen" '
            f'text-anchor="end" transform="rotate(-45 {x:.1f} {taban + 12})">'
            f"{_k(sutun)}</text>"
        )
    return _cerceve("".join(parcalar), genislik, taban + alt_bosluk, sinif="genis")


# --------------------------------------------------------------------------- #
# Küçük göstergeler
# --------------------------------------------------------------------------- #

def kiyas_cubugu(deger: float, alt: float, ust: float, *, genislik: int = 190) -> Cizim:
    """Bir değerin iki referans arasındaki yeri — aday ses uzaklığı için.

    "1.24 uzak mı?" sorusunun cevabı tek başına sayıda yok. Kütüphanenin kendi
    dağılımındaki iki nokta (eksenin içi / dışı) referans olarak çizilir.
    """
    yukseklik = 30
    kenar = 8
    en_kucuk = min(alt, ust, deger) * 0.9
    en_buyuk = max(alt, ust, deger) * 1.1
    if en_buyuk <= en_kucuk:
        en_buyuk = en_kucuk + 1
    kx = lambda v: kenar + (v - en_kucuk) / (en_buyuk - en_kucuk) * (genislik - 2 * kenar)  # noqa: E731

    return _cerceve(
        f'<line x1="{kx(en_kucuk):.1f}" y1="15" x2="{kx(en_buyuk):.1f}" y2="15" '
        f'stroke="{PALET["izgara"]}" stroke-width="4" stroke-linecap="round"/>'
        f'<line x1="{kx(alt):.1f}" y1="8" x2="{kx(alt):.1f}" y2="22" '
        f'stroke="{PALET["cok_soluk"]}" stroke-width="2"/>'
        f'<line x1="{kx(ust):.1f}" y1="8" x2="{kx(ust):.1f}" y2="22" '
        f'stroke="{PALET["cok_soluk"]}" stroke-width="2"/>'
        f'<circle cx="{kx(deger):.1f}" cy="15" r="6" fill="{PALET["vurgu"]}"/>',
        genislik, yukseklik, sinif="kiyas",
    )
