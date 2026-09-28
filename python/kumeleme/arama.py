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

## Üç yöntem (2026-09-28, yöntem notundaki sorulardan)

- **pca** — ağırlıklı matris → PCA → FCM (üretimdeki hat).
- **spektral** — PCA yerine kosinüs kNN benzerlik grafının spektral gömmesi
  (`boyut_indirgeme.spektral_gomme`). %1,4 dolu, çoğu ikili bir matriste
  «hangi albümler birbirine benziyor» sorusuna doğrudan bakar.
- **konsensus** — aynı c için bütün pca koşularının (bileşen × m) keskin
  atamalarından ortak-atama matrisi C_ij = «i ile j'nin aynı tarza düştüğü
  koşuların payı»; C'nin spektral gömmesinde FCM. Tek bir ayarın tesadüfüne
  değil, ayarlar arasında TEKRAR EDEN yapıya dayanır. Sağlamlığı iyimserdir:
  gömme tüm veriden kuruluyor, bootstrap yalnız son FCM adımını sınıyor.

Üçü de AYNI ölçütlerle (ortak referans uzayında siluet, bootstrap, asgari
boyut, kalabalık uyumu) ve aynı seçim kuralıyla yarışır.

## Seçim kuralı

Geçerli adaylar (1 ve 2) arasında en iyi siluetin %5'i içinde (göreli; `SILUET_TOLERANSI`)
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
from python.kumeleme.boyut_indirgeme import bloklari_agirlikla, pca, spektral_gomme
from python.kumeleme.fcm import c_tara, fcm, xie_beni
from python.kumeleme.stabilite import bootstrap_jaccard

BILESENLER = (5, 6, 8, 10, 12)
M_DEGERLERI = (1.3, 1.4, 1.5, 1.6)        # K3: 1,3–1,6
#: «Pratikte eşit iyi» payı — GÖRELİ. Mutlak 0,02 ilk sürümdeydi ve yapay
#: seyrek veride (%2 dolu, 6 gizli grup) yanlış c seçti: siluetler ~0,07
#: olduğu için 0,02 aslında %30'luk bir paydı ve c=9 «eşit iyi» sayıldı.
SILUET_TOLERANSI = 0.05
ASGARI_BOYUT_SABIT = 5
ASGARI_BOYUT_PAY = 0.02
TARAMA_TEKRARI = 10                        # tarama bootstrap'ı (seçilen tam sayıyla yeniden)
TARAMA_BASLANGICI = 5
ALFA = 1.0
YONTEMLER = ("pca", "spektral", "konsensus")
KOMSU = 10                                 # spektral: kNN grafında komşu sayısı


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
    yontem: str = "pca"

    @property
    def uzay(self) -> tuple[str, int]:
        """Bu adayın FCM uzayının anahtarı (bkz. `ara` → uzaylar)."""
        return (self.yontem, self.c if self.yontem == "konsensus" else self.bilesen)


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


def ortak_atama(atamalar: list[np.ndarray]) -> np.ndarray:
    """C_ij = i ile j'nin aynı kümeye düştüğü koşuların payı."""
    n = len(atamalar[0])
    C = np.zeros((n, n))
    for a in atamalar:
        C += a[:, None] == a[None, :]
    return C / len(atamalar)


def ara(
    matris: pd.DataFrame,
    ayar: Ayar = VARSAYILAN,
    *,
    bilesenler: tuple[int, ...] = BILESENLER,
    m_degerleri: tuple[float, ...] = M_DEGERLERI,
    yontemler: tuple[str, ...] = YONTEMLER,
    album_sanatci: list[str] | None = None,
    ciftler: set[tuple[str, str]] | None = None,
    yaz=print,
    uzaylar: dict | None = None,
) -> tuple[list[Aday], Aday | None]:
    """Izgarayı tara, adayları ve seçileni döndür. Veritabanına dokunmaz.

    `uzaylar` sözlük verilirse her adayın FCM uzayı (X) oraya yazılır;
    `--yaz` seçileni yeniden hesaplamadan aynı uzayda kümeler.
    """
    agirlikli = bloklari_agirlikla(matris, ayar.blok_agirliklari).to_numpy(dtype=float)
    D = kosinus_mesafe(agirlikli)
    n = agirlikli.shape[0]
    esik_boyut = asgari_boyut(n)
    uzaylar = {} if uzaylar is None else uzaylar
    adaylar: list[Aday] = []
    atamalar: dict[int, list[np.ndarray]] = defaultdict(list)

    def degerlendir(X, yontem, k, m, c, sonuc):
        atama = sonuc.uyelik.argmax(axis=1)
        boyutlar = np.bincount(atama, minlength=c)
        st = bootstrap_jaccard(X, atama, c, m, tekrar=TARAMA_TEKRARI,
                               esik=ayar.stabilite_esigi, tohum=ayar.tohum)
        aday = Aday(bilesen=k, m=m, c=c, siluet=bulanik_siluet(D, sonuc.uyelik),
                    xie_beni=xie_beni(X, sonuc, m), stabil_oran=float(st.stabil_mi.mean()),
                    jaccard_min=float(st.jaccard.min()), en_kucuk=int(boyutlar.min()),
                    yontem=yontem)
        aday.gecerli = aday.stabil_oran >= 1.0 and aday.en_kucuk >= esik_boyut
        if aday.gecerli and album_sanatci is not None and ciftler:
            aday.kalabalik = kalabalik_uyumu(atama, album_sanatci, ciftler)
        adaylar.append(aday)
        return atama

    benzerlik = np.clip(1.0 - D, 0.0, 1.0) if "spektral" in yontemler else None
    for k in bilesenler:
        if k >= min(agirlikli.shape):
            continue
        uzay_listesi = []
        if "pca" in yontemler or "konsensus" in yontemler:
            uzay_listesi.append(("pca", pca(agirlikli, aciklanan_varyans=1.0, azami_bilesen=k,
                                            asgari_bilesen=min(k, ayar.asgari_bilesen)).X))
        if "spektral" in yontemler:
            uzay_listesi.append(("spektral", spektral_gomme(benzerlik, k, komsu=KOMSU)))
        for yontem, X in uzay_listesi:
            uzaylar[(yontem, k)] = X
            for m in m_degerleri:
                for t in c_tara(X, ayar.c_araligi, m, baslangic=TARAMA_BASLANGICI,
                                yineleme=ayar.yineleme, tolerans=ayar.tolerans, tohum=ayar.tohum):
                    if yontem == "pca" and "pca" not in yontemler:
                        atamalar[t.c].append(t.sonuc.keskin_atama())   # yalnız konsensüse girdi
                        continue
                    a = degerlendir(X, yontem, k, m, t.c, t.sonuc)
                    if yontem == "pca":
                        atamalar[t.c].append(a)
        yaz(f"  {k:>2} bileşen tarandı · geçerli aday: {sum(a.gecerli for a in adaylar)}")

    if "konsensus" in yontemler:
        for c, liste in sorted(atamalar.items()):
            if len(liste) < 3:
                continue
            X = spektral_gomme(ortak_atama(liste), c)
            uzaylar[("konsensus", c)] = X
            for m in m_degerleri:
                try:
                    sonuc = fcm(X, c, m, baslangic=TARAMA_BASLANGICI, yineleme=ayar.yineleme,
                                tolerans=ayar.tolerans, tohum=ayar.tohum)
                except ValueError:
                    continue
                degerlendir(X, "konsensus", c, m, c, sonuc)
        yaz(f"  konsensüs tarandı · geçerli aday: {sum(a.gecerli for a in adaylar)}")

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
    havuz = [a for a in gecerli if a.siluet >= en_iyi - SILUET_TOLERANSI * abs(en_iyi)]
    if all(a.kalabalik is not None for a in havuz):
        return max(havuz, key=lambda a: (a.kalabalik, a.c, a.siluet))
    return max(havuz, key=lambda a: (a.c, a.siluet))


YONTEM_ADI = {"pca": "PCA", "spektral": "spektral", "konsensus": "konsensüs"}


def _ayar_metni(a: Aday) -> str:
    if a.yontem == "konsensus":
        return f"konsensüs, m {a.m:g}, c {a.c}"
    return f"{YONTEM_ADI.get(a.yontem, a.yontem)} {a.bilesen} boyut, m {a.m:g}, c {a.c}"


def rapor(adaylar: list[Aday], secilen: Aday | None, n: int, *, simdiki: Aday | None = None) -> str:
    """Markdown rapor: yöntem başına en iyiler, ilk 15 aday, seçim gerekçesi."""
    satirlar = [
        f"# Kümeleme araması — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"{n} albüm · {len(adaylar)} aday · geçerli {sum(a.gecerli for a in adaylar)} "
        f"(her tarz bootstrap'ta sağlam VE en küçük tarz ≥ {asgari_boyut(n)} albüm)",
        "",
        "## Yöntem başına en iyi geçerli aday",
        "",
        "| yöntem | ayar | bulanık siluet | kalabalık uyumu | geçerli aday |",
        "|---|---|---:|---:|---:|",
    ]
    for y in YONTEMLER:
        grup = [a for a in adaylar if a.yontem == y]
        if not grup:
            continue
        gecerli = [a for a in grup if a.gecerli]
        if gecerli:
            en = max(gecerli, key=lambda a: a.siluet)
            kal = f"{en.kalabalik:.2f}" if en.kalabalik is not None else "—"
            satirlar.append(f"| {YONTEM_ADI[y]} | {_ayar_metni(en)} | {en.siluet:.3f} | {kal} | "
                            f"{len(gecerli)}/{len(grup)} |")
        else:
            satirlar.append(f"| {YONTEM_ADI[y]} | — | — | — | 0/{len(grup)} |")
    satirlar += [
        "",
        "## İlk 15 aday",
        "",
        "| yöntem | boyut | m | c | bulanık siluet | kalabalık uyumu | XB | en küçük | en zayıf Jaccard | |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    sirali = sorted(adaylar, key=lambda a: (not a.gecerli, -a.siluet))[:15]
    for a in sirali:
        isaret = "**seçildi**" if a.secildi else ("geçerli" if a.gecerli else "")
        kal = f"{a.kalabalik:.2f}" if a.kalabalik is not None else "—"
        boyut = "—" if a.yontem == "konsensus" else a.bilesen
        satirlar.append(f"| {YONTEM_ADI.get(a.yontem, a.yontem)} | {boyut} | {a.m:g} | {a.c} | "
                        f"{a.siluet:.3f} | {kal} | {a.xie_beni:.3f} | {a.en_kucuk} | "
                        f"{a.jaccard_min:.2f} | {isaret} |")
    satirlar += ["", "XB yalnız aynı uzaydaki adaylar arasında kıyaslanabilir; yöntemler "
                 "arası kıyas siluet ve kalabalık uyumuyla yapılır. Konsensüsün sağlamlığı "
                 "iyimserdir (gömme tüm veriden kuruluyor)."]
    if simdiki:
        kal = f"{simdiki.kalabalik:.2f}" if simdiki.kalabalik is not None else "—"
        satirlar += ["", f"Şimdiki ayar ({_ayar_metni(simdiki)}): siluet "
                     f"{simdiki.siluet:.3f}, kalabalık {kal}, "
                     f"{'geçerli' if simdiki.gecerli else 'GEÇERSİZ'}."]
    if secilen:
        satirlar += ["", f"Seçilen: {_ayar_metni(secilen)}.",
                     "Sonraki adım: `python -m python.degerlendirme` ile eski ve yeni "
                     "çalışmayı öneri isabetinde kıyasla (K19)."]
    return "\n".join(satirlar) + "\n"


def secileni_yaz(db: Path, matris: pd.DataFrame, secilen: Aday, X: np.ndarray,
                 ayar: Ayar = VARSAYILAN) -> str:
    """Seçilen adayı kendi uzayında tam ayarla kümele ve yaz. calisma_id döner.

    `calistir` yalnız PCA/UMAP biliyor; spektral ve konsensüs uzayları burada
    kurulmuş olduğu için yazma da burada — üretimin yazma işlevleriyle
    (K19: kopyalamaz, çağırır).
    """
    from python.db import baglan
    from python.kumeleme.calistir import sonuclari_yaz, temsilcileri_yaz

    sonuc = fcm(X, secilen.c, secilen.m, baslangic=ayar.baslangic, yineleme=ayar.yineleme,
                tolerans=ayar.tolerans, tohum=ayar.tohum)
    st = bootstrap_jaccard(X, sonuc.keskin_atama(), secilen.c, secilen.m, tekrar=ayar.bootstrap,
                           esik=ayar.stabilite_esigi, tohum=ayar.tohum)
    boyut = "" if secilen.yontem == "konsensus" else str(secilen.bilesen)
    calisma_id = (f"{datetime.now():%Y%m%dT%H%M%S}-c{secilen.c}-m{secilen.m:g}-"
                  f"{secilen.yontem}{boyut}")
    conn = baglan(db)
    try:
        sonuclari_yaz(conn, calisma_id, matris.index, sonuc.uyelik, st.jaccard, ayar.stabilite_esigi)
        sanatcilar = (pd.read_sql_query("SELECT album_id, artist FROM albums", conn)
                      .set_index("album_id").reindex(matris.index)["artist"].fillna("").to_numpy())
        temsilcileri_yaz(conn, calisma_id, matris.index, sonuc.uyelik, X, sanatcilar, ayar)
    finally:
        conn.close()
    print(st.ozet())
    return calisma_id


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
    from python.kumeleme.calistir import matrisi_oku
    from python.kumeleme.tasi import tasi

    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--matris", type=Path, default=VARSAYILAN.matris)
    a.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    a.add_argument("--rapor", type=Path, default=Path("data/raporlar"))
    a.add_argument("--yaz", action="store_true",
                   help="seçileni veritabanına yaz ve adları/kararları taşı")
    a.add_argument("--yontemler", default=",".join(YONTEMLER),
                   help="virgülle: pca,spektral,konsensus (varsayılan hepsi)")
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

    yontemler = tuple(y.strip() for y in args.yontemler.split(",") if y.strip() in YONTEMLER)
    uzaylar: dict = {}
    adaylar, secilen = ara(matris, yontemler=yontemler, album_sanatci=sanatci, ciftler=ciftler,
                           uzaylar=uzaylar)
    simdiki = next((x for x in adaylar if x.yontem == "pca" and x.bilesen == VARSAYILAN.bilesen
                    and x.m == VARSAYILAN.m and onceki and f"-c{x.c}-" in onceki[0]), None)
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

    yeni = secileni_yaz(args.db, matris, secilen, uzaylar[secilen.uzay])
    if onceki:
        conn = baglan(args.db)
        try:
            r = tasi(conn, onceki[0], yeni)
        finally:
            conn.close()
        print(f"Taşındı: {len(r['tasinan_ad'])} ad, {len(r['karar'])} karar "
              f"(taşınamayan ad: {len(r['tasinmayan_ad'])})")
    print(f"Yeni çalışma: {yeni}")
    print("Eskiye dönmek istersen: arayüzde ?calisma=" + (onceki[0] if onceki else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
