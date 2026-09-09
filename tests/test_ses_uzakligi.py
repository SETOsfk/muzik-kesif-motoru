"""Ses uzaklığı testleri.

Bu ölçüt `bilincli_uzaklik`'in mainstream'e düşme sorununu kırmak için var:
kalabalık grafiği "kim neyi dinliyor" diyor, bu "kulağa ne kadar farklı geliyor".
Yanlış çalışırsa sessizce yanlış çalışır — testler iki tuzağı kapatıyor.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from python.discover.ses_uzakligi import aday_uzakligi

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


def _olcek(stem="drums", **sapmalar):
    varsayilan = {"zil_payi": 0.1, "tekme_payi": 0.1, "izgara_entropi": 0.05}
    varsayilan.update(sapmalar)
    return {stem: pd.DataFrame({
        "medyan": {k: 0.0 for k in varsayilan},
        "sapma": varsayilan,
    })}


def _merkez(stem="drums", **degerler):
    return {stem: pd.Series(degerler)}


def _aday(stem="drums", **degerler):
    return pd.DataFrame([{"stem": stem, **degerler}])


def test_ayni_nokta_sifir_uzaklik():
    m = _merkez(zil_payi=0.4, tekme_payi=0.2)
    a = _aday(zil_payi=0.4, tekme_payi=0.2)
    uzaklik, boyut, _ = aday_uzakligi(a, m, _olcek())
    assert uzaklik == 0.0, uzaklik
    assert boyut == 2


def test_sapma_biriminde_olculuyor():
    """1 standart sapma fark = 1.0 uzaklık — birim kütüphane sigması."""
    m = _merkez(zil_payi=0.4)
    a = _aday(zil_payi=0.5)          # sapma 0.1 → tam 1 sigma
    uzaklik, boyut, _ = aday_uzakligi(a, m, _olcek(zil_payi=0.1))
    assert abs(uzaklik - 1.0) < 1e-9, uzaklik


def test_eksik_boyut_medyanla_DOLDURULMAZ():
    """Ölçülemeyen boyut atlanır; 'ortalama' sayılıp mesafeye katılmaz.

    Doldurmak enstrümantal bir albüme 'vokali ortalama' demek olurdu.
    """
    m = _merkez(zil_payi=0.4, tekme_payi=0.2)
    a = _aday(zil_payi=0.5, tekme_payi=np.nan)
    uzaklik, boyut, _ = aday_uzakligi(a, m, _olcek(zil_payi=0.1))
    assert boyut == 1, f"eksik boyut sayılmamalı, boyut={boyut}"
    assert abs(uzaklik - 1.0) < 1e-9, uzaklik


def test_boyut_sayisi_uzakligi_sismiyor():
    """Çok boyutta ölçülen aday, az boyutta ölçülenden otomatik uzak olmamalı.

    Ham Öklid kullanılsaydı 4 boyutta 1'er sigma sapma sqrt(4)=2.0 verirdi,
    1 boyutta 1.0 — yani kapsaması geniş aday haksız yere 'daha uzak' çıkardı.
    Kök ortalama kare ikisini de 1.0 yapıyor.
    """
    olcek = _olcek(a=1.0, b=1.0, c=1.0, d=1.0)
    m = _merkez(a=0.0, b=0.0, c=0.0, d=0.0)
    genis, bg, _ = aday_uzakligi(_aday(a=1.0, b=1.0, c=1.0, d=1.0), m, olcek)
    dar, bd, _ = aday_uzakligi(
        _aday(a=1.0, b=np.nan, c=np.nan, d=np.nan), m, olcek
    )
    assert bg == 4 and bd == 1
    assert abs(genis - dar) < 1e-9, f"geniş={genis} dar={dar} — eşit olmalı"


def test_stem_kirilimi_doner():
    olcek = {**_olcek("drums"), **_olcek("bass", perde_medyan=1.0)}
    m = {"drums": pd.Series({"zil_payi": 0.4}),
         "bass": pd.Series({"perde_medyan": 10.0})}
    a = pd.DataFrame([
        {"stem": "drums", "zil_payi": 0.5},
        {"stem": "bass", "perde_medyan": 12.0},
    ])
    uzaklik, boyut, kirilim = aday_uzakligi(a, m, olcek)
    assert set(kirilim) == {"drums", "bass"}
    assert abs(kirilim["drums"] - 1.0) < 1e-9
    assert abs(kirilim["bass"] - 2.0) < 1e-9
    assert boyut == 2


def test_olcum_yoksa_none():
    assert aday_uzakligi(pd.DataFrame(), _merkez(zil_payi=0.4), _olcek())[0] is None
    assert aday_uzakligi(_aday(zil_payi=0.5), {}, _olcek())[0] is None


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
