"""Yayın testleri — herkese açık bir sürümün ihtiyaç duyduğu kapılar.

Gizlilik notu oturumsuz okunabilmeli; hesap silme kişisel veriyi bütünüyle
silmeli ama paylaşımlı veriye (albümü tarif eden gömüler, havuz)
dokunmamalı; sürüm sağlık ucunda görünmeli.
"""

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


def _istemci(tmp):
    from starlette.testclient import TestClient

    import python.db as D
    from python.hesap import CEREZ_ADI, kullanici_olustur, oturum_ac

    kok = Path(tmp)
    D.KULLANICI_KOK = kok / "kullanici"
    D.VARSAYILAN_ORTAK = kok / "ortak.sqlite"
    conn = D.baglan_ortak()
    kid = kullanici_olustur(conn, "Silinecek", eposta="s@s.s", parola="parola123")
    jeton = oturum_ac(conn, kid)
    conn.close()
    from web.sunucu import uygulama
    istemci = TestClient(uygulama)
    istemci.cookies.set(CEREZ_ADI, jeton)
    return istemci, kid, D


def test_gizlilik_oturumsuz_acik():
    from starlette.testclient import TestClient

    from web.sunucu import uygulama

    with tempfile.TemporaryDirectory() as tmp:
        import python.db as D
        D.VARSAYILAN_ORTAK = Path(tmp) / "ortak.sqlite"
        D.KULLANICI_KOK = Path(tmp) / "kullanici"
        yanit = TestClient(uygulama).get("/gizlilik", follow_redirects=False)
        assert yanit.status_code == 200
        assert "Deezer" in yanit.text and "/hesap/sil" not in yanit.text


def test_hesap_silme_oturumsuz_kapali():
    from starlette.testclient import TestClient

    from web.sunucu import uygulama

    with tempfile.TemporaryDirectory() as tmp:
        import python.db as D
        D.VARSAYILAN_ORTAK = Path(tmp) / "ortak.sqlite"
        D.KULLANICI_KOK = Path(tmp) / "kullanici"
        yanit = TestClient(uygulama).post("/hesap/sil", data={"onay": "evet"},
                                          follow_redirects=False)
        assert yanit.status_code == 303 and yanit.headers["location"] == "/giris"


def test_onaysiz_silme_bir_sey_silmez():
    with tempfile.TemporaryDirectory() as tmp:
        istemci, kid, D = _istemci(tmp)
        istemci.get("/basla")  # kullanıcı dosyası kurulsun
        yanit = istemci.post("/hesap/sil", data={}, follow_redirects=False)
        assert yanit.headers["location"] == "/gizlilik"
        assert D.kullanici_db(kid).exists()


def test_hesap_silme_kisisel_veriyi_siler_paylasimliya_dokunmaz():
    from python.hesap import kullanici_bul

    with tempfile.TemporaryDirectory() as tmp:
        istemci, kid, D = _istemci(tmp)
        conn = D.baglan_kullanici(kid)
        with conn:
            conn.execute("INSERT INTO albums (album_id, artist, title, kaynak) "
                         "VALUES ('a', 'Tool', 'Lateralus', 'liste')")
            conn.execute("INSERT INTO calma_listesi (liste_id, baslik) VALUES (1, 'prog')")
        conn.close()
        for sonek in (".liste.json", ".aktarim.json", ".aktarim.log"):
            (D.KULLANICI_KOK / f"{kid}{sonek}").write_text("{}")

        yanit = istemci.post("/hesap/sil", data={"onay": "evet"}, follow_redirects=False)
        assert yanit.headers["location"] == "/giris?hata=silindi"
        cerez = yanit.headers.get("set-cookie", "")
        assert "kesif_oturum=" in cerez and "Max-Age=0" in cerez, cerez

        kalan = sorted(p.name for p in D.KULLANICI_KOK.iterdir())
        assert kalan == [], kalan
        ortak = D.baglan_ortak()
        try:
            assert kullanici_bul(ortak, kullanici_id=kid) is None
            assert ortak.execute("SELECT COUNT(*) FROM oturum").fetchone()[0] == 0
            # Paylaşımlı havuz albümü/sanatçıyı tarif ediyor, kişiyi değil.
            assert ortak.execute("SELECT COUNT(*) FROM calma_listesi").fetchone()[0] == 1
        finally:
            ortak.close()
        # Eski çerezle artık içeri girilemez.
        assert istemci.get("/kesfet", follow_redirects=False).headers["location"] == "/giris"


def test_saglik_surumu_soyler():
    from python import __version__

    with tempfile.TemporaryDirectory() as tmp:
        istemci, _, _ = _istemci(tmp)
        govde = istemci.get("/saglik").json()
        assert govde["durum"] == "ayakta" and govde["surum"] == __version__
