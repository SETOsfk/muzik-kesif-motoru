"""Motor — liste grafiğinde yürüyüş + kapalı formlu otokodlayıcı + öğrenilmiş füzyon.

2026-10-20. Kaynak: altı ajanlı literatür taraması (`docs/arastirma/README.md`).
Üç bulgu bu modülü doğurdu:

1. **Basit doğrusal yöntemler kazanıyor.** Ferrari Dacrema ve ark. (2019)
   «Are we really making much progress?»: incelenen sinir ağı önericilerinin
   neredeyse hepsini iyi ayarlanmış ItemKNN / P3α / RP3β / EASE geçti. Bizim
   verimiz (482 liste × ~10 bin sanatçı) tam bu yöntemlerin bölgesi.
2. **Elle ölçtüğümüz düğmeler tek bir ailenin noktaları.** Liste boyutu
   ağırlığı (eşit/log/ters) RP3β'nın α'sı, PMI'nın örtük popülerlik cezası
   β'sı, `MAX(pmi)` birleştirmesi Aiolli (2013) yerellik üssünün γ→∞ ucu.
   Ayrı ayrı süpürmek yerine aile bir kez ayarlanıyor.
3. **Füzyon ağırlığı (1:2) aynı 147 sorguda seçilmişti.** Burada öğrenilen
   bir sıralayıcı var — gizleme sınamasının sözde etiketleriyle eğitilen
   koşullu logit (McFadden; ListNet top-one ile aynı kayıp) — ve İÇ İÇE
   çapraz doğrulamayla ölçülüyor. Öncül, şimdiki üretim füzyonuna merkezli:
   düzenlileştirme sonsuza giderse motor bugünkü motordur, daha kötüsü
   olamaz, ancak veri gösterirse ondan ayrılır.

Popülerlik öznitelik DEĞİL. PDA (Zhang ve ark. 2021: eğitimde kullan,
puanlamada kapat) denendi ve yapılı yapay veride motoru çökertti (MRR 0,031 →
0,003): ortak liste sayısı popülerlikle ilişkili, model ikisini birbirine karşı
dengeliyordu; biri kapatılınca öteki popüler sanatçıyı öne itti. Popülerlik
cezası RP3β'nın β'sında ve raporun «görünür» sütununda.

Bağlam listeleri (dil, ruh hâli, spor) ağırlık `BAGLAM_AGIRLIGI` ile kısılır:
Sezen Aksu vakası (karar günlüğü 2026-09-23) bir «türkçe» listesi üzerinden
geldi. Başlığında TARZ sözcüğü olan liste («türk rock») bağlam sayılmaz.

Hiçbir yol LLM ya da yeni bağımlılık istemez (K2): yalnız numpy.

Kullanım:
    python -m python.motor --egit            # ayarla + öğren + data/cache/motor.json
    python -m python.motor --egit --limit 30 # deneme
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np

from python.metin import normalize_esleme

#: Öğrenilmiş ayarların yeri. `data/` git'e girmez; ayar makineye ve
#: kütüphaneye aittir. Dosya yoksa literatür varsayılanları kullanılır.
AYAR_DOSYASI = Path("data/cache/motor.json")

#: RP3β varsayılanları — Dacrema ve ark. 2019'un resmî kodu (α=1, β=0,6).
#: α liste boyutu cezası (0 = eşit liste, 1 = 1/n), β aday popülerlik cezası.
#: Formül o kodla aynı: S_i· = d_i^−α · (x_iᵀ diag(n^−α) X) ⊙ d^−β.
ALFA, BETA = 1.0, 0.6
#: EASE düzenlileştirmesi. Büyük veride yüzler; 482 satırda Woodbury formu
#: çalışıyor ve λ küçük aralıkta süpürülür.
LAMBDA = 10.0
#: Dil/ruh hâli başlıklı listenin ağırlığı (1 = kapalı).
BAGLAM_AGIRLIGI = 0.5
#: Sıra özniteliği K/(K+sıra) — RRF'nin K'sı (Cormack 2009).
RR_K = 60
#: Füzyonun her yoldan aldığı aday sayısı (havuz = birleşim). 300 DEĞİL:
#: eski ölçümlerde gizlenenin medyan sırası 159–356'ydı; 300'de kesmek
#: motorun tavanını yapay olarak düşürürdü.
YOL_DERINLIGI = 1000

#: Öznitelikler — sıra eğitimde ve puanlamada aynı olmalı.
OZNITELIKLER = ("rr_rp3", "rr_ease", "rr_liste", "rr_ses",
                "ortak_liste", "tohum_payi")
#: Öncül merkezi = üretimdeki melez (RRF, liste 1 : ses 2).
ONCUL = {"rr_liste": 1.0, "rr_ses": 2.0}


# --------------------------------------------------------------------------- #
# Bağlam listeleri
# --------------------------------------------------------------------------- #

#: Dil ve bağlam sözcükleri. Ruh hâli sözcükleri `etiket.BAGLAM_SOZLUGU`'ndan.
DIL_SOZCUKLERI = ("türkçe", "turkce", "türkce", "turkish", "yerli", "türk",
                  "turk", "deutsch", "español", "francais", "français")

#: Tarz sözcüğü taşıyan başlık bağlam DEĞİL: «türk rock», «japanese fusion».
TARZ_SOZCUKLERI = (
    "rock", "metal", "jazz", "fusion", "prog", "djent", "rap", "hip hop",
    "hiphop", "punk", "grunge", "blues", "funk", "soul", "city pop", "indie",
    "alternative", "alternatif", "guitar", "gitar", "shred", "math", "core",
    "thrash", "death", "psych", "anadolu", "anatolian", "electronic",
    "techno", "house", "classical", "klasik", "folk", "halk", "arabesk",
    "progressive", "instrumental", "enstrümantal",
)


def baglam_listesi_mi(baslik: str | None) -> bool:
    """Başlık dil ya da ruh hâli söylüyor ve tarz söylemiyorsa True."""
    from python.etiket import BAGLAM_SOZLUGU

    b = f" {(baslik or '').lower()} "
    if any(t in b for t in TARZ_SOZCUKLERI):
        return False
    sozcukler = re.findall(r"\w+", b)
    if any(s in DIL_SOZCUKLERI for s in sozcukler):
        return True
    return any(f" {t}" in b for terimler in BAGLAM_SOZLUGU.values() for t in terimler)


# --------------------------------------------------------------------------- #
# Grafik
# --------------------------------------------------------------------------- #

@dataclass
class Grafik:
    """İkili liste × sanatçı matrisi ve liste ağırlıkları."""
    B: np.ndarray                 # (liste × sanatçı) 0/1 float32
    anahtar: list[str]            # sütun → normalize sanatçı anahtarı
    sira: dict[str, int]          # anahtar → sütun
    liste_id: np.ndarray          # satır → liste kimliği
    w: np.ndarray                 # satır → bağlam ağırlığı
    baglam: np.ndarray            # satır → bağlam listesi mi (bool)
    ad: dict[str, str] = field(default_factory=dict)  # anahtar → okunur ad

    def satir_maskesi(self, haric: set[int] | frozenset[int] = frozenset()) -> np.ndarray:
        if not haric:
            return np.ones(len(self.liste_id), dtype=bool)
        return ~np.isin(self.liste_id, list(haric))


def grafik_kur(conn: sqlite3.Connection, *,
               baglam_agirligi: float = BAGLAM_AGIRLIGI) -> Grafik:
    """`liste_parca` tablosundan grafik. Sanatçı listede bir kez sayılır."""
    basliklar = {int(r[0]): r[1] for r in conn.execute(
        "SELECT liste_id, baslik FROM calma_listesi")}
    uyelik: dict[int, set[str]] = {}
    ad: dict[str, str] = {}
    for liste_id, anahtar, sanatci in conn.execute(
            "SELECT liste_id, sanatci_anahtar, sanatci FROM liste_parca "
            "WHERE sanatci_anahtar != ''"):
        uyelik.setdefault(int(liste_id), set()).add(anahtar)
        ad.setdefault(anahtar, sanatci)
    listeler = sorted(uyelik)
    anahtar = sorted({a for u in uyelik.values() for a in u})
    sira = {a: j for j, a in enumerate(anahtar)}
    B = np.zeros((len(listeler), len(anahtar)), dtype="float32")
    for i, lid in enumerate(listeler):
        B[i, [sira[a] for a in uyelik[lid]]] = 1.0
    baglam = np.array([baglam_listesi_mi(basliklar.get(l)) for l in listeler], dtype=bool)
    w = np.where(baglam, baglam_agirligi, 1.0).astype("float32")
    return Grafik(B, anahtar, sira, np.array(listeler, dtype=np.int64), w, baglam, ad)


# --------------------------------------------------------------------------- #
# Erişim — RP3β ve EASE
# --------------------------------------------------------------------------- #

def _tohumlar(G: Grafik, tohum: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    idx = [(G.sira[a], w) for a, w in tohum.items() if a in G.sira]
    if not idx:
        return np.zeros(0, dtype=int), np.zeros(0, dtype="float32")
    i, w = zip(*idx)
    return np.array(i), np.array(w, dtype="float32")


def rp3(G: Grafik, tohum: dict[str, float], *, alfa: float = ALFA,
        beta: float = BETA, satir: np.ndarray | None = None,
        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """RP3β (Paudel ve ark. 2017) tohum satırları için.

    Sanatçı i → liste p: P_ip = w_p·B_pi / Σ_p' w_p'·B_p'i   (ağırlıklı yürüyüş)
    Liste p → sanatçı j: P_pj = B_pj / n_p
    W_ij = Σ_p P_ip^α · P_pj^α  /  d_j^β        (d_j: j'nin liste sayısı)
    skor_j = Σ_i q_i · W_ij

    Dönen: (skor [n], katkı [|tohum| × n], ortak liste sayısı [|tohum| × n]).
    Katkı tohum başına ayrıştığı için gerekçe (K7) doğrudan buradan kurulur.
    `satir`: kullanılacak listeler (gizleme katmanında sızan listeler dışarıda).
    """
    i, q = _tohumlar(G, tohum)
    n = G.B.shape[1]
    if not i.size:
        return np.zeros(n), np.zeros((0, n)), np.zeros((0, n))
    B = G.B if satir is None else G.B[satir]
    w = G.w if satir is None else G.w[satir]
    n_p = B.sum(axis=1)
    d = B.sum(axis=0)
    Bi = B[:, i] * w[:, None]                                  # (m × |S|)
    payda = Bi.sum(axis=0)
    P_ip = np.divide(Bi, payda, out=np.zeros_like(Bi), where=payda > 0)
    # Üs yalnız sıfır olmayan geçişlere: 0**0 = 1 olurdu (α = 0'da her şey bağlı).
    P_ip = np.where(P_ip > 0, P_ip, 1.0) ** alfa * (P_ip > 0)
    P_pj = B * (np.where(n_p > 0, n_p, 1.0) ** -alfa)[:, None]  # B ikili
    W = P_ip.T @ P_pj                                          # (|S| × n)
    W /= np.where(d > 0, d, 1.0) ** beta
    W[:, d == 0] = 0.0
    katki = q[:, None] * W
    ortak = B[:, i].T @ B
    return katki.sum(axis=0), katki, ortak


def ease(G: Grafik, tohum: dict[str, float], *, lam: float = LAMBDA,
         satir: np.ndarray | None = None) -> np.ndarray:
    """EASE (Steck 2019), Woodbury özdeşliğiyle: yalnız m×m ters alma.

    P = (XᵀX + λI)⁻¹ = (1/λ)[I − Xᵀ(λI + XXᵀ)⁻¹X],   X = √w · B
    B_ease = I − P·diag(P)⁻¹  ⇒  tohum dışı j için skor_j = −(qP)_j / P_jj
    m = 482 ≪ n ≈ 10 bin: 10k×10k (~400 MB) yerine 482×482 ters alınıyor.
    """
    i, q = _tohumlar(G, tohum)
    n = G.B.shape[1]
    if not i.size:
        return np.zeros(n)
    B = G.B if satir is None else G.B[satir]
    w = G.w if satir is None else G.w[satir]
    X = (np.sqrt(w)[:, None] * B).astype("float64")
    m = X.shape[0]
    K_ters = np.linalg.inv(lam * np.eye(m) + X @ X.T)
    KX = K_ters @ X                                            # (m × n)
    qXt = X[:, i] @ q                                          # (m,)
    qP = -(qXt @ KX) / lam
    qP[i] += q / lam
    diagP = (1.0 - np.einsum("pj,pj->j", X, KX)) / lam
    skor = -qP / diagP
    skor[i] = 0.0
    skor[B.sum(axis=0) == 0] = 0.0
    return skor


def ortak_ozeti(G: Grafik, ortak: np.ndarray) -> tuple[dict[str, float], dict[str, float]]:
    """({aday: tohumlarla toplam ortak liste}, {aday: bağlı tohum payı})."""
    if not ortak.size:
        return {}, {}
    nz = np.flatnonzero(ortak.any(axis=0))
    toplam, pay = ortak[:, nz].sum(axis=0), (ortak[:, nz] > 0).mean(axis=0)
    return ({G.anahtar[j]: float(t) for j, t in zip(nz, toplam)},
            {G.anahtar[j]: float(p) for j, p in zip(nz, pay)})


def sirala(skor: np.ndarray, G: Grafik, sahip: set[str], derinlik: int = YOL_DERINLIGI
           ) -> list[str]:
    """Pozitif skorlu, sahip olunmayan sanatçılar — skora göre, kararlı."""
    sira = np.argsort(-skor, kind="stable")
    sonuc = []
    for j in sira:
        if skor[j] <= 0:
            break
        a = G.anahtar[j]
        if a in sahip:
            continue
        sonuc.append(a)
        if len(sonuc) >= derinlik:
            break
    return sonuc


# --------------------------------------------------------------------------- #
# Füzyon — koşullu logit
# --------------------------------------------------------------------------- #

def _rr(sira: list[str]) -> dict[str, float]:
    return {a: RR_K / (RR_K + r) for r, a in enumerate(sira, 1)}


def oznitelikler(
    yollar: dict[str, list[str]], *, ortak: dict[str, float] | None = None,
    tohum_payi: dict[str, float] | None = None,
) -> tuple[list[str], np.ndarray]:
    """Aday havuzu (yolların birleşimi) ve öznitelik matrisi [aday × OZNITELIKLER].

    `yollar`: {"rp3": [...], "ease": [...], "liste": [...], "ses": [...]}.
    Eksik yol sıfır sütun verir; sırası yoksa aday o yolda «yok» demektir.
    """
    ortak, tohum_payi = ortak or {}, tohum_payi or {}
    rr = {ad: _rr(s[:YOL_DERINLIGI]) for ad, s in yollar.items()}
    havuz: list[str] = []
    gorulen: set[str] = set()
    for ad in ("rp3", "ease", "liste", "ses"):
        for a in yollar.get(ad, [])[:YOL_DERINLIGI]:
            if a not in gorulen:
                gorulen.add(a)
                havuz.append(a)
    F = np.zeros((len(havuz), len(OZNITELIKLER)), dtype="float64")
    for k, a in enumerate(havuz):
        F[k] = (rr.get("rp3", {}).get(a, 0.0), rr.get("ease", {}).get(a, 0.0),
                rr.get("liste", {}).get(a, 0.0), rr.get("ses", {}).get(a, 0.0),
                np.log1p(ortak.get(a, 0.0)), tohum_payi.get(a, 0.0))
    return havuz, F


def oncul() -> np.ndarray:
    return np.array([ONCUL.get(ad, 0.0) for ad in OZNITELIKLER])


def logit_egit(ornekler: list[tuple[np.ndarray, int]], *, lam: float,
               mu: np.ndarray | None = None, adim: int = 50) -> np.ndarray:
    """Koşullu logit, MAP, Newton.

    ornekler: [(F_q [aday × d], pozitifin satırı)]. Her sorgu bir seçim kümesi,
    gizlenen sanatçı tek pozitif (eşleşmiş vaka–kontrol).
        ℓ(θ) = Σ_q [θᵀx_q+ − log Σ_j exp θᵀx_qj] − (λ/2)‖θ − μ‖²
    λ → ∞: θ = μ, yani üretimdeki füzyon.
    """
    d = len(OZNITELIKLER)
    mu = oncul() if mu is None else mu
    theta = mu.copy()

    def amac(t):
        return logit_olabilirlik(ornekler, t) - lam / 2 * float((t - mu) @ (t - mu))

    eski = amac(theta)
    for _ in range(adim):
        g = -lam * (theta - mu)
        H = lam * np.eye(d)
        for F, pos in ornekler:
            z = F @ theta
            p = np.exp(z - z.max())
            p /= p.sum()
            xbar = p @ F
            g += F[pos] - xbar
            H += (F * p[:, None]).T @ F - np.outer(xbar, xbar)
        dtheta = np.linalg.solve(H, g)
        # Adım yarılama: amaç içbükey ama tam Newton adımı küçük λ'da taşabilir.
        for _ in range(20):
            yeni = amac(theta + dtheta)
            if yeni >= eski - 1e-12:
                break
            dtheta /= 2
        theta, eski = theta + dtheta, yeni
        if np.abs(dtheta).max() < 1e-6:
            break
    return theta


def logit_olabilirlik(ornekler, theta: np.ndarray) -> float:
    toplam = 0.0
    for F, pos in ornekler:
        z = F @ theta
        toplam += z[pos] - (z.max() + np.log(np.exp(z - z.max()).sum()))
    return toplam


#: λ ızgarası — iç çapraz doğrulama seçer. Büyük uç = üretim füzyonu.
LAMBDA_IZGARASI = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 1e4)


def lambda_sec(ornekler, *, kat: int = 5, tohum: int = 0) -> float:
    """Gruplu k-katlı CV, ortalama dışarıda-bırakılan log-olabilirlik."""
    if len(ornekler) < kat * 2:
        return LAMBDA_IZGARASI[-1]
    rng = np.random.default_rng(tohum)
    katman = rng.permutation(len(ornekler)) % kat
    en_iyi, en_iyi_ll = LAMBDA_IZGARASI[-1], -np.inf
    for lam in LAMBDA_IZGARASI:
        ll = 0.0
        for k in range(kat):
            egit = [o for o, c in zip(ornekler, katman) if c != k]
            sina = [o for o, c in zip(ornekler, katman) if c == k]
            ll += logit_olabilirlik(sina, logit_egit(egit, lam=lam))
        if ll > en_iyi_ll + 1e-9:
            en_iyi, en_iyi_ll = lam, ll
    return en_iyi


def puanla(F: np.ndarray, theta: np.ndarray) -> np.ndarray:
    return F @ theta


def _ornek(r: dict):
    if r["hedef"] not in r["havuz"] or not len(r["havuz"]):
        return None
    return r["F"], r["havuz"].index(r["hedef"])


def _hedef_sirasi(r: dict, theta: np.ndarray) -> int | None:
    if r["hedef"] not in r["havuz"]:
        return None
    s = puanla(r["F"], theta)
    sira = np.argsort(-s, kind="stable")
    return int(np.flatnonzero(sira == r["havuz"].index(r["hedef"]))[0]) + 1


# --------------------------------------------------------------------------- #
# Eşli kıyas — "yeni eskiyi geçti mi?"
# --------------------------------------------------------------------------- #

def eslesmis_kiyas(rr_a: list[float], rr_b: list[float], *, tekrar: int = 20000,
                   tohum: int = 0) -> dict[str, float]:
    """Aynı sorgular üzerinde iki yöntemin karşılıklı sıraları (bulunmayan = 0).

    İşaret çevirmeli permütasyon testi (iki yönlü) + eşli bootstrap %95 aralık.
    Wilcoxon DEĞİL: çok sayıda sıfır fark ve eşitlikte simetri varsayımı
    bozuluyor (Urbano ve ark. 2019).
    """
    a, b = np.asarray(rr_a, float), np.asarray(rr_b, float)
    fark = a - b
    n = len(fark)
    rng = np.random.default_rng(tohum)
    gozlenen = fark.mean() if n else 0.0
    isaret = rng.choice((-1.0, 1.0), size=(tekrar, n))
    p = float((np.abs((isaret * fark).mean(axis=1)) >= abs(gozlenen) - 1e-12).mean())
    boot = fark[rng.integers(0, n, size=(tekrar, n))].mean(axis=1) if n else np.zeros(1)
    return {"fark": float(gozlenen), "alt": float(np.percentile(boot, 2.5)),
            "ust": float(np.percentile(boot, 97.5)), "p": p, "n": n,
            "a_mrr": float(a.mean()) if n else 0.0, "b_mrr": float(b.mean()) if n else 0.0}


# --------------------------------------------------------------------------- #
# Ayarlar
# --------------------------------------------------------------------------- #

def ayar_oku(yol: Path = AYAR_DOSYASI) -> dict:
    """Öğrenilmiş ayarlar; yoksa literatür varsayılanları + üretim füzyonu."""
    varsayilan = {"alfa": ALFA, "beta": BETA, "lam_ease": LAMBDA,
                  "baglam_agirligi": BAGLAM_AGIRLIGI,
                  "theta": oncul().tolist(), "ogrenildi": False}
    try:
        veri = json.loads(Path(yol).read_text())
    except (OSError, ValueError):
        return varsayilan
    if veri.get("oznitelikler") != list(OZNITELIKLER):
        return varsayilan       # öznitelik sırası değişmiş: eski θ geçersiz
    return {**varsayilan, **veri, "ogrenildi": True}


def ayar_yaz(ayar: dict, yol: Path = AYAR_DOSYASI) -> None:
    Path(yol).parent.mkdir(parents=True, exist_ok=True)
    Path(yol).write_text(json.dumps(
        {**ayar, "oznitelikler": list(OZNITELIKLER), "tarih": date.today().isoformat()},
        ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------- #
# Üretim — bir eksen için motor sırası
# --------------------------------------------------------------------------- #

_GRAFIK: dict[float, tuple[int, Grafik]] = {}


def _grafik(conn: sqlite3.Connection, baglam_agirligi: float) -> Grafik:
    """Grafik ORTAK veriden kurulur (K20: kullanıcıya özgü değil); liste
    sayısı değişince yeniden kurulur."""
    n = conn.execute("SELECT COUNT(*) FROM liste_parca").fetchone()[0]
    onceki = _GRAFIK.get(baglam_agirligi)
    if onceki is None or onceki[0] != n:
        _GRAFIK[baglam_agirligi] = (n, grafik_kur(conn, baglam_agirligi=baglam_agirligi))
    return _GRAFIK[baglam_agirligi][1]


def eksen_sirasi(conn: sqlite3.Connection, calisma_id: str, eksen: int, *,
                 adet: int = 12, ayar: dict | None = None) -> list[dict]:
    """Bir eksen için motorun sanatçı sırası ve her birinin kanıtı.

    Dönen: [{"anahtar", "ad", "skor", "kaynaklar", "tohumlar": [(ad, ortak)],
    "ortak_liste", "liste_sayisi", "ses": {...} | None}].
    """
    from python.discover.adaylar import eksen_sanatcilari
    from python.etiket_clap import acik_havuz_adaylari

    ayar = ayar or ayar_oku()
    G = _grafik(conn, ayar["baglam_agirligi"])
    sanatcilar = eksen_sanatcilari(conn, calisma_id, eksen, adet=40)
    if sanatcilar.empty:
        return []
    tohum = {normalize_esleme(a): 1.0 for a in sanatcilar.index}
    sahip = {normalize_esleme(r[0]) for r in conn.execute(
        "SELECT DISTINCT artist FROM albums") if r[0]}

    s_rp3, katki, ortak = rp3(G, tohum, alfa=ayar["alfa"], beta=ayar["beta"])
    s_ease = ease(G, tohum, lam=ayar["lam_ease"])
    yollar = {"rp3": sirala(s_rp3, G, sahip), "ease": sirala(s_ease, G, sahip)}

    yer = ",".join("?" * len(tohum))
    yollar["liste"] = [r[0] for r in conn.execute(
        f"""SELECT aday_anahtar FROM liste_birlikteligi
             WHERE kutuphane_anahtar IN ({yer}) GROUP BY aday_anahtar
             ORDER BY MAX(pmi) DESC LIMIT ?""", (*tohum, YOL_DERINLIGI))
        if r[0] not in sahip]
    ses_kayit = {normalize_esleme(k["sanatci"]): k
                 for k in acik_havuz_adaylari(conn, calisma_id, eksen, adet=YOL_DERINLIGI)}
    yollar["ses"] = [a for a in ses_kayit if a not in sahip]

    tohum_idx, _ = _tohumlar(G, tohum)
    toplam_ortak, pay = ortak_ozeti(G, ortak)
    populer = dict(zip(G.anahtar, G.B.sum(axis=0).tolist()))
    havuz, F = oznitelikler(yollar, ortak=toplam_ortak, tohum_payi=pay)
    if not havuz:
        return []
    skor = puanla(F, np.asarray(ayar["theta"]))
    sonuc = []
    for k in np.argsort(-skor, kind="stable")[:adet]:
        a = havuz[k]
        j = G.sira.get(a)
        tohumlar = []
        if j is not None and katki.size:
            for t in np.argsort(-katki[:, j])[:3]:
                if ortak[t, j] > 0:
                    tohumlar.append((G.ad.get(G.anahtar[tohum_idx[t]], G.anahtar[tohum_idx[t]]),
                                     int(ortak[t, j])))
        kaynaklar = [ad for ad, sutun in (("rp3", 0), ("ease", 1), ("liste", 2), ("ses", 3))
                     if F[k, sutun] > 0]
        sonuc.append({
            "anahtar": a, "ad": G.ad.get(a) or (ses_kayit.get(a) or {}).get("sanatci") or a,
            "skor": float(skor[k]), "kaynaklar": kaynaklar, "tohumlar": tohumlar,
            "ortak_liste": int(toplam_ortak.get(a, 0)),
            "liste_sayisi": int(populer.get(a, 0)),
            "ses": ses_kayit.get(a),
        })
    return sonuc


def main(argv: list[str] | None = None) -> int:
    from python.db import VARSAYILAN_DB, baglan
    from python import degerlendirme as D

    ay = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ay.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ay.add_argument("--calisma")
    ay.add_argument("--limit", type=int)
    ay.add_argument("--egit", action="store_true",
                    help="RP3β/EASE ayarla, füzyonu öğren, ölç ve motor.json'a yaz")
    ay.add_argument("--yazma", action="store_true", help="ölç ama ayarı yazma")
    args = ay.parse_args(argv)
    if not args.egit:
        ay.error("--egit verilmeli")

    conn = baglan(args.db)
    try:
        sonuc = D.calistir(conn, limit=args.limit, calisma=args.calisma,
                           olcut="npmi", buzulme=1.0, melez_agirlik=(1.0, 2.0),
                           motor=True)
        print(D.rapor(sonuc))
        print(D.motor_raporu(sonuc))
        if not args.yazma and "_motor_ayar" in sonuc:
            ayar_yaz(sonuc["_motor_ayar"])
            print(f"\nAyar yazıldı: {AYAR_DOSYASI}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
