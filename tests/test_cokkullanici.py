"""Çok kiracılık testleri — iki veritabanı, tek görünüm.

Mimarinin dayandığı varsayım şu: NİTELİKSİZ bir tablo adı SQLite tarafından
önce `main`de, bulunamazsa ATTACH edilmiş veritabanında aranır. Bu sayede
kütüphaneyi okuyan 145 ve paylaşımlı tabloları okuyan 117 sorgu yeri HİÇ
DEĞİŞMEDEN çalışıyor.

Varsayım sessizce bozulursa (bir tablo yanlışlıkla iki tarafta da oluşursa,
ya da sınıflandırma kayarsa) sorgular patlamaz — YANLIŞ VERİYİ okur. Bir
kullanıcının kütüphanesi başkasınınkine karışır ve bunu kimse fark etmez.
Testler o yüzden ayrımın kendisini koruyor.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


def _ortam(tmp):
    """İki kullanıcı, paylaşımlı bir ortak veritabanı."""
    import python.db as D

    kok = Path(tmp)
    D.KULLANICI_KOK = kok / "kullanici"
    D.VARSAYILAN_ORTAK = kok / "ortak.sqlite"
    return D


def test_tablo_tam_bir_tarafta():
    """Bir tablo iki tarafta birden olursa hangisinin okunduğu belirsizleşir."""
    from python.db import ORTAK_TABLOLAR, SEMA, _tablo_adi

    kullanici = {_tablo_adi(d) for d in SEMA if _tablo_adi(d) not in ORTAK_TABLOLAR}
    kullanici.discard(None)
    cakisma = kullanici & ORTAK_TABLOLAR
    assert not cakisma, f"iki tarafta birden: {cakisma}"

    # Her DDL sınıflandırılabilmeli; sınıflandırılamayan iki tarafa da yazılır.
    assert not [d.strip()[:50] for d in SEMA if _tablo_adi(d) is None]


def test_paylasimli_tabloda_albums_fk_kalmaz():
    """Veritabanları arası FK sessizce yok sayılmıyor, PATLIYOR.

    Ölçüldü: `ortak.credits`e yazarken SQLite `ortak.albums` arıyor ve
    "no such table" veriyor. Bu yüzden paylaşımlı DDL'lerden `REFERENCES
    albums(...)` sökülmek zorunda.
    """
    from python.db import _sema_bolumu

    for ddl in _sema_bolumu(ortak=True):
        assert "REFERENCES albums" not in ddl, ddl.strip()[:70]


def test_niteliksiz_sorgu_iki_veritabanini_da_gorur():
    """Mimarinin tamamı buna dayanıyor: sorgular değişmeden çalışmalı."""
    with tempfile.TemporaryDirectory() as tmp:
        D = _ortam(tmp)
        conn = D.baglan_kullanici(1)
        with conn:
            conn.execute("INSERT INTO albums (album_id, artist, title) "
                         "VALUES ('a1','Rush','Hemispheres')")
            conn.execute("INSERT INTO credits (album_id, person_name, role, kaynak) "
                         "VALUES ('a1','Neil Peart','drums','test')")
        # albums main'de, credits ortak'ta — ikisi de niteliksiz okunuyor
        assert conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM credits").fetchone()[0] == 1
        # ve aralarında JOIN yapılabiliyor
        satir = conn.execute(
            "SELECT a.artist, c.person_name FROM albums a "
            "JOIN credits c USING(album_id)").fetchone()
        assert tuple(satir) == ("Rush", "Neil Peart"), tuple(satir)


def test_kutuphaneler_ayri_havuz_ortak():
    """İki kullanıcının kütüphanesi karışmamalı, havuzu paylaşılmalı.

    Bu testin koruduğu şey ürünün tamamı: kullanıcı A'nın albümü B'nin
    kütüphanesinde görünürse öneriler ve «sende olmayan» süzgeci bozulur.
    """
    with tempfile.TemporaryDirectory() as tmp:
        D = _ortam(tmp)
        a = D.baglan_kullanici(1)
        with a:
            a.execute("INSERT INTO albums (album_id, artist, title) "
                      "VALUES ('a1','Rush','Hemispheres')")
            a.execute("INSERT INTO calma_listesi (liste_id, baslik) VALUES (1,'havuz')")
        a.close()

        b = D.baglan_kullanici(2)
        with b:
            b.execute("INSERT INTO albums (album_id, artist, title) "
                      "VALUES ('b1','Casiopea','Mint Jams')")

        # kütüphaneler AYRI
        assert [r[0] for r in b.execute("SELECT artist FROM albums")] == ["Casiopea"]
        # havuz ORTAK — 1 numaralı kullanıcının yazdığı listeyi 2 de görüyor
        assert b.execute("SELECT COUNT(*) FROM calma_listesi").fetchone()[0] == 1
        b.close()

        a2 = D.baglan_kullanici(1)
        assert [r[0] for r in a2.execute("SELECT artist FROM albums")] == ["Rush"]


def test_hesap_tablosu_paylasimli():
    """Hesaplar ortakta olmalı; kullanıcı dosyasında olsa giriş yapılamazdı."""
    from python.db import ORTAK_TABLOLAR

    assert "kullanici" in ORTAK_TABLOLAR
    assert "oturum" in ORTAK_TABLOLAR


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
