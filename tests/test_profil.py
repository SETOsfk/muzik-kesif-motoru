"""Dinleyici profili testleri.

Bu ekran kullanıcıya "sen busun" diyor; yanlış söylememesi gerekiyor. Testler
özellikle iki şeyi koruyor: (1) uydurma norm üretilmemesi, (2) az veriyle
cümle kurulmaması.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from python.profil import (
    CAPALAR,
    EKSENLER,
    _capa_cumlesi,
    cesitlilik,
    eksen_ozeti,
    enstruman_dengesi,
    profil_cumleleri,
)

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


def _sahte(n=40, stem="drums", **sutunlar):
    rng = np.random.default_rng(0)
    temel = {
        "album_id": [f"a{i}" for i in range(n)],
        "stem": [stem] * n,
        "artist": [f"S{i}" for i in range(n)],
        "title": [f"T{i}" for i in range(n)],
        "year": [2000] * n,
        "enerji_payi": rng.uniform(0.02, 0.08, n),
        "onizleme_url": ["http://x"] * n,
    }
    temel.update(sutunlar)
    return pd.DataFrame(temel)


def test_az_veride_eksen_uretilmez():
    """10 albümden az ölçüm varsa o eksen hiç gösterilmemeli."""
    az = _sahte(n=5, zil_payi=[0.1, 0.2, 0.3, 0.4, 0.5],
                tekme_payi=[0.1] * 5, izgara_entropi=[0.9] * 5, tempo=[120] * 5)
    assert eksen_ozeti(az).empty, "5 albümle eksen özeti üretilmemeli"


def test_uclar_gercek_album_adi_tasir():
    n = 20
    zil = np.linspace(0.1, 0.7, n)
    veri = _sahte(n=n, zil_payi=zil, tekme_payi=[0.2] * n,
                  izgara_entropi=[0.95] * n, tempo=[120] * n)
    ozet = eksen_ozeti(veri)
    zil_satir = ozet[ozet["sutun"] == "zil_payi"].iloc[0]
    assert zil_satir["en_dusuk"] == "S0 — T0"
    assert zil_satir["en_yuksek"] == f"S{n-1} — T{n-1}"
    assert zil_satir["en_dusuk_deger"] < zil_satir["en_yuksek_deger"]


def test_capa_uydurmaz():
    """Çapası olmayan eksende konum cümlesi kurulmamalı."""
    assert _capa_cumlesi("tempo", "drums", 120.0) is None
    assert _capa_cumlesi("izgara_entropi", "drums", 0.5) is not None


def test_capa_uclari_dogru_tarafa_koyar():
    alt = _capa_cumlesi("zil_payi", "drums", 0.05)
    ust = _capa_cumlesi("zil_payi", "drums", 0.90)
    assert "TOOL" in alt, alt
    assert "Meshuggah" in ust, ust


def test_enstrumantal_kutuphane_tespiti():
    """Vokal kapsaması düşükse bu söylenmeli — gerçek bir dinleyici özelliği."""
    davul = _sahte(n=20, stem="drums", zil_payi=np.linspace(.1, .6, 20),
                   tekme_payi=[.2] * 20, izgara_entropi=[.95] * 20, tempo=[120] * 20)
    vokal = _sahte(n=5, stem="vocals", perde_medyan=[30.0] * 5,
                   perde_araligi=[10.0] * 5)
    vokal["album_id"] = [f"a{i}" for i in range(5)]
    veri = pd.concat([davul, vokal], ignore_index=True)
    denge = enstruman_dengesi(veri)
    cumleler = profil_cumleleri(eksen_ozeti(veri), denge)
    assert any("enstrümantal" in c for c in cumleler), cumleler


def test_capalar_eksen_tanimiyla_tutarli():
    """Çapası olan her (sütun, stem) çifti EKSENLER'de tanımlı olmalı."""
    tanimli = {(s, st) for s, st, *_ in EKSENLER}
    for anahtar in CAPALAR:
        assert anahtar in tanimli, f"{anahtar} çapası var ama ekseni tanımlı değil"


def test_cesitlilik_dar_ekseni_sona_koyar():
    n = 30
    veri = _sahte(n=n, zil_payi=np.linspace(0.05, 0.95, n),   # geniş
                  tekme_payi=np.linspace(0.20, 0.21, n),      # dar
                  izgara_entropi=[0.95] * n, tempo=[120] * n)
    c = cesitlilik(eksen_ozeti(veri)).set_index("eksen")["yayilim"]
    # Yalnız bu iki ekseni kıyasla: sahte veride sabit tutulan eksenlerin
    # yayılımı 0 ve doğal olarak en sonda — testin konusu o değil.
    assert c["zil ağırlığı"] > c["tekme ağırlığı"], c.to_dict()


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
