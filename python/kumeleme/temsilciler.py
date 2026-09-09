"""Küme temsilcisi albüm seçimi (K4) ve küme profili.

K4: en yüksek üyelikli 5 albümü almak yanlış — aynı sanatçının 5 albümü çıkar,
küme kimliği anlaşılmaz. Üst %20 üyelikten başlanır ve aralarında maksimum
çeşitlilik olanlar seçilir (max-min mesafe / açgözlü uzak nokta örneklemesi).

Ek olarak `kume_profili`: kümeyi asıl anlatan şey temsilci albümler değil,
kümenin hangi öznitelikler etrafında toplandığıdır — "bu küme şu davulcunun
etrafında dönüyor" bilgisi isimlendirmeyi kolaylaştırır.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def temsilci_sec(
    X: np.ndarray,
    uyelik: np.ndarray,
    kume: int,
    *,
    adet: int = 5,
    ust_dilim: float = 0.80,
    ayni_sanatci_cezasi: np.ndarray | None = None,
) -> list[int]:
    """Küme için temsilci albüm indeksleri.

    ayni_sanatci_cezasi: (n,) sanatçı kimliği dizisi verilirse, aynı sanatçıdan
    ikinci albüm ancak başka aday kalmadığında seçilir.
    """
    u = uyelik[:, kume]
    if u.size == 0:
        return []

    # Havuz, kümeye KESKİN olarak atanmış albümlerden kurulur. Önceki iki sürüm
    # de yanlıştı ve sonucu şöyle bozuyordu (ölçüldü, c=12):
    #   1. temsilcinin üyeliği ortalama 0.98, diğer dördününki 0.22.
    # Sebep: yüzdelik tüm kütüphaneden hesaplanıyordu ve 1/c tabanı (c=12 için
    # 0.083) neredeyse hiçbir şeyi elemiyordu. Max-min çeşitlilik de doğal olarak
    # kümenin KENARINI seçiyordu — yani kümeye zar zor ait albümleri.
    #
    # Artık: önce keskin üyeler, sonra onların üst yarısı, sonra çeşitlilik.
    # Böylece her temsilci gerçekten o kümenin albümü oluyor. K4'ün "üst %20"si
    # burada kümenin kendi içinde okunuyor; %20 birebir uygulanırsa 25 üyeli bir
    # kümede tam 5 aday kalıyor ve seçilecek bir şey kalmıyor.
    uyeler = np.flatnonzero(np.argmax(uyelik, axis=1) == kume)
    if uyeler.size == 0:
        uyeler = np.argsort(-u)[: max(adet * 3, 1)]

    sirali = uyeler[np.argsort(-u[uyeler])]
    havuz_boyu = max(adet * 3, int(np.ceil(sirali.size * (1.0 - ust_dilim) * 2.5)), adet)
    havuz = sirali[:havuz_boyu]

    if havuz.size <= adet:
        return sorted(havuz.tolist(), key=lambda i: -u[i])

    # 1. temsilci: kümenin en tipik albümü.
    secilenler = [int(havuz[np.argmax(u[havuz])])]

    while len(secilenler) < adet:
        kalan = [i for i in havuz.tolist() if i not in secilenler]
        if not kalan:
            break
        kalan_dizi = np.array(kalan)
        # Seçilenlere olan en küçük mesafe — onu büyüten aday kazanır (max-min).
        farklar = X[kalan_dizi][:, None, :] - X[secilenler][None, :, :]
        mesafeler = np.sqrt(np.einsum("ksp,ksp->ks", farklar, farklar))
        en_yakin = mesafeler.min(axis=1)

        if ayni_sanatci_cezasi is not None:
            secili_sanatcilar = {ayni_sanatci_cezasi[i] for i in secilenler}
            tekrar = np.array(
                [ayni_sanatci_cezasi[i] in secili_sanatcilar for i in kalan], dtype=bool
            )
            # Ceza: aynı sanatçı ancak gerçekten çeşitlilik katıyorsa girsin.
            en_yakin = np.where(tekrar, en_yakin * 0.25, en_yakin)

        secilenler.append(int(kalan_dizi[int(np.argmax(en_yakin))]))

    return secilenler


def kume_profili(
    matris: pd.DataFrame, uyelik: np.ndarray, kume: int, *, adet: int = 8
) -> pd.DataFrame:
    """Kümeyi tanımlayan öznitelikler: üyelikle ağırlıklı ortalamanın en yükseği.

    Kütüphane geneline göre fark alınır — her kümede çıkan "rock" etiketi o
    kümeyi anlatmaz, onu diğerlerinden ayıran şey anlatır.
    """
    u = uyelik[:, kume]
    toplam = u.sum()
    if toplam <= 0:
        return pd.DataFrame(columns=["ozellik", "blok", "kume_ort", "genel_ort", "fark"])

    degerler = matris.to_numpy(dtype=float)
    kume_ort = (u[:, None] * degerler).sum(axis=0) / toplam
    genel_ort = degerler.mean(axis=0)
    fark = kume_ort - genel_ort

    profil = pd.DataFrame(
        {
            "ozellik": [s.split("__", 1)[-1] for s in matris.columns],
            "blok": [s.split("__", 1)[0] for s in matris.columns],
            "kume_ort": kume_ort,
            "genel_ort": genel_ort,
            "fark": fark,
        }
    )
    return profil.sort_values("fark", ascending=False).head(adet).reset_index(drop=True)


def ortusen_albumler(
    uyelik: np.ndarray, *, esik: float = 0.30, adet: int = 20
) -> pd.DataFrame:
    """İki ekseni birden besleyen albümler — bulanık kümelemenin asıl kazancı.

    En yüksek iki üyeliği de eşiğin üstünde olan albümler; keskin kümeleme bu
    bilgiyi tamamen kaybederdi (K3).
    """
    if uyelik.shape[1] < 2:
        return pd.DataFrame(columns=["satir", "kume_a", "kume_b", "uyelik_a", "uyelik_b"])

    sirali = np.argsort(-uyelik, axis=1)
    ilk = sirali[:, 0]
    ikinci = sirali[:, 1]
    u_ilk = uyelik[np.arange(len(ilk)), ilk]
    u_ikinci = uyelik[np.arange(len(ikinci)), ikinci]

    maske = u_ikinci >= esik
    cerceve = pd.DataFrame(
        {
            "satir": np.flatnonzero(maske),
            "kume_a": ilk[maske],
            "kume_b": ikinci[maske],
            "uyelik_a": u_ilk[maske],
            "uyelik_b": u_ikinci[maske],
        }
    )
    return cerceve.sort_values("uyelik_b", ascending=False).head(adet).reset_index(drop=True)
