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


def test_spektral_gomme_bloklari_ayirir():
    from python.kumeleme.boyut_indirgeme import spektral_gomme
    # İki blok: içi benzer, arası benzemez.
    S = np.zeros((20, 20))
    S[:10, :10] = 0.9
    S[10:, 10:] = 0.9
    X = spektral_gomme(S, 2, komsu=5)
    a, b = X[:10].mean(axis=0), X[10:].mean(axis=0)
    assert np.linalg.norm(a - b) > 1.0                      # birim çember üstünde uzak
    assert np.allclose(np.linalg.norm(X, axis=1), 1.0)


def test_ortak_atama_tutarli_ciftleri_bir_yapar():
    a1 = np.array([0, 0, 1, 1])
    a2 = np.array([1, 1, 0, 0])                             # etiket değişse de aynı bölme
    a3 = np.array([0, 1, 1, 1])
    C = arama.ortak_atama([a1, a2, a3])
    assert C[0, 1] == 2 / 3 and C[2, 3] == 1.0 and C[0, 3] == 0.0


def test_uc_yontem_de_yarisir_ve_uzay_saklanir():
    X, _ = _yapili_matris()
    uzaylar = {}
    # Konsensüs c başına ≥ 3 pca koşusu ister: 2 boyut × 2 m = 4.
    adaylar, secilen = arama.ara(X, VARSAYILAN.ile(c_araligi=(2, 4)), bilesenler=(3, 5),
                                 m_degerleri=(1.3, 1.4), yaz=lambda *a: None, uzaylar=uzaylar)
    assert {a.yontem for a in adaylar} == {"pca", "spektral", "konsensus"}
    assert secilen.c == 3 and secilen.uzay in uzaylar


def test_goreli_tolerans_kaba_bolmeyi_esit_saymaz():
    """Siluetler küçükken mutlak tolerans kaba bölmeyi «eşit iyi» sayıyordu."""
    A = arama.Aday
    adaylar = [A(8, 1.4, 6, 0.071, 0.1, 1, 0.8, 30, gecerli=True),
               A(5, 1.6, 9, 0.055, 0.1, 1, 0.8, 12, gecerli=True)]
    assert arama.sec(adaylar).c == 6


def test_secileni_yaz_yeni_calisma_kurar(tmp_path, monkeypatch):
    import python.db as D

    monkeypatch.setattr(D, "KULLANICI_KOK", tmp_path / "kullanici")
    monkeypatch.setattr(D, "VARSAYILAN_ORTAK", tmp_path / "ortak.sqlite")
    X, _ = _yapili_matris()
    db = D.kullanici_db(1)
    conn = D.baglan_kullanici(1)
    with conn:
        for a in X.index:
            conn.execute("INSERT INTO albums (album_id, artist, title) VALUES (?,?,?)", (a, a, a))
    conn.close()
    uzaylar = {}
    _, secilen = arama.ara(X, VARSAYILAN.ile(c_araligi=(2, 4)), bilesenler=(3,),
                           m_degerleri=(1.4,), yontemler=("spektral",), yaz=lambda *a: None,
                           uzaylar=uzaylar)
    calisma = arama.secileni_yaz(db, X, secilen, uzaylar[secilen.uzay],
                                 VARSAYILAN.ile(bootstrap=5))
    conn = D.baglan_kullanici(1)
    try:
        assert "spektral" in calisma
        assert conn.execute("SELECT COUNT(*) FROM clusters WHERE calisma_id = ?", (calisma,)).fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM memberships WHERE calisma_id = ?", (calisma,)).fetchone()[0] == 3 * len(X)
    finally:
        conn.close()
