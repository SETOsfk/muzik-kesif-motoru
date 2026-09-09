"""Bootstrap Jaccard stabilitesi (Hennig'in yordamı, K3).

Bir küme "gerçek" mi yoksa bu veri kümesinin kazası mı? Yordam:

1. Albümler yerine koyarak yeniden örneklenir (bootstrap).
2. Aynı c ile FCM yeniden çalıştırılır.
3. Orijinal her küme için, bootstrap kümeleri arasındaki EN İYİ Jaccard bulunur.
4. B tekrarın ortalaması o kümenin stabilitesidir.

Yorum (Hennig 2007): ≥0.85 çok stabil, 0.75–0.85 stabil, 0.60–0.75 kararsız
ama anlamlı olabilir, <0.60 güvenilmez. Projede eşik 0.60 — altındaki kümeler
kullanıcıya isimlendirme için gösterilmez, çünkü isimlendirilen şeyin bir daha
aynı yerde çıkacağının garantisi yok.

Jaccard keskin atamalar üzerinden hesaplanır: bulanık üyeliğin küme kimliği
argmax'tır, küme "kimliği" sorusu keskin bir sorudur.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from python.kumeleme.fcm import fcm


@dataclass(frozen=True)
class StabiliteSonuc:
    jaccard: np.ndarray        # (c,) küme başına ortalama
    tekrar: int
    esik: float

    @property
    def stabil_mi(self) -> np.ndarray:
        return self.jaccard >= self.esik

    def ozet(self) -> str:
        stabil = int(self.stabil_mi.sum())
        return (
            f"{stabil}/{len(self.jaccard)} küme stabil (eşik {self.esik:.2f}, "
            f"{self.tekrar} bootstrap)"
        )


def _jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    birlesim = len(a | b)
    return len(a & b) / birlesim if birlesim else 0.0


def bootstrap_jaccard(
    X: np.ndarray,
    orijinal_atama: np.ndarray,
    c: int,
    m: float,
    *,
    tekrar: int = 50,
    esik: float = 0.60,
    baslangic: int = 3,
    tohum: int = 0,
) -> StabiliteSonuc:
    """Her küme için ortalama en iyi Jaccard.

    baslangic burada düşük tutulur (varsayılan 3): bootstrap zaten B kez FCM
    çalıştırıyor, her birinde 10 rastgele başlangıç maliyeti gereksiz.
    """
    n = X.shape[0]
    rng = np.random.default_rng(tohum)
    skorlar = np.zeros((tekrar, c), dtype=float)

    for tur in range(tekrar):
        secim = rng.integers(0, n, size=n)
        tekil = np.unique(secim)
        if len(tekil) <= c:  # dejenere örnek, bu turu atla
            skorlar[tur] = np.nan
            continue

        try:
            yeni = fcm(
                X[tekil], c, m, baslangic=baslangic, tohum=tohum + tur * 101
            )
        except ValueError:
            skorlar[tur] = np.nan
            continue

        yeni_atama = yeni.keskin_atama()
        yeni_kumeler = [set(tekil[yeni_atama == k].tolist()) for k in range(c)]

        for kume in range(c):
            # Orijinal küme, bootstrap örneğinde görünen üyeleriyle karşılaştırılır.
            orijinal = set(tekil[orijinal_atama[tekil] == kume].tolist())
            if not orijinal:
                skorlar[tur, kume] = np.nan
                continue
            skorlar[tur, kume] = max(_jaccard(orijinal, yeni_k) for yeni_k in yeni_kumeler)

    with np.errstate(invalid="ignore"):
        ortalama = np.nanmean(skorlar, axis=0)
    return StabiliteSonuc(jaccard=np.nan_to_num(ortalama), tekrar=tekrar, esik=esik)
