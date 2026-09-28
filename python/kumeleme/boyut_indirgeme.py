"""Blok ağırlıklandırma ve boyut indirgeme.

K3: "Yüksek boyutta FCM üyelikleri 1/c'ye yakınsar → önce boyut indirgeme."
Sebep mesafe yoğunlaşması: p büyüdükçe en yakın ve en uzak komşu arasındaki
göreli fark kaybolur, u_ij → 1/c olur ve bulanık üyelik bilgi taşımaz hale gelir.

Varsayılan PCA (bağımlılıksız, deterministik, bileşen sayısı açıklanan varyansla
gerekçelendirilebilir). UMAP `umap-learn` kuruluysa seçilebilir — yerel yapıyı
daha iyi korur ama stokastiktir ve tohuma bağlıdır.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class IndirgemeSonuc:
    X: np.ndarray                 # (n, k) indirgenmiş uzay
    yontem: str
    bilesen: int
    aciklanan_varyans: float | None
    orijinal_boyut: int

    def ozet(self) -> str:
        if self.aciklanan_varyans is None:
            return f"{self.yontem.upper()}: {self.orijinal_boyut} → {self.bilesen} boyut"
        return (
            f"{self.yontem.upper()}: {self.orijinal_boyut} → {self.bilesen} boyut "
            f"(açıklanan varyans %{self.aciklanan_varyans * 100:.1f})"
        )


def blok_adi(sutun: str) -> str:
    """'kredi__Neil Peart' → 'kredi'."""
    return sutun.split("__", 1)[0] if "__" in sutun else "bilinmeyen"


def bloklari_agirlikla(matris: pd.DataFrame, agirliklar: dict[str, float]) -> pd.DataFrame:
    """Her bloğu kendi ağırlığıyla çarp. Ağırlığı verilmeyen blok 1.0 alır."""
    agirlikli = matris.copy()
    for sutun in matris.columns:
        katsayi = agirliklar.get(blok_adi(sutun), 1.0)
        if katsayi != 1.0:
            agirlikli[sutun] = agirlikli[sutun] * katsayi
    return agirlikli


def blok_ozeti(matris: pd.DataFrame, agirliklar: dict[str, float]) -> pd.DataFrame:
    """Hangi blok mesafeye ne kadar katkı veriyor — ağırlık ayarlamanın tek dayanağı.

    Pay AĞIRLIK UYGULANDIKTAN sonra hesaplanır. Ham pay yanıltıcı olur: asıl
    merak edilen "kredi bloğu kararı gerçekten domine ediyor mu" sorusudur ve
    onun cevabı ağırlıklı enerjidedir (ağırlık kareli girer, çünkü mesafe kareli).
    """
    satirlar = []
    for blok in sorted({blok_adi(s) for s in matris.columns}):
        sutunlar = [s for s in matris.columns if blok_adi(s) == blok]
        alt = matris[sutunlar].to_numpy(dtype=float)
        katsayi = agirliklar.get(blok, 1.0)
        satirlar.append(
            {
                "blok": blok,
                "sutun": len(sutunlar),
                "agirlik": katsayi,
                "ham_enerji": float((alt**2).sum()),
                "agirlikli_enerji": float((alt**2).sum()) * katsayi**2,
            }
        )
    ozet = pd.DataFrame(satirlar)
    toplam = ozet["agirlikli_enerji"].sum()
    ozet["enerji_payi"] = ozet["agirlikli_enerji"] / toplam if toplam > 0 else 0.0
    return ozet.sort_values("enerji_payi", ascending=False).reset_index(drop=True)


def pca(
    X: np.ndarray,
    *,
    aciklanan_varyans: float = 0.80,
    azami_bilesen: int = 30,
    asgari_bilesen: int = 2,
) -> IndirgemeSonuc:
    """Ortalaması alınmış SVD. Bileşen sayısı açıklanan varyansla belirlenir."""
    orijinal = X.shape[1]
    Xc = X - X.mean(axis=0, keepdims=True)
    # full_matrices=False: n×p yerine n×min(n,p) — büyük matriste bellek farkı.
    _, s, Vt = np.linalg.svd(Xc, full_matrices=False)

    varyans = s**2
    toplam = varyans.sum()
    if toplam <= 0:
        raise ValueError("Matriste hiç değişkenlik yok — kümeleme anlamsız.")
    oranlar = np.cumsum(varyans) / toplam

    k = int(np.searchsorted(oranlar, aciklanan_varyans) + 1)
    k = max(asgari_bilesen, min(k, azami_bilesen, Vt.shape[0]))

    return IndirgemeSonuc(
        X=Xc @ Vt[:k].T,
        yontem="pca",
        bilesen=k,
        aciklanan_varyans=float(oranlar[k - 1]),
        orijinal_boyut=orijinal,
    )


def umap(
    X: np.ndarray, *, bilesen: int = 10, komsu: int = 15, tohum: int = 0
) -> IndirgemeSonuc:
    try:
        import umap as umap_learn
    except ImportError as hata:
        raise SystemExit(
            "umap-learn kurulu değil. Ya `pip install umap-learn` ya da --yontem pca kullanın."
        ) from hata

    model = umap_learn.UMAP(
        n_components=min(bilesen, X.shape[1]),
        n_neighbors=min(komsu, max(2, X.shape[0] - 1)),
        metric="euclidean",
        random_state=tohum,  # tekrarlanabilirlik; paralelliği kapatır, kabul
    )
    return IndirgemeSonuc(
        X=np.asarray(model.fit_transform(X), dtype=float),
        yontem="umap",
        bilesen=min(bilesen, X.shape[1]),
        aciklanan_varyans=None,
        orijinal_boyut=X.shape[1],
    )


def boyut_indir(matris: pd.DataFrame, ayar) -> IndirgemeSonuc:
    """Ayara göre PCA ya da UMAP."""
    X = matris.to_numpy(dtype=float)
    if ayar.yontem == "umap":
        return umap(X, bilesen=ayar.umap_bilesen, komsu=ayar.umap_komsu, tohum=ayar.tohum)
    return pca(
        X,
        aciklanan_varyans=1.0,          # bileşen sayısını varyans değil ayar belirler
        azami_bilesen=ayar.bilesen,
        asgari_bilesen=ayar.asgari_bilesen,
    )


def spektral_gomme(S: np.ndarray, bilesen: int, *, komsu: int | None = None) -> np.ndarray:
    """Benzerlik matrisinden spektral gömme (Ng–Jordan–Weiss).

    PCA'ya ALTERNATİF (2026-09-28, yöntem notundaki soru 1): matris %1,4 dolu
    ve çoğu ikili; PCA varyansı en büyük yönleri arıyor, oysa burada soru
    «hangi albümler birbirine benziyor». Grafik tabanlı gömme doğrudan buna
    bakıyor: kNN benzerlik grafının normalleştirilmiş Laplace'ının en küçük
    `bilesen` özvektörü, satırlar birim uzunluğa ölçeklenir.

    `komsu` verilirse her albüm yalnız en benzer `komsu` albüme bağlanır
    (simetrik: biri ötekinin komşusuysa bağ var). Hiç bağı olmayan albüm
    çok küçük bir taban benzerlikle grafa tutturulur; yoksa sıfır satır
    ölçeklenemezdi.
    """
    S = np.array(S, dtype=float, copy=True)
    n = S.shape[0]
    np.fill_diagonal(S, 0.0)
    S = np.clip(S, 0.0, None)
    if komsu is not None and komsu < n - 1:
        esik = -np.sort(-S, axis=1)[:, komsu - 1:komsu]
        S = np.where(S >= esik, S, 0.0)
        S = np.maximum(S, S.T)
    S += 1e-4 * (1.0 - np.eye(n))
    d = S.sum(axis=1)
    Dm = 1.0 / np.sqrt(d)
    L = np.eye(n) - (Dm[:, None] * S * Dm[None, :])
    _, vektor = np.linalg.eigh(L)
    X = vektor[:, :bilesen].copy()
    for j in range(X.shape[1]):               # işaret belirsizliğini sabitle (K2)
        if X[np.argmax(np.abs(X[:, j])), j] < 0:
            X[:, j] *= -1
    norm = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.maximum(norm, 1e-12)
