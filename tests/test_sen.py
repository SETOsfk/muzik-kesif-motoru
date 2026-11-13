"""«Sen» portresi — dayanağı olmayan cümle kurulmaz."""

import sqlite3

import pytest

import python.db as D
from python import sen


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "KULLANICI_KOK", tmp_path / "kullanici")
    monkeypatch.setattr(D, "VARSAYILAN_ORTAK", tmp_path / "ortak.sqlite")
    c = D.baglan_kullanici(1)
    yield c
    c.close()


def _albumler(conn, kayitlar, calisma="c1"):
    with conn:
        for i, (sanatci, yil, kume, tag) in enumerate(kayitlar):
            aid = f"a{i}"
            conn.execute("INSERT INTO albums (album_id, artist, title, year) VALUES (?,?,?,?)",
                         (aid, sanatci, f"T{i}", yil))
            for k in (0, 1):
                conn.execute("INSERT INTO memberships VALUES (?,?,?,?)",
                             (aid, k, 0.9 if k == kume else 0.1, calisma))
            if tag:
                conn.execute("INSERT INTO tags VALUES (?,?,1)", (aid, tag))


def test_onyil_eki_okunusa_gore():
    assert sen.onyil_adi(1990) == "1990'lar"
    assert sen.onyil_adi(1980) == "1980'ler"
    assert sen.onyil_adi(2010) == "2010'lar"
    assert sen.onyil_adi(2000) == "2000'ler"


def test_eksen_adi_yoksa_merkezdeki_sanatcilar(conn):
    _albumler(conn, [("Casiopea", 1982, 0, None)] * 3 + [("Tool", 2001, 1, None)] * 4)
    p = sen.portre(conn, "c1")
    assert [e["album"] for e in p["eksenler"]] == [4, 3]
    assert sen.eksen_adi(p["eksenler"][1]) == "Casiopea gibi"


def test_tur_kapsamasi_azsa_turden_soz_edilmez(conn):
    """Etiketsiz kütüphanede (liste/Spotify) tür cümlesi kurulmaz — sesten
    tür tahmini ölçüldü ve çöktü, yerine konmaz."""
    _albumler(conn, [("A", 2001, 0, None)] * 8 + [("B", 2002, 1, "metal")] * 2)
    p = sen.portre(conn, "c1")
    assert p["turler"] == []
    assert "tür" not in sen.ozet_cumlesi(p)


def test_yil_yoksa_donem_cumlesi_yok(conn):
    _albumler(conn, [("A", None, 0, None)] * 5)
    p = sen.portre(conn, "c1")
    assert p["donem"] is None and "kalbin" not in sen.ozet_cumlesi(p)


def test_evren_ucu_boyut_ve_tekrarlanabilir(conn):
    """Dört ayrık tarz: aynı tarzın albümleri yakın, farklı tarzlar uzak;
    aynı veri aynı haritayı verir; az tarzda harita kurulmaz."""
    with conn:
        for i in range(12):
            conn.execute("INSERT INTO albums (album_id, artist, title) VALUES (?,?,?)", (f"e{i}", f"S{i}", "T"))
            for k in range(4):
                conn.execute("INSERT INTO memberships VALUES (?,?,?,?)",
                             (f"e{i}", k, 0.85 if k == i % 4 else 0.05, "c4"))
    eksenler = sen._eksenler(conn, "c4")
    e = sen.evren(conn, "c4", eksenler)
    assert e == sen.evren(conn, "c4", eksenler)
    assert len(e["noktalar"]) == 12 and e["aciklanan"] == pytest.approx(1.0)
    assert all(-1 <= v <= 1 for n in e["noktalar"] for v in n[:3])
    uzak = lambda a, b: sum((p - q) ** 2 for p, q in zip(a[:3], b[:3])) ** .5
    n = {x[4]: x for x in e["noktalar"]}
    assert uzak(n["S0 — T"], n["S4 — T"]) < 1e-6 < uzak(n["S0 — T"], n["S1 — T"])
    assert {x[3] for x in n.values()} == {0, 1, 2, 3}
    assert sen.evren(conn, "yok", []) is None
