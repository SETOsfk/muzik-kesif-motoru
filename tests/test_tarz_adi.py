"""Otomatik tarz adı — ilgili olmalı, kullanıcının adına dokunmamalı."""

import pytest

import python.db as D
from python.tarz_adi import ad_onerileri, bos_olanlari_adlandir


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "KULLANICI_KOK", tmp_path / "kullanici")
    monkeypatch.setattr(D, "VARSAYILAN_ORTAK", tmp_path / "ortak.sqlite")
    c = D.baglan_kullanici(1)
    yield c
    c.close()


def _kur(conn, albumler, etiketli=True):
    """albumler: [(sanatçı, küme, [etiketler])]"""
    with conn:
        for k in {k for _, k, _ in albumler}:
            conn.execute("INSERT INTO clusters (kume_id, calisma_id, stabil_mi) VALUES (?, 'c', 1)", (k,))
        for i, (s, k, tags) in enumerate(albumler):
            conn.execute("INSERT INTO albums (album_id, artist, title) VALUES (?,?,?)", (f"a{i}", s, f"T{i}"))
            for kk in (0, 1):
                conn.execute("INSERT INTO memberships VALUES (?,?,?,'c')",
                             (f"a{i}", kk, 0.9 - i * 0.01 if kk == k else 0.1))
            for tag in (tags if etiketli else []):
                conn.execute("INSERT INTO tags VALUES (?,?,1)", (f"a{i}", tag))


def test_ayirt_eden_etiket_secilir_her_yerde_olan_degil(conn):
    _kur(conn, [("Gojira", 0, ["rock", "progressive metal"])] * 4
         + [("Duman", 1, ["rock", "turkish rock"])] * 4)
    oneri = ad_onerileri(conn, "c")
    assert oneri == {0: "progressive metal", 1: "turkish rock"}   # "rock" değil


def test_etiket_yoksa_merkezdeki_sanatcilar(conn):
    _kur(conn, [("Casiopea", 0, []), ("Plini", 0, []), ("Casiopea", 0, []),
                ("Tool", 1, []), ("Tool", 1, [])], etiketli=False)
    assert ad_onerileri(conn, "c")[0] == "Casiopea · Plini tarzı"


def test_kullanicinin_adina_dokunulmaz(conn):
    _kur(conn, [("Gojira", 0, ["progressive metal"])] * 3 + [("Duman", 1, ["turkish rock"])] * 3)
    with conn:
        conn.execute("UPDATE clusters SET kullanici_adi = 'benim metalim' WHERE kume_id = 0")
    assert bos_olanlari_adlandir(conn, "c") == 1
    adlar = dict(conn.execute("SELECT kume_id, kullanici_adi FROM clusters"))
    assert adlar == {0: "benim metalim", 1: "turkish rock"}
