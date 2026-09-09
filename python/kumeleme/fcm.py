"""Bulanık c-ortalamalar (FCM) ve geçerlilik indeksleri.

Bezdek'in alternating optimization'ı. Kütüphane kullanmak yerine açıkça yazıldı:
algoritma kısa, savunması gereken bir metodolojinin görünür olması iyi, ve
scikit-fuzzy'nin bakımı seyrek.

    J_m = Σ_i Σ_j u_ij^m ||x_j − v_i||²

    v_i = Σ_j u_ij^m x_j / Σ_j u_ij^m
    u_ij = 1 / Σ_k (d_ij / d_kj)^(2/(m−1))

Geçerlilik indeksleri (K3):
  Xie-Beni        XB = J_m / (n · min_{i≠k} ||v_i − v_k||²)   → küçük olan iyi
  Partition entropy  PE = −(1/n) Σ u log u, log c ile normalize  → küçük = keskin
  Partition coeff.   PC = (1/n) Σ u²                            → büyük = keskin

m=2 kullanılmaz (K3): yüksek boyutta üyelikler 1/c'ye yakınsar, kümeler erir.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

EPS = 1e-12


@dataclass(frozen=True)
class FcmSonuc:
    uyelik: np.ndarray      # (n, c) — satır toplamı 1
    merkezler: np.ndarray   # (c, p)
    amac: float             # J_m
    yineleme: int
    yakinsadi: bool

    @property
    def c(self) -> int:
        return self.merkezler.shape[0]

    def keskin_atama(self) -> np.ndarray:
        """En yüksek üyelikli küme — Jaccard ve raporlama için."""
        return np.argmax(self.uyelik, axis=1)


def _mesafe_kare(X: np.ndarray, V: np.ndarray) -> np.ndarray:
    """(n, c) kare öklid mesafeleri."""
    fark = X[:, None, :] - V[None, :, :]
    return np.einsum("ncp,ncp->nc", fark, fark)


def _uyelik_guncelle(d2: np.ndarray, m: float) -> np.ndarray:
    ussu = 1.0 / (m - 1.0)
    d2 = np.maximum(d2, EPS)

    # Bir nokta tam merkeze düşerse (d=0) üyeliği o kümede 1 olmalı; genel formül
    # burada 0/0 verir.
    tam_ustunde = d2 <= EPS * 10
    ters = (1.0 / d2) ** ussu
    U = ters / np.maximum(ters.sum(axis=1, keepdims=True), EPS)

    kilitli = tam_ustunde.any(axis=1)
    if kilitli.any():
        U[kilitli] = 0.0
        U[kilitli] = tam_ustunde[kilitli] / tam_ustunde[kilitli].sum(axis=1, keepdims=True)
    return U


def _merkez_guncelle(X: np.ndarray, U: np.ndarray, m: float) -> np.ndarray:
    Um = U**m
    return (Um.T @ X) / np.maximum(Um.sum(axis=0)[:, None], EPS)


def fcm_tek(
    X: np.ndarray,
    c: int,
    m: float,
    *,
    yineleme: int = 300,
    tolerans: float = 1e-6,
    rng: np.random.Generator,
) -> FcmSonuc:
    """Tek rastgele başlangıçtan FCM."""
    n = X.shape[0]
    U = rng.dirichlet(np.ones(c), size=n)
    V = _merkez_guncelle(X, U, m)
    amac = np.inf
    yakinsadi = False
    adim = 0

    for adim in range(1, yineleme + 1):
        d2 = _mesafe_kare(X, V)
        U = _uyelik_guncelle(d2, m)
        V = _merkez_guncelle(X, U, m)
        yeni_amac = float(((U**m) * _mesafe_kare(X, V)).sum())
        if abs(amac - yeni_amac) < tolerans:
            amac = yeni_amac
            yakinsadi = True
            break
        amac = yeni_amac

    return FcmSonuc(uyelik=U, merkezler=V, amac=amac, yineleme=adim, yakinsadi=yakinsadi)


def fcm(
    X: np.ndarray,
    c: int,
    m: float = 1.4,
    *,
    baslangic: int = 10,
    yineleme: int = 300,
    tolerans: float = 1e-6,
    tohum: int = 0,
) -> FcmSonuc:
    """Birden çok rastgele başlangıç, en düşük J_m kazanır.

    FCM yerel optimuma takılır; tek başlangıç sonucu tohuma bağımlı kılar.
    Sabit tohum + çok başlangıç = tekrarlanabilir ve daha iyi çözüm.
    """
    if c < 2:
        raise ValueError("c en az 2 olmalı")
    if not 1.0 < m < 5.0:
        raise ValueError("m 1 ile 5 arasında olmalı (K3: 1.3–1.6 önerilir)")
    if X.shape[0] <= c:
        raise ValueError(f"albüm sayısı ({X.shape[0]}) küme sayısından ({c}) büyük olmalı")

    en_iyi: FcmSonuc | None = None
    for tekrar in range(baslangic):
        rng = np.random.default_rng(tohum + tekrar)
        sonuc = fcm_tek(X, c, m, yineleme=yineleme, tolerans=tolerans, rng=rng)
        if en_iyi is None or sonuc.amac < en_iyi.amac:
            en_iyi = sonuc
    assert en_iyi is not None
    return en_iyi


# --------------------------------------------------------------------------- #
# Geçerlilik indeksleri
# --------------------------------------------------------------------------- #

def xie_beni(X: np.ndarray, sonuc: FcmSonuc, m: float) -> float:
    """J_m / (n · en yakın iki merkez arası kare mesafe). Küçük olan iyi."""
    V = sonuc.merkezler
    if V.shape[0] < 2:
        return float("inf")
    farklar = V[:, None, :] - V[None, :, :]
    merkez_mesafeleri = np.einsum("ikp,ikp->ik", farklar, farklar)
    np.fill_diagonal(merkez_mesafeleri, np.inf)
    en_yakin = float(merkez_mesafeleri.min())
    if en_yakin <= EPS:
        return float("inf")
    return float(sonuc.amac / (X.shape[0] * en_yakin))


def partition_entropy(sonuc: FcmSonuc, *, normalize: bool = True) -> float:
    """Küçük = keskin bölünme. Normalize edilirse 0–1, c'ler arası karşılaştırılabilir."""
    U = np.clip(sonuc.uyelik, EPS, 1.0)
    pe = float(-(U * np.log(U)).sum() / U.shape[0])
    if normalize and sonuc.c > 1:
        pe /= np.log(sonuc.c)
    return pe


def partition_coefficient(sonuc: FcmSonuc) -> float:
    """Büyük = keskin bölünme (1/c ile 1 arası)."""
    return float((sonuc.uyelik**2).sum() / sonuc.uyelik.shape[0])


@dataclass(frozen=True)
class Tarama:
    c: int
    xie_beni: float
    partition_entropy: float
    partition_coefficient: float
    amac: float
    sonuc: FcmSonuc


def c_tara(
    X: np.ndarray,
    c_araligi: tuple[int, int],
    m: float,
    *,
    baslangic: int = 10,
    yineleme: int = 300,
    tolerans: float = 1e-6,
    tohum: int = 0,
) -> list[Tarama]:
    """c aralığını tara, her c için indeksleri hesapla."""
    alt, ust = c_araligi
    ust = min(ust, X.shape[0] - 1)
    taramalar = []
    for c in range(max(2, alt), ust + 1):
        sonuc = fcm(
            X, c, m, baslangic=baslangic, yineleme=yineleme, tolerans=tolerans, tohum=tohum
        )
        taramalar.append(
            Tarama(
                c=c,
                xie_beni=xie_beni(X, sonuc, m),
                partition_entropy=partition_entropy(sonuc),
                partition_coefficient=partition_coefficient(sonuc),
                amac=sonuc.amac,
                sonuc=sonuc,
            )
        )
    return taramalar


def en_iyi_c(
    taramalar: list[Tarama],
    stabil_oranlar: dict[int, float] | None = None,
    asgari_stabil_oran: float = 1.0,
) -> Tarama:
    """Xie-Beni minimumu — ama önce stabilite süzgecinden geçenler arasından.

    K3 üç ölçüt sayıyor: Xie-Beni, partition entropy VE bootstrap stabilitesi.
    Stabilite hesaba katılmazsa XB c arttıkça düşmeye devam edip aralığın
    sonuna kaçar: gerçek kütüphanede c=13'e kadar düştü, ama o noktada kümeler
    11 albüme inmiş ve yarısı kararsızdı. Önce "bütün kümeleri stabil olan c"
    adayları süzülür, XB kararı onların arasında verir.

    `stabil_oranlar`: c → stabil küme oranı (0–1). Verilmezse eski davranış.
    """
    if stabil_oranlar:
        adaylar = [
            t for t in taramalar
            if stabil_oranlar.get(t.c, 0.0) >= asgari_stabil_oran
        ]
        if adaylar:
            return min(adaylar, key=lambda t: (t.xie_beni, t.partition_entropy))
        # Hiçbir c'de tüm kümeler stabil değilse eşiği gevşet, yine de en
        # stabil olanı tercih et — sessizce XB'ye düşmek yanıltıcı olur.
        en_stabil = max(stabil_oranlar.values(), default=0.0)
        if en_stabil > 0:
            adaylar = [
                t for t in taramalar
                if stabil_oranlar.get(t.c, 0.0) >= en_stabil - 1e-9
            ]
            return min(adaylar, key=lambda t: (t.xie_beni, t.partition_entropy))
    return min(taramalar, key=lambda t: (t.xie_beni, t.partition_entropy))
