"""Alım katmanı testleri — OKUBENI.md'deki 2. öncelik (artımlı alım) merkezde.

pytest ile ya da doğrudan çalıştırılabilir:
    pytest tests/test_alim.py
    python tests/test_alim.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.db import baglan
from python.ingest.dinleme_logu import AlbumIndeksi, Dinleme, iceri_aktar, tarih_coz
from python.ingest.kutuphane_tara import Parca, tara
from python.metin import album_kimligi, normalize


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #

def sahte_okuyucu(harita: dict[str, tuple[str, str, int | None]]):
    """Dosya adına göre etiket üreten okuyucu — mutagen'e gerek kalmasın."""

    def oku(yol: Path, st: os.stat_result) -> Parca | None:
        kayit = harita.get(yol.name)
        if kayit is None:
            return None
        artist, album, yil = kayit
        return Parca(
            yol=yol, mtime=st.st_mtime, boyut=st.st_size,
            artist=artist, album=album, yil=yil, label=None,
        )

    return oku


def dosya_yaz(yol: Path, icerik: str = "x") -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(icerik)


# --------------------------------------------------------------------------- #
# 1. Normalizasyon ve kimlik
# --------------------------------------------------------------------------- #

def test_normalize_gurultuyu_atar():
    assert normalize("Meddle (2011 Remaster)") == "meddle"
    assert normalize("Aja - 2011 Remaster") == "aja"
    assert normalize("The Yes Album") == "yes album"
    # Anlamlı parantez korunur.
    assert normalize("III (Wisdom)") == "iii wisdom"


def test_normalize_turkce_harfler():
    assert normalize("Şebnem Ferah") == "sebnem ferah"
    assert normalize("Yüksek Sadakat") == "yuksek sadakat"
    assert normalize("MOR VE ÖTESİ") == "mor ve otesi"


def test_album_kimligi_kararli():
    a = album_kimligi("Pink Floyd", "Meddle (2011 Remaster)", 1971)
    b = album_kimligi("pink floyd", "Meddle", 1971)
    assert a == b
    assert a != album_kimligi("Pink Floyd", "Animals", 1977)


def test_tarih_coz():
    assert tarih_coz(1620000000, "2026-01-01") == ("2021-05-03", False)
    assert tarih_coz("05 Jan 2021 20:41", "2026-01-01") == ("2021-01-05", False)
    assert tarih_coz("2021-01-05T20:41:00Z", "2026-01-01") == ("2021-01-05", False)
    assert tarih_coz("", "2026-01-01") == ("2026-01-01", True)


# --------------------------------------------------------------------------- #
# 2. Artımlı alım
# --------------------------------------------------------------------------- #

def test_artimli_alim():
    harita = {
        "01.flac": ("Pink Floyd", "Meddle", 1971),
        "02.flac": ("Pink Floyd", "Meddle", 1971),
        "03.flac": ("Rush", "Moving Pictures", 1981),
    }
    okuyucu = sahte_okuyucu(harita)

    with tempfile.TemporaryDirectory() as gecici:
        kok = Path(gecici) / "muzik"
        dosya_yaz(kok / "Pink Floyd" / "Meddle" / "01.flac")
        dosya_yaz(kok / "Pink Floyd" / "Meddle" / "02.flac")
        dosya_yaz(kok / "Rush" / "Moving Pictures" / "03.flac")
        conn = baglan(":memory:")

        # İlk tarama: her şey yeni.
        ilk = tara(conn, kok, okuyucu=okuyucu)
        assert ilk.taranan == 3
        assert ilk.okunan == 3
        assert ilk.atlanan == 0
        assert ilk.yeni_album == 2

        meddle = album_kimligi("Pink Floyd", "Meddle", 1971)
        satir = conn.execute(
            "SELECT track_count, path FROM albums WHERE album_id = ?", (meddle,)
        ).fetchone()
        assert satir["track_count"] == 2
        assert satir["path"].endswith("Meddle")

        # İkinci tarama: hiçbir dosya değişmedi → hepsi atlanır (OKUBENI #2).
        ikinci = tara(conn, kok, okuyucu=okuyucu)
        assert ikinci.atlanan == 3
        assert ikinci.okunan == 0
        assert ikinci.yeni_album == 0

        # --yeniden bayrağı atlamayı kapatır.
        zorla = tara(conn, kok, okuyucu=okuyucu, yeniden=True)
        assert zorla.atlanan == 0
        assert zorla.okunan == 3

        # Tek dosya değişti → sadece o okunur.
        degisen_yol = kok / "Rush" / "Moving Pictures" / "03.flac"
        dosya_yaz(degisen_yol, "değişti")
        os.utime(degisen_yol, (0, 0))
        ucuncu = tara(conn, kok, okuyucu=okuyucu)
        assert ucuncu.okunan == 1
        assert ucuncu.atlanan == 2

        # Dosya silindi → track_count düşer, albüm kaydı silinmez.
        (kok / "Pink Floyd" / "Meddle" / "02.flac").unlink()
        dorduncu = tara(conn, kok, okuyucu=okuyucu)
        assert dorduncu.silinen == 1
        assert conn.execute(
            "SELECT track_count FROM albums WHERE album_id = ?", (meddle,)
        ).fetchone()["track_count"] == 1
        assert conn.execute("SELECT COUNT(*) FROM dosyalar").fetchone()[0] == 2


def test_zenginlestirme_verisi_korunur():
    """Tarama, mbid/country gibi zenginleştirme alanlarını ezmemeli."""
    harita = {"01.flac": ("Rush", "Hemispheres", 1978)}
    with tempfile.TemporaryDirectory() as gecici:
        kok = Path(gecici) / "muzik"
        dosya_yaz(kok / "01.flac")
        conn = baglan(":memory:")
        tara(conn, kok, okuyucu=sahte_okuyucu(harita))

        album_id = album_kimligi("Rush", "Hemispheres", 1978)
        with conn:
            conn.execute(
                "UPDATE albums SET mbid = ?, country = ? WHERE album_id = ?",
                ("abc-123", "CA", album_id),
            )
        tara(conn, kok, okuyucu=sahte_okuyucu(harita), yeniden=True)
        satir = conn.execute(
            "SELECT mbid, country FROM albums WHERE album_id = ?", (album_id,)
        ).fetchone()
        assert satir["mbid"] == "abc-123"
        assert satir["country"] == "CA"


def test_etiketsiz_dosya_raporlanir():
    with tempfile.TemporaryDirectory() as gecici:
        kok = Path(gecici) / "muzik"
        dosya_yaz(kok / "01.flac")
        dosya_yaz(kok / "bozuk.flac")
        conn = baglan(":memory:")
        ozet = tara(conn, kok, okuyucu=sahte_okuyucu({"01.flac": ("Rush", "2112", 1976)}))
        assert len(ozet.etiketsiz) == 1
        assert ozet.etiketsiz[0].name == "bozuk.flac"


# --------------------------------------------------------------------------- #
# 3. Dinleme logu eşleştirmesi
# --------------------------------------------------------------------------- #

def _kutuphaneli_db():
    conn = baglan(":memory:")
    with conn:
        for album_id, artist, title in (
            ("a1", "Pink Floyd", "Meddle"),
            ("a2", "Rush", "Moving Pictures"),
            ("a3", "Şebnem Ferah", "Perdeler"),
        ):
            conn.execute(
                "INSERT INTO albums (album_id, artist, title) VALUES (?, ?, ?)",
                (album_id, artist, title),
            )
    return conn


def test_bulanik_album_eslesmesi():
    indeks = AlbumIndeksi(_kutuphaneli_db().execute("SELECT album_id, artist, title FROM albums"))
    assert indeks.bul("Pink Floyd", "Meddle")[0] == "a1"
    assert indeks.bul("pink floyd", "Meddle (2011 Remaster)")[0] == "a1"
    assert indeks.bul("Rush", "Moving Picutres")[0] == "a2"  # yazım hatası
    assert indeks.bul("Sebnem Ferah", "Perdeler")[0] == "a3"  # aksansız
    assert indeks.bul("Miles Davis", "Kind of Blue")[0] is None


def test_iceri_aktarim_idempotent():
    conn = _kutuphaneli_db()
    satirlar = [
        Dinleme("Pink Floyd", "Meddle", "Echoes", "2026-08-01"),
        Dinleme("Pink Floyd", "Meddle (Remastered)", "Echoes", "2026-08-01"),
        Dinleme("Rush", "Moving Pictures", "YYZ", "2026-08-02"),
        Dinleme("Miles Davis", "Kind of Blue", "So What", "2026-08-02"),
    ]
    ozet = iceri_aktar(conn, satirlar, "lastfm")
    assert ozet.eslesen == 3
    assert len(ozet.eslesmeyen) == 1

    toplam = conn.execute("SELECT SUM(adet) FROM plays").fetchone()[0]
    assert toplam == 3  # Echoes iki kez → aynı gün 2 adet

    # Aynı dosyayı tekrar aktarmak sayıları şişirmemeli.
    iceri_aktar(conn, satirlar, "lastfm")
    assert conn.execute("SELECT SUM(adet) FROM plays").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 2

    # Farklı kaynak aynı günü kapsasa bile ayrı satırda durur.
    iceri_aktar(conn, satirlar, "listenbrainz")
    assert conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 4


def test_kuru_calisma_yazmaz():
    conn = _kutuphaneli_db()
    ozet = iceri_aktar(
        conn, [Dinleme("Rush", "Moving Pictures", "YYZ", "2026-08-02")], "lastfm", kuru=True
    )
    assert ozet.eslesen == 1
    assert conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0] == 0


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
        except Exception as hata:  # noqa: BLE001 — test koşucusu
            basarisiz += 1
            print(f"ÇÖKTÜ {ad}: {type(hata).__name__}: {hata}")
    print("—" * 40)
    print("tüm testler geçti" if not basarisiz else f"{basarisiz} test başarısız")
    raise SystemExit(1 if basarisiz else 0)
