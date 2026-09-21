"""Yeniden kümelemede ad ve karar taşıma (`python/kumeleme/tasi.py`)."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def _yollari_geri_al():
    import python.db as D

    eski = (D.KULLANICI_KOK, D.VARSAYILAN_ORTAK)
    yield
    D.KULLANICI_KOK, D.VARSAYILAN_ORTAK = eski


def _kur(conn, calisma, atama: dict[str, int], adlar: dict[int, str] | None = None):
    kumeler = sorted(set(atama.values()))
    with conn:
        for k in kumeler:
            conn.execute("INSERT INTO clusters (kume_id, calisma_id, kullanici_adi, "
                         "stabilite, stabil_mi) VALUES (?,?,?,0.9,1)",
                         (k, calisma, (adlar or {}).get(k)))
        for album, k in atama.items():
            for j in kumeler:
                conn.execute("INSERT INTO memberships (album_id, kume_id, uyelik, "
                             "calisma_id) VALUES (?,?,?,?)",
                             (album, j, 0.9 if j == k else 0.1 / len(kumeler), calisma))


def test_kume_numarasi_degisse_de_ad_dogru_kumeye_gider():
    import python.db as D
    from python.kumeleme.tasi import tasi

    with tempfile.TemporaryDirectory() as tmp:
        D.KULLANICI_KOK = Path(tmp) / "k"
        D.VARSAYILAN_ORTAK = Path(tmp) / "o.sqlite"
        conn = D.baglan_kullanici(1)
        metal = [f"m{i}" for i in range(10)]
        caz = [f"c{i}" for i in range(10)]
        diger = [f"d{i}" for i in range(10)]
        # Eski: 0 = metal, 1 = caz, 2 = diğer (adsız)
        _kur(conn, "eski", {**{a: 0 for a in metal}, **{a: 1 for a in caz},
                            **{a: 2 for a in diger}}, {0: "metal", 1: "caz"})
        # Yeni: numaralar karışık; caz kümesinin yalnız 4/10'u aynı yerde kaldı.
        _kur(conn, "yeni", {**{a: 2 for a in metal}, **{a: 0 for a in caz[:4]},
                            **{a: 1 for a in caz[4:] + diger}})
        with conn:
            conn.execute("INSERT INTO feedback (aday_id, eksen, karar, tarih, calisma_id) "
                         "VALUES ('x', 0, 'begendim', '2026-09-21', 'eski')")

        rapor = tasi(conn, "eski", "yeni")
        adlar = dict(conn.execute(
            "SELECT kume_id, kullanici_adi FROM clusters WHERE calisma_id='yeni'").fetchall())
        assert adlar[2] == "metal", adlar
        # caz ↔ yeni 0: Jaccard 0,4 < 0,5 → ad taşınmaz, raporlanır.
        assert "caz" not in adlar.values(), adlar
        assert [r[0] for r in rapor["tasinmayan_ad"]] == ["caz"]
        # Karar taşındı, ekseni yeni «metal» kümesi.
        k = conn.execute("SELECT eksen, karar FROM feedback WHERE calisma_id='yeni'").fetchone()
        assert tuple(k) == (2, "begendim"), tuple(k)
        # İkinci çalıştırma çift kayıt yapmaz.
        assert not tasi(conn, "eski", "yeni")["karar"]
        conn.close()
