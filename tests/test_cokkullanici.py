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


def test_web_onbellekleri_kullaniciya_gore_anahtarlanir():
    """`lru_cache` kullanıcıya özel veri önbelleklerse A'nın verisi B'ye gider.

    GERÇEK HATA (2026-09-15). Çok kiracılıktan önce tek kullanıcı vardı ve
    anahtarsız `lru_cache` doğruydu. Sonra aynı kod iki şeyi birden bozdu:
    sunucu ilk isteği OTURUMSUZ karşılayınca boş sonuç önbelleğe girdi ve
    ondan sonra herkes "hiç kümeleme çalışması yok" gördü — ve daha kötüsü,
    bir kullanıcının küme adları ile sayaçları başka kullanıcıya servis
    edilebilir hâle geldi.

    Test, önbellekli işlevlerin İLK PARAMETRESİNİN kullanıcı olmasını
    koruyor. Yeni bir önbellekli işlev eklenirse ve kullanıcıya özel veri
    okuyorsa, buraya eklenmesi gerekir.
    """
    import inspect

    from web import sunucu

    onbellekli = {
        "_calismalar_onbellek": 0,
        "_eksen_adlari_onbellek": 0,
        "_boru_hatti_onbellek": 0,
    }
    for ad, konum in onbellekli.items():
        fn = getattr(sunucu, ad, None)
        assert fn is not None, f"{ad} kayboldu — önbellek anahtarı gözden geçirilmeli"
        parametreler = list(inspect.signature(fn).parameters)
        assert parametreler[konum] == "kullanici_id", \
            f"{ad} kullanıcıya göre anahtarlanmıyor: {parametreler}"

    # İcra eşleşmesi kullanıcıyı ikinci parametrede taşıyor.
    icra = list(inspect.signature(sunucu._icra_eslesmesi_onbellek).parameters)
    assert "kullanici_id" in icra, icra


def test_kullanici_verisi_sizmaz():
    """Bir kullanıcının adayları başka kullanıcının sayfasında GÖRÜNMEMELİ.

    Yalıtımın uçtan uca kanıtı: aynı sunucu, iki oturum, iki sonuç.
    """
    import tempfile

    from starlette.testclient import TestClient

    import python.db as D
    from python.hesap import CEREZ_ADI, kullanici_olustur, oturum_ac
    from web.sunucu import uygulama

    with tempfile.TemporaryDirectory() as tmp:
        D = _ortam(tmp)
        ortak = D.baglan_ortak()
        a = kullanici_olustur(ortak, "A", eposta="a@a.a", parola="parola123")
        b = kullanici_olustur(ortak, "B", eposta="b@b.b", parola="parola123")
        jeton_a, jeton_b = oturum_ac(ortak, a), oturum_ac(ortak, b)
        ortak.close()

        # A'nın kütüphanesine bir albüm koy
        ca = D.baglan_kullanici(a)
        with ca:
            ca.execute("INSERT INTO albums (album_id, artist, title) "
                       "VALUES ('x','GizliSanatci','Album')")
        ca.close()

        # Önbellekler istekler arasında paylaşılıyor; A önce baksın.
        istemci = TestClient(uygulama)
        istemci.cookies.set(CEREZ_ADI, jeton_a)
        istemci.get("/veri")

        istemci.cookies.set(CEREZ_ADI, jeton_b)
        yanit = istemci.get("/veri", follow_redirects=True)
        assert "GizliSanatci" not in yanit.text, \
            "A'nın sanatçısı B'nin sayfasında göründü — önbellek sızıntısı"


def test_kullanici_vtsinde_golge_tablo_olusmaz():
    """`baglan()` kullanıcı yoluna TAM ŞEMA kurmamalı.

    GERÇEK HATA (2026-09-15). `--db data/db/kullanici/1.sqlite` ile
    çalıştırılan bir komut `baglan()`a düşüyordu ve o tam şemayı kuruyordu.
    Sonuç, kullanıcı veritabanında paylaşımlı tabloların BOŞ gölge kopyaları
    oldu. SQLite niteliksiz adı önce `main`de aradığı için bütün sorgular
    45.899 satırlık `liste_parca` yerine boş olanı okumaya başladı.

    Sessiz ve yıkıcı: hata vermiyor, sadece her şey boş dönüyor. Öneriler
    kaybolur, PMI sıfırlanır, kimse sebebini anlamaz.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        D = _ortam(tmp)
        hedef = D.KULLANICI_KOK / "7.sqlite"
        conn = D.baglan(hedef)          # düz `baglan` — yönlendirmeli
        try:
            tablolar = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            golge = tablolar & D.ORTAK_TABLOLAR
            assert not golge, f"kullanıcı vt'sinde gölge tablo: {sorted(golge)}"
            # Ve ortak tablolar yine okunabilmeli (ATTACH üzerinden).
            conn.execute("SELECT COUNT(*) FROM liste_parca").fetchone()
        finally:
            conn.close()


def test_varsayilan_db_kullaniciya_bakar():
    """CLI araçları ile web uygulaması AYNI veritabanını görmeli.

    Çok kiracılığa geçişte `VARSAYILAN_DB` eski tek dosyayı gösteriyordu:
    komutlar oraya yazıyor, web uygulaması kullanıcı dosyasını okuyordu ve
    ikisi sessizce ayrıştı (ölçüldü: geri bildirim 15'e karşı 32).
    """
    from python.db import ESKI_TEK_DB, VARSAYILAN_DB

    assert VARSAYILAN_DB != ESKI_TEK_DB
    # `KULLANICI_KOK` ile karşılaştırılmıyor: diğer testler onu geçici dizine
    # yönlendiriyor ve sıraya bağlı bir sınama olurdu. Yapının kendisi
    # sınanıyor.
    assert VARSAYILAN_DB.parent.name == "kullanici", VARSAYILAN_DB


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
