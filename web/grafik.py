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



def _kisalt(metin: str, azami: int) -> str:
    """Dar grafikte uzun ad: sonu «…» (tam adı ipucu taşır)."""
    metin = str(metin)
    return metin if len(metin) <= azami else metin[: azami - 1].rstrip() + "…"


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
    ipuclari: list[str] | None = None,
    renkler: list[str] | None = None,
    tarzlar: list[int | None] | None = None,
) -> Cizim:
    """Etiket + çubuk + değer. En uzun etiket ölçüye göre yer ayırır.

    `renkler` / `tarzlar` verilirse her satır kendi rengini ve `data-tarz`ını
    taşır (panoda süzgeçle solar)."""
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
        ipucu = f"<title>{_k(ipuclari[i])}</title>" if ipuclari else ""
        veri = f' data-tarz="{tarzlar[i]}"' if tarzlar and tarzlar[i] is not None else ""
        satir_rengi = renkler[i] if renkler else renk
        parcalar.append(
            f'<g class="g-satir"{veri}>{ipucu}'
            f'<rect x="0" y="{y}" width="{genislik}" height="{sira_yuksekligi}" fill="transparent"/>'
            f'<text x="{etiket_eni}" y="{orta}" text-anchor="end" '
            f'dominant-baseline="central" class="g-etiket">{_k(etiket)}</text>'
            f'<rect x="{etiket_eni + 12}" y="{y + 7}" width="{uzunluk:.1f}" '
            f'height="{sira_yuksekligi - 14}" rx="3" fill="{satir_rengi}" opacity="0.9"/>'
            f'<text x="{etiket_eni + 20 + uzunluk:.1f}" y="{orta}" '
            f'dominant-baseline="central" class="g-deger">'
            f"{_sayi(deger, basamak)}{_k(birim)}</text></g>"
        )
    return _cerceve(
        "".join(parcalar), genislik, ust * 2 + len(satirlar) * sira_yuksekligi
    )


# --------------------------------------------------------------------------- #
# Dikey sütunlar (histogram / zaman)
# --------------------------------------------------------------------------- #

def sutunlar(
    satirlar: list[tuple[str, float, str]],
    *,
    vurgu: int | None = None,
    genislik: int = 640,
    yukseklik: int = 200,
    etiket_adimi: int = 1,
) -> Cizim:
    """(x etiketi, değer, ipucu) — tek seri; `vurgu` sıradaki sütun turuncu.

    Tek seri olduğu için efsane yok (başlık adlandırır). Sütunlar tabana
    oturur, üst uçları yuvarlak, aralarında 2 px boşluk; değer yalnız
    vurgulanan sütunun üstünde yazar, gerisi üzerine gelince görünür.
    """
    if not satirlar:
        return _cerceve("", genislik, 40)
    ust, alt = 22, 26
    alan = yukseklik - ust - alt
    en_buyuk = max(d for _, d, _ in satirlar) or 1
    adim = genislik / len(satirlar)
    bosluk = 2 if adim > 6 else 0.5
    taban = ust + alan
    parcalar = [f'<line x1="0" y1="{taban}" x2="{genislik}" y2="{taban}" '
                f'stroke="{PALET["kenar"]}"/>']
    for i, (etiket, deger, ipucu) in enumerate(satirlar):
        x = i * adim + bosluk / 2
        g = adim - bosluk
        h = deger / en_buyuk * alan
        renk = PALET["vurgu"] if i == vurgu else PALET["ikincil"]
        r = min(4, g / 2, h)
        yol = (f"M{x:.1f},{taban} V{taban - h + r:.1f} "
               f"Q{x:.1f},{taban - h:.1f} {x + r:.1f},{taban - h:.1f} "
               f"H{x + g - r:.1f} Q{x + g:.1f},{taban - h:.1f} {x + g:.1f},{taban - h + r:.1f} "
               f"V{taban} Z") if h > 0 else ""
        parcalar.append(
            f'<g class="g-sutun"><title>{_k(ipucu)}</title>'
            f'<rect x="{i * adim:.1f}" y="{ust}" width="{adim:.1f}" height="{alan + alt}" fill="transparent"/>'
            + (f'<path d="{yol}" fill="{renk}" opacity="{1 if i == vurgu else 0.8}"/>' if yol else "")
        )
        if i == vurgu:
            parcalar.append(
                f'<text x="{x + g / 2:.1f}" y="{taban - h - 6:.1f}" text-anchor="middle" '
                f'class="g-deger">{_sayi(deger, 0)}</text>')
        if i % etiket_adimi == 0:
            parcalar.append(
                f'<text x="{x + g / 2:.1f}" y="{taban + 17}" text-anchor="middle" '
                f'class="g-eksen">{_k(etiket)}</text>')
        parcalar.append("</g>")
    return _cerceve("".join(parcalar), genislik, yukseklik)


# --------------------------------------------------------------------------- #
# Yığılmış yatay çubuk (bir bütünün parçaları)
# --------------------------------------------------------------------------- #

#: Yığında parça tonları: aynı mürekkebin koyudan açığa üç basamağı. Parçalar
#: KİMLİK değil sıra taşıdığı için tek renk ailesi (sıralı) — kategorik palet
#: gerekmiyor; efsane yine de şablonda yazılı.
YIGIN_TONLARI = ((PALET["ikincil"], 0.92), (PALET["ikincil"], 0.42), (PALET["cok_soluk"], 0.28))


def yigin_cubuk(
    satirlar: list[tuple[str, list[float], str]],
    *,
    genislik: int = 440,
    etiket_eni: int | None = None,
    toplam_goster: bool = True,
    tarzlar: list[int] | None = None,
    renkler: list[str] | None = None,
) -> Cizim:
    """(etiket, [parça değerleri], ipucu). Parçalar soldan sağa YIGIN_TONLARI."""
    if not satirlar:
        return _cerceve("", genislik, 40)
    sira, ust = 30, 4
    if etiket_eni is None:
        etiket_eni = min(170, max(0, 7 * max(len(a) for a, _, _ in satirlar))) if any(
            a for a, _, _ in satirlar) else 0
    deger_eni = 38 if toplam_goster else 6
    bas = etiket_eni + (12 if etiket_eni else 0)
    eni = genislik - bas - deger_eni
    en_buyuk = max(sum(p) for _, p, _ in satirlar) or 1
    parcalar = []
    for i, (etiket, degerler, ipucu) in enumerate(satirlar):
        y = ust + i * sira
        orta = y + sira / 2
        veri = f' data-tarz="{tarzlar[i]}"' if tarzlar else ""
        parcalar.append(f'<g class="g-satir"{veri}><title>{_k(ipucu)}</title>'
                        f'<rect x="0" y="{y}" width="{genislik}" height="{sira}" fill="transparent"/>')
        if etiket:
            parcalar.append(f'<text x="{etiket_eni}" y="{orta}" text-anchor="end" '
                            f'dominant-baseline="central" class="g-etiket">{_k(etiket)}</text>')
        x = bas
        for j, d in enumerate(degerler):
            w = d / en_buyuk * eni
            if w <= 0:
                continue
            renk, op = YIGIN_TONLARI[min(j, len(YIGIN_TONLARI) - 1)]
            if renkler:
                renk = renkler[i]
            parcalar.append(f'<rect x="{x:.1f}" y="{y + 7}" width="{max(w - 2, 1):.1f}" '
                            f'height="{sira - 14}" rx="3" fill="{renk}" opacity="{op}"/>')
            x += w
        if toplam_goster:
            parcalar.append(f'<text x="{x + 6:.1f}" y="{orta}" dominant-baseline="central" '
                            f'class="g-deger">{_sayi(sum(degerler), 0)}</text>')
        parcalar.append("</g>")
    return _cerceve("".join(parcalar), genislik, ust * 2 + len(satirlar) * sira)


# --------------------------------------------------------------------------- #
# Konum şeridi: iki anlamlı uç arasında nerede?
# --------------------------------------------------------------------------- #

def konum_seridi(
    satirlar: list[tuple[str, float, float, float, str]],
    *,
    sol: str,
    sag: str,
    genislik: int = 440,
    renkler: list[str] | None = None,
) -> Cizim:
    """(etiket, ortanca, alt çeyrek, üst çeyrek, ipucu) — değerler 0..1 yüzdelik.

    Saçılım haritası iki eksenli ve tarzlar üst üste biniyordu; okuyana hiçbir
    şey söylemiyordu (kullanıcı geri bildirimi, 2026-09-28). Burada TEK soru
    var: bu tarz, kütüphanendeki albümler arasında iki ucun hangisine yakın?
    0 = kütüphanenin en «sol» albümü, 1 = en «sağ»ı; orta çizgi ortanca albüm.
    Soluk bant tarzın albümlerinin yarısının durduğu aralık.
    """
    if not satirlar:
        return _cerceve("", genislik, 40)
    sira, ust = 28, 30
    etiket_eni = min(125, max(64, 6.6 * max(len(s[0]) for s in satirlar)))
    x0, x1 = etiket_eni + 14, genislik - 12
    olcek = lambda d: x0 + max(0.0, min(1.0, d)) * (x1 - x0)  # noqa: E731
    alt_y = ust + len(satirlar) * sira
    parcalar = [
        f'<text x="{x0}" y="14" class="g-baslik">← {_k(sol)}</text>',
        f'<text x="{x1}" y="14" text-anchor="end" class="g-baslik">{_k(sag)} →</text>',
        f'<line x1="{olcek(0.5):.1f}" y1="{ust - 6}" x2="{olcek(0.5):.1f}" y2="{alt_y}" '
        f'stroke="{PALET["kenar"]}" stroke-dasharray="3 3"/>',
    ]
    for i, (etiket, orta, q1, q3, ipucu) in enumerate(satirlar):
        y = ust + i * sira + sira / 2
        renk = renkler[i] if renkler else PALET["ikincil"]
        parcalar.append(
            f'<g class="g-satir"><title>{_k(ipucu)}</title>'
            f'<rect x="0" y="{y - sira / 2}" width="{genislik}" height="{sira}" fill="transparent"/>'
            f'<text x="{etiket_eni}" y="{y}" text-anchor="end" dominant-baseline="central" '
            f'class="g-etiket">{_k(_kisalt(etiket, 19))}</text>'
            f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{PALET["izgara"]}" stroke-width="2"/>'
            f'<rect x="{olcek(q1):.1f}" y="{y - 5}" width="{max(olcek(q3) - olcek(q1), 2):.1f}" '
            f'height="10" rx="5" fill="{renk}" opacity="0.3"/>'
            f'<circle cx="{olcek(orta):.1f}" cy="{y}" r="6" fill="{renk}" '
            f'stroke="#fbf9f4" stroke-width="2"/></g>')
    return _cerceve("".join(parcalar), genislik, alt_y + 6)


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
    renk = {g: tarz_rengi(i) for i, g in enumerate(gruplar)}

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
        renk = tarz_rengi(i)
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


# --------------------------------------------------------------------------- #
# Pano: tarz haritası, on yıl × tarz, tarz başına tempo
# --------------------------------------------------------------------------- #
#
# Bu üç grafik ETKİLEŞİMLİ panonun parçası: her işaret `data-tarz` taşır;
# `uygulama.js` bir tarz seçildiğinde öbürlerini soldurur. Seçim DURUMU
# yalnız sayfada (ve `#tarz-N` bağlantısında); sunucu her zaman tam resmi çizer.

def _ayir(noktalar: list[list[float]], yaricap: list[float], genislik: float,
          yukseklik: float, tur: int = 120) -> None:
    """Üst üste binen kabarcıkları it (yerinde). Basit, deterministik gevşetme."""
    for _ in range(tur):
        hareket = False
        for i in range(len(noktalar)):
            for j in range(i + 1, len(noktalar)):
                dx = noktalar[j][0] - noktalar[i][0]
                dy = noktalar[j][1] - noktalar[i][1]
                d = math.hypot(dx, dy) or 0.01
                en_az = yaricap[i] + yaricap[j] + 26          # alttaki etikete yer
                if d < en_az:
                    itme = (en_az - d) / 2
                    ux, uy = (dx / d, dy / d) if d > 0.01 else (1.0, 0.0)
                    noktalar[i][0] -= ux * itme
                    noktalar[i][1] -= uy * itme
                    noktalar[j][0] += ux * itme
                    noktalar[j][1] += uy * itme
                    hareket = True
        for k, (x, y) in enumerate(noktalar):
            r = yaricap[k]
            noktalar[k][0] = min(max(x, r + 8), genislik - r - 8)
            noktalar[k][1] = min(max(y, r + 8), yukseklik - r - 30)
        if not hareket:
            break


def tarz_haritasi(
    tarzlar: list[dict],
    ciftler: list[tuple[int, int, int]],
    adlar: dict[int, str],
    *,
    genislik: int = 620,
    yukseklik: int = 380,
) -> Cizim:
    """Kabarcık = tarz (alan ∝ albüm), çizgi = köprü albüm sayısı.

    Konum `istatistik.tarz_haritasi` (birlikte-üyelikten MDS): yakın duran
    tarzlar albümlerini paylaşıyor. Eksen yok — yalnız yakınlık okunur.
    """
    if not tarzlar:
        return _cerceve("", genislik, 40)
    en_buyuk = max(t["album"] for t in tarzlar) or 1
    k = max(0.62, min(1.0, genislik / 620))
    yaricap = [(14 + 34 * math.sqrt(t["album"] / en_buyuk)) * k for t in tarzlar]
    kenar = 70 * k
    noktalar = [[kenar + t["x"] * (genislik - 2 * kenar),
                 kenar + t["y"] * (yukseklik - 2 * kenar - 20)] for t in tarzlar]
    _ayir(noktalar, yaricap, genislik, yukseklik)
    yer = {t["kume"]: i for i, t in enumerate(tarzlar)}
    en_cok = max((n for _, _, n in ciftler), default=1) or 1

    parcalar = []
    for a, b, n in ciftler:
        if a not in yer or b not in yer:
            continue
        (x1, y1), (x2, y2) = noktalar[yer[a]], noktalar[yer[b]]
        parcalar.append(
            f'<line class="g-kopru" data-tarz="{a} {b}" x1="{x1:.1f}" y1="{y1:.1f}" '
            f'x2="{x2:.1f}" y2="{y2:.1f}" stroke="{PALET["cok_soluk"]}" '
            f'stroke-width="{1.5 + 6 * n / en_cok:.1f}" stroke-linecap="round" opacity="0.35">'
            f"<title>{_k(adlar.get(a, a))} ↔ {_k(adlar.get(b, b))}: {n}</title></line>")
    for i, t in enumerate(tarzlar):
        x, y = noktalar[i]
        r = yaricap[i]
        ad = adlar.get(t["kume"], str(t["kume"]))
        parcalar.append(
            f'<g class="g-tarz" data-tarz="{t["kume"]}" tabindex="0" role="button" '
            f'aria-label="{_k(ad)}">'
            f"<title>{_k(ad)} · {t['album']}</title>"
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{tarz_rengi(t["renk"])}" '
            f'stroke="#fbf9f4" stroke-width="3"/>'
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" class="g-kabarcik-sayi">'
            f'{t["album"]}</text>'
            f'<text x="{x:.1f}" y="{y + r + 16:.1f}" text-anchor="middle" class="g-etiket g-kabarcik-ad">'
            f"{_k(_kisalt(ad, 22))}</text></g>")
    return _cerceve("".join(parcalar), genislik, yukseklik, sinif="tarz-haritasi")


def onyil_tarz(
    onyillar: list[int],
    tarzlar: list[dict],
    adlar: dict[int, str],
    *,
    genislik: int = 620,
    yukseklik: int = 230,
    onyil_adi=lambda o: str(o),
) -> Cizim:
    """Her on yılda albümler, tarza göre yığılı sütun."""
    if not onyillar or not tarzlar:
        return _cerceve("", genislik, 40)
    ust, alt = 12, 26
    alan = yukseklik - ust - alt
    toplamlar = [sum(t["onyil"].get(o, 0) for t in tarzlar) for o in onyillar]
    en_buyuk = max(toplamlar) or 1
    adim = genislik / len(onyillar)
    g = min(adim - 10, 64)
    taban = ust + alan
    parcalar = [f'<line x1="0" y1="{taban}" x2="{genislik}" y2="{taban}" stroke="{PALET["kenar"]}"/>']
    for i, o in enumerate(onyillar):
        x = i * adim + (adim - g) / 2
        y = taban
        for t in tarzlar:
            n = t["onyil"].get(o, 0)
            if not n:
                continue
            h = n / en_buyuk * alan
            parcalar.append(
                f'<rect class="g-parca" data-tarz="{t["kume"]}" x="{x:.1f}" y="{y - h + 1:.1f}" '
                f'width="{g:.1f}" height="{max(h - 2, 1):.1f}" rx="2" fill="{tarz_rengi(t["renk"])}">'
                f"<title>{_k(onyil_adi(o))} · {_k(adlar.get(t['kume'], t['kume']))}: {n}</title></rect>")
            y -= h
        parcalar.append(
            f'<text x="{x + g / 2:.1f}" y="{taban + 17}" text-anchor="middle" class="g-eksen">'
            f"{o}</text>"
            f'<text x="{x + g / 2:.1f}" y="{y - 5:.1f}" text-anchor="middle" class="g-deger">'
            f"{toplamlar[i]}</text>")
    return _cerceve("".join(parcalar), genislik, yukseklik)


def tempo_seridi(
    tarzlar: list[dict],
    adlar: dict[int, str],
    alan: tuple[float, float],
    *,
    genislik: int = 620,
    birim: str = "bpm",
) -> Cizim:
    """Tarz başına tempo: bant = albümlerin ortadaki yarısı, nokta = ortanca."""
    satirlar = [t for t in tarzlar if t.get("tempo")]
    if not satirlar:
        return _cerceve("", genislik, 40)
    sira, ust = 26, 6
    etiket_eni = min(150, max(70, 6.8 * max(len(adlar.get(t["kume"], "")) for t in satirlar)))
    x0, x1 = etiket_eni + 14, genislik - 14
    lo, hi = alan
    lo, hi = math.floor(lo / 20) * 20, math.ceil(hi / 20) * 20
    olcek = lambda v: x0 + (v - lo) / max(hi - lo, 1) * (x1 - x0)  # noqa: E731
    alt_y = ust + len(satirlar) * sira
    parcalar = []
    for v in range(int(lo), int(hi) + 1, 20):
        parcalar.append(
            f'<line x1="{olcek(v):.1f}" y1="{ust}" x2="{olcek(v):.1f}" y2="{alt_y}" '
            f'stroke="{PALET["izgara"]}"/>'
            f'<text x="{olcek(v):.1f}" y="{alt_y + 16}" text-anchor="middle" class="g-eksen">{v}</text>')
    for i, t in enumerate(satirlar):
        y = ust + i * sira + sira / 2
        orta, q1, q3 = t["tempo"]
        renk = tarz_rengi(t["renk"])
        ad = adlar.get(t["kume"], str(t["kume"]))
        parcalar.append(
            f'<g class="g-satir" data-tarz="{t["kume"]}"><title>{_k(ad)}: {round(orta)} {birim} '
            f'({round(q1)}–{round(q3)})</title>'
            f'<rect x="0" y="{y - sira / 2}" width="{genislik}" height="{sira}" fill="transparent"/>'
            f'<text x="{etiket_eni}" y="{y}" text-anchor="end" dominant-baseline="central" '
            f'class="g-etiket">{_k(_kisalt(ad, 20))}</text>'
            f'<rect x="{olcek(q1):.1f}" y="{y - 6}" width="{max(olcek(q3) - olcek(q1), 3):.1f}" '
            f'height="12" rx="6" fill="{renk}" opacity="0.3"/>'
            f'<circle cx="{olcek(orta):.1f}" cy="{y}" r="6" fill="{renk}" stroke="#fbf9f4" '
            f'stroke-width="2"/></g>')
    return _cerceve("".join(parcalar), genislik, alt_y + 24)
