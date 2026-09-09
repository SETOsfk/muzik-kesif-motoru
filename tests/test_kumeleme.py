"""Kümeleme testleri. numpy/pandas gerektirir (.venv içinden çalıştırın).

    .venv/bin/python tests/test_kumeleme.py

Testlerin çoğu "bilinen yapıyı geri bulabiliyor mu" biçiminde: yapay olarak
ayrılmış kümeler üretilir, FCM'in onları bulması beklenir. Doğru cevabı bilmeden
kümeleme test edilemez.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import numpy as np
    import pandas as pd
except ImportError:  # pragma: no cover
    print("numpy/pandas yok — .venv/bin/python ile çalıştırın")
    raise SystemExit(0)

from python.kumeleme.ayar import VARSAYILAN, Ayar
from python.kumeleme.boyut_indirgeme import (
    blok_adi,
    blok_ozeti,
    bloklari_agirlikla,
    pca,
)
from python.kumeleme.fcm import (
    c_tara,
    en_iyi_c,
    fcm,
    partition_coefficient,
    partition_entropy,
    xie_beni,
)
from python.kumeleme.stabilite import bootstrap_jaccard
from python.kumeleme.temsilciler import kume_profili, ortusen_albumler, temsilci_sec


def _kumeli_veri(kume_sayisi=3, kume_basina=25, yayilim=0.35, tohum=7):
    """Birbirinden iyi ayrılmış kume_sayisi tane küre."""
    rng = np.random.default_rng(tohum)
    merkezler = np.eye(kume_sayisi) * 6.0
    X = np.vstack(
        [rng.normal(m, yayilim, size=(kume_basina, kume_sayisi)) for m in merkezler]
    )
    etiketler = np.repeat(np.arange(kume_sayisi), kume_basina)
    return X, etiketler


def _eslesme_orani(atama: np.ndarray, gercek: np.ndarray) -> float:
    """Küme numaraları keyfi; her gerçek küme için en iyi eşleşmeyi say."""
    dogru = 0
    for kume in np.unique(gercek):
        maske = gercek == kume
        if maske.sum():
            dogru += np.bincount(atama[maske]).max()
    return dogru / len(gercek)


# --------------------------------------------------------------------------- #
# FCM
# --------------------------------------------------------------------------- #

def test_uyelikler_toplami_bir():
    """OKUBENI #4: her albümün üyelik toplamı 1 olmalı."""
    X, _ = _kumeli_veri()
    sonuc = fcm(X, 3, m=1.4, baslangic=3, tohum=1)
    toplamlar = sonuc.uyelik.sum(axis=1)
    assert np.allclose(toplamlar, 1.0), toplamlar[:5]
    assert (sonuc.uyelik >= 0).all()


def test_fcm_bilinen_yapiyi_bulur():
    X, gercek = _kumeli_veri(kume_sayisi=4, kume_basina=20)
    sonuc = fcm(X, 4, m=1.4, baslangic=5, tohum=1)
    assert _eslesme_orani(sonuc.keskin_atama(), gercek) > 0.98


def test_ayni_tohum_ayni_sonuc():
    """Tekrarlanabilirlik: K1/K2 gereği, kümeleme deterministik olmalı."""
    X, _ = _kumeli_veri()
    a = fcm(X, 3, m=1.4, baslangic=3, tohum=42)
    b = fcm(X, 3, m=1.4, baslangic=3, tohum=42)
    assert np.allclose(a.uyelik, b.uyelik)
    assert a.amac == b.amac


def test_farkli_tohum_ayni_yapiyi_bulur():
    X, gercek = _kumeli_veri()
    for tohum in (0, 5, 99):
        sonuc = fcm(X, 3, m=1.4, baslangic=5, tohum=tohum)
        assert _eslesme_orani(sonuc.keskin_atama(), gercek) > 0.98, tohum


def test_gecersiz_parametreler():
    X, _ = _kumeli_veri()
    for cagri in (
        lambda: fcm(X, 1, m=1.4),
        lambda: fcm(X, 3, m=1.0),
        lambda: fcm(X, 3, m=9.0),
        lambda: fcm(X[:2], 3, m=1.4),
    ):
        try:
            cagri()
        except ValueError:
            continue
        raise AssertionError("geçersiz parametre ValueError vermeliydi")


def test_m_kucukse_uyelik_keskinlesir():
    """m → 1 keskin, m büyüdükçe bulanık. K3'ün m=2 uyarısının dayanağı."""
    X, _ = _kumeli_veri(yayilim=1.2)
    keskin = partition_coefficient(fcm(X, 3, m=1.15, baslangic=3, tohum=3))
    bulanik = partition_coefficient(fcm(X, 3, m=2.0, baslangic=3, tohum=3))
    assert keskin > bulanik


# --------------------------------------------------------------------------- #
# Geçerlilik indeksleri
# --------------------------------------------------------------------------- #

def test_xie_beni_dogru_c_de_en_dusuk():
    X, _ = _kumeli_veri(kume_sayisi=3, kume_basina=25)
    taramalar = c_tara(X, (2, 6), m=1.4, baslangic=3, tohum=2)
    assert en_iyi_c(taramalar).c == 3


def test_partition_entropy_keskinde_sifira_yakin():
    X, _ = _kumeli_veri(yayilim=0.15)
    keskin = fcm(X, 3, m=1.3, baslangic=3, tohum=4)
    assert partition_entropy(keskin) < 0.05

    # Tek noktaya toplanmış veri: hiçbir yapı yok, entropi yüksek olmalı.
    rng = np.random.default_rng(0)
    gurultu = rng.normal(0, 1, size=(60, 3))
    assert partition_entropy(fcm(gurultu, 3, m=1.9, baslangic=3, tohum=4)) > 0.3


def test_xie_beni_tek_merkezde_sonsuz():
    X, _ = _kumeli_veri()
    sonuc = fcm(X, 2, m=1.4, baslangic=2, tohum=1)
    tek_merkez = type(sonuc)(
        uyelik=sonuc.uyelik[:, :1], merkezler=sonuc.merkezler[:1],
        amac=sonuc.amac, yineleme=1, yakinsadi=True,
    )
    assert xie_beni(X, tek_merkez, 1.4) == float("inf")


# --------------------------------------------------------------------------- #
# Boyut indirgeme ve blok ağırlıkları
# --------------------------------------------------------------------------- #

def test_blok_adi():
    assert blok_adi("kredi__Neil Peart") == "kredi"
    assert blok_adi("ses__tempo_medyan") == "ses"
    assert blok_adi("onceksiz") == "bilinmeyen"


def test_bloklari_agirlikla():
    matris = pd.DataFrame({"kredi__a": [1.0, 2.0], "ses__b": [1.0, 1.0]})
    agirlikli = bloklari_agirlikla(matris, {"kredi": 2.0, "ses": 0.5})
    assert agirlikli["kredi__a"].tolist() == [2.0, 4.0]
    assert agirlikli["ses__b"].tolist() == [0.5, 0.5]


def test_blok_ozeti_agirliktan_sonra_hesaplar():
    matris = pd.DataFrame({"kredi__a": [1.0, 1.0], "ses__b": [1.0, 1.0]})
    ozet = blok_ozeti(matris, {"kredi": 2.0, "ses": 1.0}).set_index("blok")
    # Ham enerjiler eşit; ağırlık kareli girdiği için pay 4:1 olmalı.
    assert abs(ozet.loc["kredi", "enerji_payi"] - 0.8) < 1e-9
    assert abs(ozet.loc["ses", "enerji_payi"] - 0.2) < 1e-9
    assert abs(ozet["enerji_payi"].sum() - 1.0) < 1e-9


def test_pca_boyut_indirir():
    X, _ = _kumeli_veri(kume_sayisi=3, kume_basina=20)
    # 3 boyutlu veriyi 10 boyuta gömüp geri indirgenmesini bekle.
    rng = np.random.default_rng(0)
    donusum = rng.normal(size=(3, 10))
    sonuc = pca(X @ donusum, aciklanan_varyans=0.90, azami_bilesen=8)
    assert sonuc.orijinal_boyut == 10
    assert 2 <= sonuc.bilesen <= 8
    assert sonuc.aciklanan_varyans >= 0.90
    assert sonuc.X.shape == (X.shape[0], sonuc.bilesen)


def test_pca_yapiyi_korur():
    X, gercek = _kumeli_veri(kume_sayisi=3, kume_basina=20)
    indirgenmis = pca(X, aciklanan_varyans=0.95).X
    sonuc = fcm(indirgenmis, 3, m=1.4, baslangic=3, tohum=1)
    assert _eslesme_orani(sonuc.keskin_atama(), gercek) > 0.98


def test_pca_degisken_olmayan_matriste_hata():
    try:
        pca(np.ones((10, 4)))
    except ValueError:
        return
    raise AssertionError("değişkenliği olmayan matriste hata bekleniyordu")


# --------------------------------------------------------------------------- #
# Stabilite
# --------------------------------------------------------------------------- #

def test_ayrik_kumeler_stabil():
    X, _ = _kumeli_veri(kume_sayisi=3, kume_basina=25, yayilim=0.3)
    sonuc = fcm(X, 3, m=1.4, baslangic=3, tohum=1)
    stabilite = bootstrap_jaccard(
        X, sonuc.keskin_atama(), 3, 1.4, tekrar=15, tohum=1
    )
    assert stabilite.stabil_mi.all(), stabilite.jaccard
    assert (stabilite.jaccard > 0.8).all()


def test_yapisiz_veride_stabilite_duser():
    """Tek bir bulutu zorla 4'e bölersen kümeler tekrarlanmaz."""
    rng = np.random.default_rng(3)
    X = rng.normal(0, 1, size=(70, 4))
    sonuc = fcm(X, 4, m=1.4, baslangic=3, tohum=1)
    stabilite = bootstrap_jaccard(X, sonuc.keskin_atama(), 4, 1.4, tekrar=15, tohum=1)
    assert stabilite.jaccard.mean() < 0.8, stabilite.jaccard


# --------------------------------------------------------------------------- #
# Temsilciler
# --------------------------------------------------------------------------- #

def test_temsilci_sayisi_ve_cesitlilik():
    X, _ = _kumeli_veri(kume_sayisi=2, kume_basina=40)
    sonuc = fcm(X, 2, m=1.4, baslangic=3, tohum=1)
    secilenler = temsilci_sec(X, sonuc.uyelik, 0, adet=5)
    assert len(secilenler) == 5
    assert len(set(secilenler)) == 5

    # Max-min seçim, en yüksek 5 üyeliği almaktan daha yayılmış olmalı (K4).
    en_yuksekler = np.argsort(-sonuc.uyelik[:, 0])[:5]

    def yayilim(indeksler):
        alt = X[list(indeksler)]
        farklar = alt[:, None, :] - alt[None, :, :]
        return np.sqrt(np.einsum("ijp,ijp->ij", farklar, farklar)).sum()

    assert yayilim(secilenler) > yayilim(en_yuksekler)


def test_temsilci_ayni_sanatciyi_cezalandirir():
    X, _ = _kumeli_veri(kume_sayisi=2, kume_basina=30)
    sonuc = fcm(X, 2, m=1.4, baslangic=3, tohum=1)
    # İlk yarı tek sanatçı, ikinci yarı ayrı ayrı sanatçılar.
    sanatcilar = np.array(["Aynı"] * 30 + [f"S{i}" for i in range(30)])
    secilenler = temsilci_sec(X, sonuc.uyelik, 0, adet=5, ayni_sanatci_cezasi=sanatcilar)
    assert len({sanatcilar[i] for i in secilenler}) >= 2


def test_temsilci_kucuk_kumede_cokmez():
    X = np.random.default_rng(0).normal(size=(6, 3))
    U = np.full((6, 2), 0.5)
    secilenler = temsilci_sec(X, U, 0, adet=5)
    assert 0 < len(secilenler) <= 5


def test_ortusen_albumler():
    U = np.array([[0.9, 0.1], [0.5, 0.5], [0.45, 0.55], [0.99, 0.01]])
    ortusen = ortusen_albumler(U, esik=0.30)
    assert set(ortusen["satir"]) == {1, 2}
    assert ortusen.iloc[0]["uyelik_b"] >= ortusen.iloc[-1]["uyelik_b"]


def test_kume_profili_ayirt_ediciyi_bulur():
    matris = pd.DataFrame(
        {
            "kredi__ortak": [1.0, 1.0, 1.0, 1.0],   # herkeste var → ayırt etmez
            "kredi__ozel": [1.0, 1.0, 0.0, 0.0],    # sadece ilk kümede
            "etiket__diger": [0.0, 0.0, 1.0, 1.0],
        }
    )
    U = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]])
    profil = kume_profili(matris, U, 0, adet=3)
    assert profil.iloc[0]["ozellik"] == "ozel"


# --------------------------------------------------------------------------- #
# Ayar
# --------------------------------------------------------------------------- #

def test_ayar_yol_donusumu_ve_kopya():
    ayar = Ayar(matris="a/b.parquet", db="c/d.sqlite")
    assert isinstance(ayar.matris, Path) and isinstance(ayar.db, Path)
    yeni = ayar.ile(m=1.6)
    assert yeni.m == 1.6 and ayar.m == VARSAYILAN.m  # özgün nesne değişmedi


def test_varsayilan_m_k3_araliginda():
    assert 1.3 <= VARSAYILAN.m <= 1.6, "K3: m=2 kullanılmaz"


if __name__ == "__main__":
    basarisiz = 0
    for ad, islev in sorted(globals().items()):
        if not ad.startswith("test_") or not callable(islev):
            continue
        try:
            islev()
            print(f"ok   {ad}")
        except AssertionError as hata:
            basarisiz += 1
            print(f"HATA {ad}: {hata}")
        except Exception as hata:  # noqa: BLE001
            basarisiz += 1
            print(f"ÇÖKTÜ {ad}: {type(hata).__name__}: {hata}")
    print("—" * 40)
    print("tüm testler geçti" if not basarisiz else f"{basarisiz} test başarısız")
    raise SystemExit(1 if basarisiz else 0)
