"""Güçlü kümeleme: ayar ARAMASI, tek ayar değil (kullanıcı isteği, 2026-09-28).

«Bazı önerilerinden hâlâ emin değilim.» Kümeleme şimdiye dek SABİT bir
ayarla koşuyordu (8 PCA bileşeni, m = 1,4) ve yalnız c taranıyordu. Oysa
bileşen sayısı ile bulanıklık da sonucu değiştiriyor; hangisinin doğru
olduğu ölçülmemişti. Burada üçü birlikte taranır ve seçim ÖLÇÜYLE yapılır.

## Ölçütler

1. **Bootstrap sağlamlığı (K3).** Her tarz, yeniden örneklemede aynı
   albümleri toplamalı (Jaccard ≥ eşik). Tek bir oynak tarz bile adayı eler.
2. **Asgari boyut.** Keskin atamada hiçbir tarz `asgari_boyut`tan küçük
   olamaz; beş albümlük bir «tarz» temsilci seçimine (K4) bile yetmez.
3. **Bulanık siluet** (Campello & Hruschka, 2006). Klasik siluet, her
   albümün iki en yüksek üyeliği farkıyla ağırlıklanır:
       FS = Σ_j (u_pj − u_qj)^α · s_j  /  Σ_j (u_pj − u_qj)^α
   Sınırdaki albümler (iki tarz arasında) yargıya az katılır; net olanlar çok.
   XB'nin tersine c büyüdükçe kendiliğinden iyileşmez.
   **Ortak referans uzayında** hesaplanır: ağırlıklı ama İNDİRGENMEMİŞ matris,
   kosinüs mesafesi. Her aday kendi PCA uzayında ölçülseydi 5 bileşenli uzayla
   12 bileşenli uzayın silueti kıyaslanamazdı.
4. **Kalabalık uyumu** (dış geçerlilik, varsa). Çalma listelerinde birlikte
   geçen (PMI > 0) kütüphane sanatçısı çiftlerinin ne kadarı AYNI tarzda?
   Rastgele bir bölmenin aynı boyutlarla vereceği orana (Σ p_k²) bölünür:
   1'den büyük = tarzlar insanların birlikte dinlediğiyle örtüşüyor. Bu,
   kümelemeye hiç girmeyen bir veri — iç ölçütlerin göremediğini görür.

## Seçim kuralı

Geçerli adaylar (1 ve 2) arasında en iyi siluetin `SILUET_TOLERANSI` içinde
kalanlar havuzdur («bir standart hata» kuralının akrabası: pratikte eşit iyi
olanlar). Havuzda kalabalık uyumu en yüksek olan seçilir; kalabalık verisi
yoksa en ince bölme (en büyük c) — kullanıcı ince taneli ayrım istiyor
(CLAUDE.md, kullanıcı bağlamı).

Değerlendirmenin (K19, leave-one-artist-out) yerine GEÇMEZ: o, öneri
isabetini ölçer ve dakikalar sürer. Arama seçtikten sonra
`python -m python.degerlendirme` eski ve yeni çalışmayı kıyaslamalıdır.

Kullanım (Mac'te, gerçek veriyle):
    python -m python.kumeleme.arama                 # yalnız rapor
    python -m python.kumeleme.arama --yaz           # seç, yaz, adları taşı
"""

from __future__ import annotations

import argparse
import math
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from python.kumeleme.ayar import VARSAYILAN, Ayar
from python.kumeleme.boyut_indirgeme import bloklari_agirlikla, pca
from python.kumeleme.fcm import c_tara, xie_beni
from python.kumeleme.stabilite import bootstrap_jaccard

BILESENLER = (5, 6, 8, 10, 12)
M_DEGERLERI = (1.3, 1.4, 1.5, 1.6)        # K3: 1,3–1,6
SILUET_TOLERANSI = 0.02
ASGARI_BOYUT_SABIT = 5
ASGARI_BOYUT_PAY = 0.02
TARAMA_TEKRARI = 10                        # tarama bootstrap'ı (seçilen tam sayıyla yeniden)
TARAMA_BASLANGICI = 5
ALFA = 1.0


@dataclass
class Aday:
    bilesen: int
    m: float
    c: int
    siluet: float
    xie_beni: float
    stabil_oran: float
    jaccard_min: float
    en_kucuk: int
    kalabalik: float | None = None
    gecerli: bool = False
    secildi: bool = False


# --------------------------------------------------------------------------- #
# Ölçütler
# --------------------------------------------------------------------------- #

def kosinus_mesafe(X: np.ndarray) -> np.ndarray:
    """Satırları L2'ye göre ölçekle, 1 − kosinüs benzerliği."""
    norm = np.linalg.norm(X, axis=1, keepdims=True)
    Y = X / np.maximum(norm, 1e-12)
    return np.clip(1.0 - Y @ Y.T, 0.0, 2.0)


def bulanik_siluet(D: np.ndarray, U: np.ndarray, alfa: float = ALFA) -> float:
    """Campello & Hruschka (2006) bulanık siluet. D: (n, n) mesafe, U: (n, c)."""
    n, c = U.shape
    atama = U.argmax(axis=1)
    siralı = np.sort(U, axis=1)
    agirlik = (siralı[:, -1] - siralı[:, -2]) ** alfa if c > 1 else np.ones(n)
    tek = np.eye(c)[atama]                          # (n, c) keskin atama
    sayi = tek.sum(axis=0)                          # küme boyutları
    toplamlar = D @ tek                             # her albümün her kümeye mesafe toplamı
    kendi_say = sayi[atama]
    a = toplamlar[np.arange(n), atama] / np.maximum(kendi_say - 1, 1)
    ort = toplamlar / np.maximum(sayi, 1)
    ort[np.arange(n), atama] = np.inf
    ort[:, sayi == 0] = np.inf
    b = ort.min(axis=1)
    b = np.where(np.isfinite(b), b, 0.0)
    payda = np.maximum(a, b)
    s = np.where(payda > 0, (b - a) / np.where(payda > 0, payda, 1), 0.0)
    s = np.where(kendi_say <= 1, 0.0, s)            # tek üyeli küme: s = 0 (Rousseeuw)
    toplam = agirlik.sum()
    return float((agirlik * s).sum() / toplam) if toplam > 0 else float(s.mean())


def kalabalik_ciftleri(conn: sqlite3.Connection, sanatcilar: set[str]) -> set[tuple[str, str]]:
    """Çalma listelerinde PMI > 0 olan kütüphane sanatçısı çiftleri (anahtarlar)."""
    try:
        from python.degerlendirme import pmi_tablosu
        tablo = pmi_tablosu(conn, sanatcilar)
    except sqlite3.Error:
        return set()
    ciftler = set()
    for a, komsular in tablo.items():
        for b, deger in komsular.items():
            if deger > 0 and b in sanatcilar and a != b:
                ciftler.add(tuple(sorted((a, b))))
    return ciftler


def kalabalik_uyumu(atama: np.ndarray, album_sanatci: list[str],
                    ciftler: set[tuple[str, str]], asgari_cift: int = 10) -> float | None:
    """Birlikte dinlenen sanatçı çiftlerinin aynı tarzda olma oranı / rastgele beklenti."""
    if len(ciftler) < asgari_cift:
        return None
    # Sanatçının tarzı: albümlerinin çoğunluğunun tarzı.
    sayac: dict[str, Counter] = defaultdict(Counter)
    for s, k in zip(album_sanatci, atama):
        if s:
            sayac[s][int(k)] += 1
    tarz = {s: c.most_common(1)[0][0] for s, c in sayac.items()}
    gecerli = [(a, b) for a, b in ciftler if a in tarz and b in tarz]
    if len(gecerli) < asgari_cift:
        return None
    ayni = sum(tarz[a] == tarz[b] for a, b in gecerli) / len(gecerli)
    paylar = np.bincount(list(tarz.values())) / len(tarz)
    beklenen = float((paylar ** 2).sum())
    return float(ayni / beklenen) if beklenen > 0 else None


# --------------------------------------------------------------------------- #
# Arama
# --------------------------------------------------------------------------- #

def asgari_boyut(n: int) -> int:
    return max(ASGARI_BOYUT_SABIT, math.ceil(ASGARI_BOYUT_PAY * n))


def ara(
    matris: pd.DataFrame,
    ayar: Ayar = VARSAYILAN,
    *,
    bilesenler: tuple[int, ...] = BILESENLER,
    m_degerleri: tuple[float, ...] = M_DEGERLERI,
    album_sanatci: list[str] | None = None,
    ciftler: set[tuple[str, str]] | None = None,
    yaz=print,
) -> tuple[list[Aday], Aday | None]:
    """Izgarayı tara, adayları ve seçileni döndür. Veritabanına dokunmaz."""
    agirlikli = bloklari_agirlikla(matris, ayar.blok_agirliklari).to_numpy(dtype=float)
    D = kosinus_mesafe(agirlikli)
    n = agirlikli.shape[0]
    esik_boyut = asgari_boyut(n)
    adaylar: list[Aday] = []
    for k in bilesenler:
        if k >= min(agirlikli.shape):
            continue
        X = pca(agirlikli, aciklanan_varyans=1.0, azami_bilesen=k,
                asgari_bilesen=min(k, ayar.asgari_bilesen)).X
        for m in m_degerleri:
            for t in c_tara(X, ayar.c_araligi, m, baslangic=TARAMA_BASLANGICI,
                            yineleme=ayar.yineleme, tolerans=ayar.tolerans, tohum=ayar.tohum):
                atama = t.sonuc.keskin_atama()
                boyutlar = np.bincount(atama, minlength=t.c)
                st = bootstrap_jaccard(X, atama, t.c, m, tekrar=TARAMA_TEKRARI,
                                       esik=ayar.stabilite_esigi, tohum=ayar.tohum)
                aday = Aday(
                    bilesen=k, m=m, c=t.c,
                    siluet=bulanik_siluet(D, t.sonuc.uyelik),
                    xie_beni=xie_beni(X, t.sonuc, m),
                    stabil_oran=float(st.stabil_mi.mean()),
                    jaccard_min=float(st.jaccard.min()),
                    en_kucuk=int(boyutlar.min()),
                )
                aday.gecerli = aday.stabil_oran >= 1.0 and aday.en_kucuk >= esik_boyut
                if aday.gecerli and album_sanatci is not None and ciftler:
                    aday.kalabalik = kalabalik_uyumu(atama, album_sanatci, ciftler)
                adaylar.append(aday)
        yaz(f"  {k:>2} bileşen tarandı · geçerli aday: {sum(a.gecerli for a in adaylar)}")
    secilen = sec(adaylar)
    if secilen:
        secilen.secildi = True
    return adaylar, secilen


def sec(adaylar: list[Aday]) -> Aday | None:
    """Seçim kuralı — modül belgesinde."""
    gecerli = [a for a in adaylar if a.gecerli]
    if not gecerli:
        # Hiçbiri tam sağlam değilse: en sağlam olanlar arasında en iyi siluet.
        if not adaylar:
            return None
        en = max(a.stabil_oran for a in adaylar)
        return max((a for a in adaylar if a.stabil_oran >= en - 1e-9), key=lambda a: a.siluet)
    en_iyi = max(a.siluet for a in gecerli)
    havuz = [a for a in gecerli if a.siluet >= en_iyi - SILUET_TOLERANSI]
    if all(a.kalabalik is not None for a in havuz):
        return max(havuz, key=lambda a: (a.kalabalik, a.c, a.siluet))
    return max(havuz, key=lambda a: (a.c, a.siluet))


def rapor(adaylar: list[Aday], secilen: Aday | None, n: int, *, simdiki: Aday | None = None) -> str:
    """Markdown rapor: en iyi 15 aday + seçim gerekçesi."""
    satirlar = [
        f"# Kümeleme araması — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"{n} albüm · {len(adaylar)} aday · geçerli {sum(a.gecerli for a in adaylar)} "
        f"(her tarz bootstrap'ta sağlam VE en küçük tarz ≥ {asgari_boyut(n)} albüm)",
        "",
        "| bileşen | m | c | bulanık siluet | kalabalık uyumu | XB | en küçük | en zayıf Jaccard | |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    sirali = sorted(adaylar, key=lambda a: (not a.gecerli, -a.siluet))[:15]
    for a in sirali:
        isaret = "**seçildi**" if a.secildi else ("geçerli" if a.gecerli else "")
        kal = f"{a.kalabalik:.2f}" if a.kalabalik is not None else "—"
        satirlar.append(f"| {a.bilesen} | {a.m:g} | {a.c} | {a.siluet:.3f} | {kal} | "
                        f"{a.xie_beni:.3f} | {a.en_kucuk} | {a.jaccard_min:.2f} | {isaret} |")
    if simdiki:
        kal = f"{simdiki.kalabalik:.2f}" if simdiki.kalabalik is not None else "—"
        satirlar += ["", f"Şimdiki ayar (8 bileşen, m 1,4, c {simdiki.c}): siluet "
                     f"{simdiki.siluet:.3f}, kalabalık {kal}, "
                     f"{'geçerli' if simdiki.gecerli else 'GEÇERSİZ'}."]
    if secilen:
        satirlar += ["", f"Seçilen: {secilen.bilesen} bileşen, m {secilen.m:g}, c {secilen.c}.",
                     "Sonraki adım: `python -m python.degerlendirme` ile eski ve yeni "
                     "çalışmayı öneri isabetinde kıyasla (K19)."]
    return "\n".join(satirlar) + "\n"


# --------------------------------------------------------------------------- #
# Komut satırı
# --------------------------------------------------------------------------- #

def _sanatcilar(conn: sqlite3.Connection, album_ids: pd.Index) -> list[str]:
    from python.metin import normalize_esleme
    harita = {r[0]: normalize_esleme(r[1] or "") for r in conn.execute(
        "SELECT album_id, artist FROM albums")}
    return [harita.get(a, "") for a in album_ids]


def main(argv: list[str] | None = None) -> int:
    from python.db import VARSAYILAN_DB, baglan
    from python.kumeleme.calistir import calistir, matrisi_oku
    from python.kumeleme.tasi import tasi

    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--matris", type=Path, default=VARSAYILAN.matris)
    a.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    a.add_argument("--rapor", type=Path, default=Path("data/raporlar"))
    a.add_argument("--yaz", action="store_true",
                   help="seçileni veritabanına yaz ve adları/kararları taşı")
    args = a.parse_args(argv)

    matris = matrisi_oku(args.matris)
    conn = baglan(args.db)
    try:
        sanatci = _sanatcilar(conn, matris.index)
        ciftler = kalabalik_ciftleri(conn, {s for s in sanatci if s})
        onceki = conn.execute(
            "SELECT calisma_id FROM clusters ORDER BY calisma_id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    print(f"Matris {matris.shape[0]} × {matris.shape[1]} · kalabalık çifti: {len(ciftler)}")

    adaylar, secilen = ara(matris, album_sanatci=sanatci, ciftler=ciftler)
    simdiki = next((x for x in adaylar if x.bilesen == VARSAYILAN.bilesen and x.m == VARSAYILAN.m
                    and onceki and f"-c{x.c}-" in onceki[0]), None)
    metin = rapor(adaylar, secilen, matris.shape[0], simdiki=simdiki)
    args.rapor.mkdir(parents=True, exist_ok=True)
    yol = args.rapor / f"kumeleme-arama-{datetime.now():%Y%m%dT%H%M}.md"
    yol.write_text(metin, encoding="utf-8")
    print(metin)
    print(f"Rapor: {yol}")

    if not args.yaz or secilen is None:
        if secilen is not None:
            print("Yazmak için: --yaz")
        return 0

    ayar = VARSAYILAN.ile(matris=args.matris, db=args.db, bilesen=secilen.bilesen,
                          m=secilen.m, c_araligi=(secilen.c, secilen.c))
    sonuc = calistir(ayar)
    if onceki:
        conn = baglan(args.db)
        try:
            r = tasi(conn, onceki[0], sonuc["calisma_id"])
        finally:
            conn.close()
        print(f"Taşındı: {len(r['tasinan_ad'])} ad, {len(r['karar'])} karar "
              f"(taşınamayan ad: {len(r['tasinmayan_ad'])})")
    print(f"Yeni çalışma: {sonuc['calisma_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
