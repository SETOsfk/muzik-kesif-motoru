"""Öznitelik matrisi testleri. pandas gerektirir (.venv içinden çalıştırın).

    .venv/bin/python tests/test_matris.py
    .venv/bin/pytest tests/test_matris.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    print("pandas yok — .venv/bin/python ile çalıştırın")
    raise SystemExit(0)

from python.db import baglan
from python.enrich.matris_kur import (
    _l2_normalize,
    _seyrekleri_at,
    etiket_blogu,
    kredi_blogu,
    matris_kur,
    sahne_blogu,
    ses_blogu,
)


def _db():
    """İki albümü ortak davulcu, biri ayrık — kümelemenin göreceği asgari yapı."""
    conn = baglan(":memory:")
    with conn:
        conn.executemany(
            "INSERT INTO albums (album_id, artist, title, year, label, country) VALUES (?,?,?,?,?,?)",
            [
                ("a1", "Rush", "Moving Pictures", 1981, "Anthem", "CA"),
                ("a2", "Rush", "Hemispheres", 1978, "Anthem", "CA"),
                ("a3", "Şebnem Ferah", "Perdeler", 2005, "Universal", "TR"),
            ],
        )
        conn.executemany(
            "INSERT INTO credits (album_id, person_id, person_name, role, kaynak) VALUES (?,?,?,?,?)",
            [
                ("a1", "np", "Neil Peart", "drums", "musicbrainz"),
                ("a2", "np", "Neil Peart", "drums", "musicbrainz"),
                # Aynı kişi Discogs'ta farklı kimlik ve farklı yazımla:
                ("a1", "discogs:9", "neil peart", "percussion", "discogs"),
                ("a1", "gl", "Geddy Lee", "bass", "musicbrainz"),
                ("a3", "sf", "Şebnem Ferah", "vocals", "musicbrainz"),
            ],
        )
        conn.executemany(
            "INSERT INTO tags (album_id, tag, agirlik) VALUES (?,?,?)",
            [
                ("a1", "progressive rock", 0.7),
                ("a1", "hard rock", 0.3),
                ("a2", "progressive rock", 1.0),
                ("a3", "alternative rock", 1.0),
            ],
        )
    return conn


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #

def test_l2_normalize_satir_normu_bir():
    cerceve = pd.DataFrame({"a": [3.0, 0.0], "b": [4.0, 0.0]})
    sonuc = _l2_normalize(cerceve)
    assert abs(sonuc.loc[0, "a"] - 0.6) < 1e-9
    assert abs(sonuc.loc[0, "b"] - 0.8) < 1e-9
    # Tamamı sıfır olan satır sıfır kalır, sıfıra bölünmez.
    assert sonuc.loc[1].tolist() == [0.0, 0.0]


def test_seyrek_sutunlar_atilir():
    cerceve = pd.DataFrame({"sik": [1.0, 1.0, 0.0], "tek": [1.0, 0.0, 0.0]})
    assert list(_seyrekleri_at(cerceve, 2).columns) == ["sik"]
    assert list(_seyrekleri_at(cerceve, 1).columns) == ["sik", "tek"]


# --------------------------------------------------------------------------- #
# Bloklar
# --------------------------------------------------------------------------- #

def test_kredi_blogu_kisiyi_kaynaklar_arasinda_birlestirir():
    conn = _db()
    albumler = pd.Index(["a1", "a2", "a3"], name="album_id")
    blok = kredi_blogu(conn, albumler, min_album=1)
    # "Neil Peart" ve "neil peart" tek sütun olmalı.
    peart = [s for s in blok.columns if s.casefold() == "neil peart"]
    assert len(peart) == 1, blok.columns.tolist()
    assert blok.loc["a1", peart[0]] == 1.0
    assert blok.loc["a2", peart[0]] == 1.0
    assert blok.loc["a3", peart[0]] == 0.0


def test_kredi_blogu_esik_tek_albumluk_kisiyi_eler():
    conn = _db()
    albumler = pd.Index(["a1", "a2", "a3"], name="album_id")
    blok = kredi_blogu(conn, albumler, min_album=2)
    # Sadece iki albümde birden çalan Neil Peart kalır.
    assert [s.casefold() for s in blok.columns] == ["neil peart"]


def test_sahne_blogu_ulke_ve_donem():
    conn = _db()
    albumler = pd.Index(["a1", "a2", "a3"], name="album_id")
    blok = sahne_blogu(conn, albumler, min_album=1)
    sutunlar = set(blok.columns)
    assert {"ulke:CA", "ulke:TR", "donem:1980lar", "donem:1970lar"} <= sutunlar
    assert blok.loc["a1", "donem:1980lar"] == 1.0
    assert blok.loc["a2", "donem:1970lar"] == 1.0


def test_sahne_blogunda_label_yok():
    """K9 (kullanıcı kararı): plak şirketi müzikal yakınlık göstermez, matrise girmez."""
    conn = _db()
    blok = sahne_blogu(conn, pd.Index(["a1", "a2", "a3"], name="album_id"), min_album=1)
    assert not any(s.startswith("label:") for s in blok.columns), blok.columns.tolist()


def test_etiket_blogu_agirliklari_tasir():
    conn = _db()
    albumler = pd.Index(["a1", "a2", "a3"], name="album_id")
    blok = etiket_blogu(conn, albumler, min_album=1)
    assert blok.loc["a1", "progressive rock"] == 0.7
    assert blok.loc["a3", "progressive rock"] == 0.0


def test_ses_blogu_robust_z_ve_eksik_doldurma():
    conn = _db()
    with conn:
        conn.executemany(
            """INSERT INTO audio_features
               (album_id, tempo_medyan, tempo_iqr, dinamik_aralik,
                nabiz_netligi, vurus_degiskenligi, spektral_merkez)
               VALUES (?,?,?,?,?,?,?)""",
            [
                ("a1", 100.0, 5.0, 10.0, 8.0, 0.02, 2000.0),
                ("a2", 140.0, 7.0, 12.0, 4.0, 0.06, 2400.0),
            ],
        )
    albumler = pd.Index(["a1", "a2", "a3"], name="album_id")
    blok, eksik = ses_blogu(conn, albumler)
    assert eksik == 1                       # a3'ün ses özniteliği yok
    assert blok.loc["a3", "tempo_medyan"] == 0.0   # medyanda duruyor
    # İki gözlemde medyan ortada; simetrik olarak ±0.5 IQR'a düşerler.
    assert abs(blok.loc["a1", "tempo_medyan"] + blok.loc["a2", "tempo_medyan"]) < 1e-9
    assert blok.loc["a1", "tempo_medyan"] < 0 < blok.loc["a2", "tempo_medyan"]


def test_ses_blogu_sabit_sutun_sifirlanir():
    conn = _db()
    with conn:
        conn.executemany(
            """INSERT INTO audio_features
               (album_id, tempo_medyan, tempo_iqr, dinamik_aralik,
                nabiz_netligi, vurus_degiskenligi, spektral_merkez)
               VALUES (?,?,?,?,?,?,?)""",
            [("a1", 120.0, 5.0, 10.0, 8.0, 0.02, 2000.0), ("a2", 120.0, 5.0, 10.0, 8.0, 0.02, 2000.0)],
        )
    blok, _ = ses_blogu(conn, pd.Index(["a1", "a2", "a3"], name="album_id"))
    # IQR = 0 → bilgi yok → sütun sıfırlanır, NaN/sonsuz üretilmez.
    assert blok["tempo_medyan"].tolist() == [0.0, 0.0, 0.0]


# --------------------------------------------------------------------------- #
# Birleştirme
# --------------------------------------------------------------------------- #

def test_matris_bloklari_isimlendirir_ve_normalize_eder():
    conn = _db()
    matris, sozluk = matris_kur(conn, min_album=1)

    assert list(matris.index) == ["a1", "a2", "a3"]
    assert all("__" in sutun for sutun in matris.columns)
    assert set(sozluk["blok"]) == {"kredi", "sahne", "etiket"}  # ses boş

    for blok in ("kredi", "sahne", "etiket"):
        alt = matris[[s for s in matris.columns if s.startswith(f"{blok}__")]]
        normlar = ((alt**2).sum(axis=1) ** 0.5).round(9)
        assert set(normlar) == {1.0}, f"{blok}: {normlar.tolist()}"


def test_sozluk_kapsami_dogru_sayar():
    conn = _db()
    _, sozluk = matris_kur(conn, min_album=1)
    satir = sozluk[sozluk["ham_ad"] == "progressive rock"].iloc[0]
    assert satir["blok"] == "etiket"
    assert satir["kapsam"] == 2  # a1 ve a2


def test_bos_veritabani_anlasilir_hata():
    conn = baglan(":memory:")
    try:
        matris_kur(conn)
    except SystemExit as hata:
        assert "albums" in str(hata)
    else:
        raise AssertionError("boş albums tablosunda hata bekleniyordu")


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
