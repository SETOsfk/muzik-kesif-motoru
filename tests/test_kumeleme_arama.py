"""Kümeleme araması: bilinen yapıyı bulur, ölçütler doğru yönde."""

import numpy as np
import pandas as pd

from python.kumeleme import arama
from python.kumeleme.ayar import VARSAYILAN


def _yapili_matris(k=3, her=25, boyut=20, tohum=1):
    rng = np.random.default_rng(tohum)
    merkezler = rng.normal(0, 4, (k, boyut))
    X = np.vstack([merkezler[i] + rng.normal(0, 0.6, (her, boyut)) for i in range(k)])
    df = pd.DataFrame(X, columns=[f"kredi__{i}" for i in range(boyut)],
                      index=pd.Index([f"a{i}" for i in range(len(X))], name="album_id"))
    return df, np.repeat(np.arange(k), her)


def test_bulanik_siluet_net_yapida_yuksek_karisikta_dusuk():
    X, gercek = _yapili_matris()
    D = arama.kosinus_mesafe(X.to_numpy())
    U = np.eye(3)[gercek] * 0.8 + 0.2 / 3
    assert arama.bulanik_siluet(D, U) > 0.5
    karisik = np.eye(3)[np.random.default_rng(0).integers(0, 3, len(gercek))] * 0.8 + 0.2 / 3
    assert arama.bulanik_siluet(D, karisik) < 0.1


def test_arama_bilinen_uc_kumeyi_secer():
    X, _ = _yapili_matris()
    ayar = VARSAYILAN.ile(c_araligi=(2, 5))
    adaylar, secilen = arama.ara(X, ayar, bilesenler=(3, 5), m_degerleri=(1.4,), yaz=lambda *a: None)
    assert secilen is not None and secilen.c == 3 and secilen.secildi
    assert any(a.gecerli for a in adaylar)


def test_kalabalik_uyumu_rastgeleden_iyi():
    atama = np.array([0, 0, 1, 1])
    sanatci = ["a", "b", "c", "d"]
    ciftler = {("a", "b"), ("c", "d")} | {(f"x{i}", f"y{i}") for i in range(10)}
    # Geçerli çift 2 < asgari → None
    assert arama.kalabalik_uyumu(atama, sanatci, ciftler) is None
    assert arama.kalabalik_uyumu(atama, sanatci, {("a", "b"), ("c", "d")}, asgari_cift=2) == 2.0


def test_secim_kurali_esit_iyiler_arasinda_kalabaligi_tercih_eder():
    A = arama.Aday
    adaylar = [A(8, 1.4, 4, 0.30, 0.1, 1, 0.8, 20, kalabalik=1.2, gecerli=True),
               A(6, 1.5, 6, 0.29, 0.1, 1, 0.8, 12, kalabalik=1.6, gecerli=True),
               A(5, 1.3, 9, 0.20, 0.1, 1, 0.8, 8, kalabalik=2.0, gecerli=True),
               A(5, 1.3, 12, 0.40, 0.1, 0.8, 0.4, 3, gecerli=False)]
    assert arama.sec(adaylar).c == 6     # 0,29 toleransta; 0,20 değil; geçersiz sayılmaz


def test_rapor_secileni_yazar():
    A = arama.Aday
    a = A(8, 1.4, 5, 0.3, 0.1, 1, 0.8, 20, gecerli=True, secildi=True)
    metin = arama.rapor([a], a, 100)
    assert "**seçildi**" in metin and "degerlendirme" in metin
