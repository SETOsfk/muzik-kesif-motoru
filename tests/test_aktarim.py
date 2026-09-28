"""Spotify aktarım hattı testleri — ağa çıkmaz, torch yüklemez.

Hattın pahalı ve ağa bağlı iki ucu (Deezer, CLAP) sahteleriyle değiştiriliyor;
sınanan şey aradaki mantık: tekilleştirme, doğrulama, artımlılık, c seçimi
ve web akışının yarım bir hattı kullanıcıya "hazır" diye göstermemesi.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def _yollari_geri_al():
    """`_ortam` modül genellerini değiştiriyor; sonraki test dosyalarına
    sızmasın (özellikle `GOMU_KLASOR` — ses kümesi testleri onu okuyor)."""
    import python.db as D
    import python.etiket_clap as E

    eski = (D.KULLANICI_KOK, D.VARSAYILAN_ORTAK, E.GOMU_KLASOR)
    yield
    D.KULLANICI_KOK, D.VARSAYILAN_ORTAK, E.GOMU_KLASOR = eski


def _ortam(tmp):
    import python.db as D
    import python.etiket_clap as E

    kok = Path(tmp)
    D.KULLANICI_KOK = kok / "kullanici"
    D.VARSAYILAN_ORTAK = kok / "ortak.sqlite"
    E.GOMU_KLASOR = kok / "clap"
    return D, E


class _SahteDeezer:
    """`search` ve `track/{id}` yanıtları; kaç kez çağrıldığını sayar."""

    def __init__(self, arama: dict[str, list[dict]]):
        self.arama = arama
        self.cagri: list[tuple[str, dict, bool]] = []

    def get_json(self, yol, params=None, *, yenile=False):
        self.cagri.append((yol, params or {}, yenile))
        if yol == "search":
            return {"data": self.arama.get(params["q"], [])}
        if yol.startswith("track/"):
            return {"preview": f"https://ornek/{yol.split('/')[1]}.mp3"}
        return None


def _kayit(sanatci, album, kaynak="spotify_kayitli", yil=None):
    return {"sanatci": sanatci, "album": album, "yil": yil, "kaynak": kaynak}


def test_c_tavani_kutuphaneyle_buyur():
    """Tavan n//10, [2, 12]. Seçimi tavan değil stabilite yapar."""
    from python.aktarim import c_tavani

    assert c_tavani(20) == 2
    assert c_tavani(52) == 5
    assert c_tavani(288) == 12
    assert c_tavani(5000) == 12


def test_en_ince_stabil_c_xb_yerine_stabiliteye_bakar():
    """XB c=2'yi sevse de bütün kümeleri stabil en büyük c seçilmeli;
    küçük kümeli ya da kararsız c'ler elenmeli."""
    from types import SimpleNamespace

    from python.kumeleme.fcm import en_ince_stabil_c

    def t(c, xb, boyutlar):
        atama = np.repeat(np.arange(c), boyutlar)
        return SimpleNamespace(c=c, xie_beni=xb, partition_entropy=0.1,
                               sonuc=SimpleNamespace(keskin_atama=lambda a=atama: a))

    # Düz rejim (CLAP gibi): XB'ler birbirine yakın → en ince stabil c.
    taramalar = [t(2, 0.5, [30, 30]), t(3, 0.7, [20, 20, 20]),
                 t(4, 0.6, [20, 20, 17, 3]), t(5, 0.6, [12] * 5)]
    oranlar = {2: 1.0, 3: 1.0, 4: 1.0, 5: 0.8}
    assert en_ince_stabil_c(taramalar, oranlar).c == 3   # 4 küçük, 5 kararsız

    # Yapılı rejim: doğru c'nin XB'si çok daha iyi → daha ince ama kötü c'ler
    # stabil olsa bile seçilmez (bootstrap gürültüdeki bölünmeyi de kararlı bulur).
    taramalar = [t(2, 0.23, [30, 30]), t(3, 0.01, [20, 20, 20]),
                 t(4, 1.1, [15, 15, 15, 15]), t(5, 1.4, [12] * 5)]
    oranlar = {2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0}
    assert en_ince_stabil_c(taramalar, oranlar).c == 3


def test_kutuphaneye_yaz_tekillestirir_ve_kaynak_yazar():
    """Aynı albüm iki kaynaktan (kayıtlı + son çalınan) iki kimlikle girmemeli.

    Spotify kayıtlı albümde yıl veriyor, son çalınanda vermiyor; kimlik yıla
    bağlı olduğu için kimlikle tekilleştirmek ikizler üretirdi.
    """
    from python.aktarim import kutuphaneye_yaz

    with tempfile.TemporaryDirectory() as tmp:
        D, _ = _ortam(tmp)
        conn = D.baglan_kullanici(7)
        with conn:
            conn.execute("INSERT INTO albums (album_id, artist, title) "
                         "VALUES ('yerel1', 'Rush', 'Hemispheres')")
        n = kutuphaneye_yaz(conn, [
            _kayit("Rush", "Hemispheres", yil=1978),          # yerelde var
            _kayit("Tool", "Lateralus", yil=2001),
            _kayit("TOOL", "Lateralus", kaynak="spotify_son"),  # aynı albüm
            _kayit("Nas", "Illmatic", kaynak="spotify_son"),
        ])
        assert n == 2, n
        satirlar = {r["title"]: r["kaynak"] for r in conn.execute(
            "SELECT title, kaynak FROM albums")}
        assert satirlar == {"Hemispheres": "yerel", "Lateralus": "spotify_kayitli",
                            "Illmatic": "spotify_son"}, satirlar
        conn.close()


def test_gomule_yanlis_albumu_gommez():
    """Arama sanatçının HIT şarkısına düşerse o klip yanlış albümü anlatır.

    Doğrulanamayan albüm gömülmemeli — `onizleme._album_uyuyor_mu` ile aynı
    gerekçe (Mariya Takeuchi'nin üç albümü için de «Plastic Love» dönmüştü).
    """
    from python.aktarim import Ilerleme, gomule, kutuphaneye_yaz

    with tempfile.TemporaryDirectory() as tmp:
        D, E = _ortam(tmp)
        conn = D.baglan_kullanici(7)
        kutuphaneye_yaz(conn, [_kayit("Mariya Takeuchi", "Love Songs"),
                               _kayit("Tool", "Lateralus")])
        deezer = _SahteDeezer({
            "Mariya Takeuchi Love Songs": [{
                "id": 1, "title": "Plastic Love",
                "artist": {"name": "Mariya Takeuchi"},
                "album": {"title": "Variety"}}],
            "Tool Lateralus": [{
                "id": 2, "title": "Schism", "artist": {"name": "TOOL"},
                "album": {"title": "Lateralus"}}],
        })
        gomulen = []

        def gomucu(url):
            gomulen.append(url)
            return np.ones(512, dtype="float32") / np.sqrt(512)

        sayac = gomule(conn, Ilerleme(None, sessiz=True),
                       gomucu=gomucu, istemci=deezer)
        assert sayac["gomulen"] == 1 and sayac["eslesmedi"] == 1, sayac
        assert gomulen == ["https://ornek/2.mp3"], gomulen
        conn.close()


def test_gomule_taze_url_ister_ve_artimlidir():
    """İki kural: (1) önizleme URL'si `yenile=True` ile alınır — imzalı URL
    kısa ömürlü, önbellekteki 403 döner; (2) gömüsü olan albüme dokunulmaz."""
    from python.aktarim import Ilerleme, gomule, kutuphaneye_yaz

    with tempfile.TemporaryDirectory() as tmp:
        D, E = _ortam(tmp)
        conn = D.baglan_kullanici(7)
        kutuphaneye_yaz(conn, [_kayit("Tool", "Lateralus")])
        deezer = _SahteDeezer({"Tool Lateralus": [{
            "id": 2, "title": "Schism", "artist": {"name": "Tool"},
            "album": {"title": "Lateralus"}}]})
        birim = lambda url: np.ones(512, dtype="float32") / np.sqrt(512)  # noqa: E731

        gomule(conn, Ilerleme(None, sessiz=True), gomucu=birim, istemci=deezer)
        parca_cagrilari = [c for c in deezer.cagri if c[0].startswith("track/")]
        assert parca_cagrilari and all(c[2] for c in parca_cagrilari), parca_cagrilari

        deezer.cagri.clear()
        sayac = gomule(conn, Ilerleme(None, sessiz=True), gomucu=birim, istemci=deezer)
        assert sayac["hazir"] == 1 and not deezer.cagri, (sayac, deezer.cagri)
        conn.close()


def test_az_albumle_kumeleme_yapilmaz():
    from python.aktarim import AktarimHatasi, kumele, kutuphaneye_yaz

    with tempfile.TemporaryDirectory() as tmp:
        D, E = _ortam(tmp)
        conn = D.baglan_kullanici(7)
        kutuphaneye_yaz(conn, [_kayit("A", f"Albüm {i}") for i in range(5)])
        try:
            kumele(7, conn)
        except AktarimHatasi as hata:
            assert "en az" in str(hata)
        else:
            raise AssertionError("5 albümle kümeleme yapıldı")
        conn.close()


def test_kumele_sesten_eksen_cikarir():
    """Bilinen yapı: üç ayrı ses bölgesi → stabil eksenler, doğru ayrım."""
    from python.aktarim import kumele, kutuphaneye_yaz
    from python.metin import album_kimligi

    with tempfile.TemporaryDirectory() as tmp:
        D, E = _ortam(tmp)
        E.GOMU_KLASOR.mkdir(parents=True)
        conn = D.baglan_kullanici(7)
        rng = np.random.default_rng(0)
        merkezler = np.eye(512, dtype="float32")[:3] * 3
        kayitlar = []
        for i in range(75):
            k = _kayit(f"Sanatçı {i}", f"Albüm {i}")
            kayitlar.append(k)
            v = merkezler[i % 3] + rng.normal(0, 0.05, 512).astype("float32")
            np.save(E.GOMU_KLASOR / f"{album_kimligi(k['sanatci'], k['album'])}.npy",
                    v / np.linalg.norm(v))
        kutuphaneye_yaz(conn, kayitlar)
        sonuc = kumele(7, conn)
        assert sonuc["albüm"] == 75 and sonuc["c"] == 3, sonuc
        assert sonuc["stabil"] == 3, sonuc
        n = conn.execute("SELECT COUNT(DISTINCT album_id) FROM memberships "
                         "WHERE calisma_id = ?", (sonuc["calisma_id"],)).fetchone()[0]
        assert n == 75, n
        conn.close()


def test_olu_surec_calisiyor_sayilmaz():
    """Süreç öldürülürse durum dosyası sonsuza dek 'çalışıyor' derdi."""
    from python.aktarim import calisiyor_mu, durum_yolu

    with tempfile.TemporaryDirectory() as tmp:
        _ortam(tmp)
        yol = durum_yolu(7)
        yol.parent.mkdir(parents=True)
        yol.write_text(json.dumps({"durum": "calisiyor", "pid": os.getpid()}))
        assert calisiyor_mu(7)
        # Var olmayan süreç kimliği (Darwin/Linux'ta pid_max'ın üstü).
        yol.write_text(json.dumps({"durum": "calisiyor", "pid": 2 ** 22 + 7}))
        assert not calisiyor_mu(7)


def test_durum_dosyasi_gercek_dizine_yazilmaz():
    """Yol ÇAĞRI ANINDA çözülmeli; testin yönlendirmesi işlemeli."""
    from python.aktarim import Ilerleme

    with tempfile.TemporaryDirectory() as tmp:
        D, _ = _ortam(tmp)
        Ilerleme(987654, sessiz=True).asama("gomu", 3)
        assert (D.KULLANICI_KOK / "987654.aktarim.json").exists()
    assert not Path("data/db/kullanici/987654.aktarim.json").exists()


# --------------------------------------------------------------------------- #
# Web akışı
# --------------------------------------------------------------------------- #

def _istemci(tmp, *, spotify=True):
    from starlette.testclient import TestClient

    from python.hesap import CEREZ_ADI, kullanici_olustur, oturum_ac

    D, E = _ortam(tmp)
    conn = D.baglan_ortak()
    kid = kullanici_olustur(conn, "Yeni", eposta="y@y.y",
                            spotify_id="sp_9" if spotify else None,
                            spotify_yenile="yj" if spotify else None)
    jeton = oturum_ac(conn, kid)
    conn.close()
    from web.sunucu import uygulama
    istemci = TestClient(uygulama)
    istemci.cookies.set(CEREZ_ADI, jeton)
    return istemci, kid, D


def test_calisma_yoksa_oneriler_baslaya_gider():
    """Yeni kullanıcı komut satırı talimatı görmemeli."""
    with tempfile.TemporaryDirectory() as tmp:
        istemci, _, _ = _istemci(tmp)
        yanit = istemci.get("/oneriler", follow_redirects=False)
        assert yanit.status_code == 303 and yanit.headers["location"] == "/basla"


def test_yarim_hat_oneriye_yonlendirmez():
    """Albüm var ama aday yok (aktarım sürüyor) → /basla'da kal, ilerlemeyi göster."""
    from python.aktarim import Ilerleme

    with tempfile.TemporaryDirectory() as tmp:
        istemci, kid, D = _istemci(tmp)
        conn = D.baglan_kullanici(kid)
        with conn:
            conn.execute("INSERT INTO albums (album_id, artist, title, kaynak) "
                         "VALUES ('a', 'Tool', 'Lateralus', 'spotify_kayitli')")
        conn.close()
        Ilerleme(kid, sessiz=True).asama("gomu", 40)

        yanit = istemci.get("/basla", follow_redirects=False)
        assert yanit.status_code == 200, yanit.status_code
        assert "aktarılıyor" in yanit.text and "0/40" in yanit.text

        durum = istemci.get("/api/aktar/durum").json()
        assert durum["calisiyor"] and durum["asama"] == "gomu", durum


def test_spotifysiz_hesap_aktarim_baslatamaz():
    with tempfile.TemporaryDirectory() as tmp:
        istemci, _, _ = _istemci(tmp, spotify=False)
        yanit = istemci.post("/api/aktar", follow_redirects=False)
        assert yanit.headers["location"] == "/basla?hata=spotify_yok"


def test_hata_durumu_gosterilir():
    from python.aktarim import Ilerleme

    with tempfile.TemporaryDirectory() as tmp:
        istemci, kid, _ = _istemci(tmp)
        i = Ilerleme(kid, sessiz=True)
        i.asama("kume")
        i.bitir(hata="kümeleme için en az 20 albümün sesi gerekiyor, 4 tanesi bulunabildi")
        yanit = istemci.get("/basla")
        assert "Aktarım durdu" in yanit.text and "4 tanesi" in yanit.text
        assert "yeniden başlat" in yanit.text


# --------------------------------------------------------------------------- #
# Spotify'sız başlangıç: elle yazılmış liste (2026-09-28)
# --------------------------------------------------------------------------- #

def test_liste_ayristir_sanatci_ve_albumu_ayirir():
    from python.aktarim import liste_ayristir

    kayitlar, sanatcilar = liste_ayristir(
        "1. Tool\n- Casiopea\n\nPlini — Impulse Voices\nJay-Z\n"
        "AC/DC - Back in Black\ntool\n• Sigur Rós\t( )\n")
    assert sanatcilar == ["Tool", "Casiopea", "Jay-Z"], sanatcilar
    assert [(k["sanatci"], k["album"]) for k in kayitlar] == [
        ("Plini", "Impulse Voices"), ("AC/DC", "Back in Black"), ("Sigur Rós", "( )")]
    assert {k["kaynak"] for k in kayitlar} == {"liste"}


def test_liste_tavani_ve_yeterlilik():
    from python.aktarim import (
        ASGARI_ALBUM, LISTE_AZAMI_SATIR, LISTE_SANATCI_ALBUM, liste_ayristir,
        liste_yeterli_mi,
    )

    _, sanatcilar = liste_ayristir("\n".join(f"S{i}" for i in range(500)))
    assert len(sanatcilar) == LISTE_AZAMI_SATIR
    gerekli = -(-ASGARI_ALBUM // LISTE_SANATCI_ALBUM)
    assert liste_yeterli_mi([], [f"S{i}" for i in range(gerekli)])
    assert not liste_yeterli_mi([], [f"S{i}" for i in range(gerekli - 1)])


def test_sanatci_albumleri_ayri_albumler_doner():
    """En popüler parçaların İKİSİ aynı albümdense ikinci albüm aşağıdan gelir."""
    from python.aktarim import sanatci_albumleri, sanatci_albumu

    class _Sahte:
        def get_json(self, yol, params=None, *, yenile=False):
            if yol == "search/artist":
                return {"data": [{"id": 5, "name": "Tool"}]}
            if yol == "artist/5/top":
                return {"data": [
                    {"id": 1, "title": "Schism", "album": {"title": "Lateralus"}},
                    {"id": 2, "title": "Parabola", "album": {"title": "Lateralus"}},
                    {"id": 3, "title": "Sober", "album": {"title": "Undertow"}},
                    {"id": 4, "title": "Pneuma", "album": {"title": "Fear Inoculum"}},
                ]}
            return None

    iki = sanatci_albumleri(_Sahte(), "tool", adet=2, kaynak="liste")
    assert [a["album"] for a in iki] == ["Lateralus", "Undertow"]
    assert {a["kaynak"] for a in iki} == {"liste"} and iki[0]["sanatci"] == "Tool"
    assert sanatci_albumu(_Sahte(), "tool")["kaynak"] == "spotify_en_cok"


def test_kisa_liste_sureci_baslatmaz_ve_metni_korur():
    with tempfile.TemporaryDirectory() as tmp:
        istemci, kid, D = _istemci(tmp, spotify=False)
        yanit = istemci.post("/api/aktar/liste", data={"liste": "Tool\nCasiopea"},
                             follow_redirects=False)
        assert yanit.status_code == 400
        assert "Casiopea" in yanit.text and "kısa" in yanit.text
        assert not (D.KULLANICI_KOK / f"{kid}.liste.json").exists()


def test_liste_aktarimi_ayri_surec_baslatir(monkeypatch):
    import subprocess

    import web.sunucu as W

    cagrilar = []

    class _Surec:
        pid = 2 ** 22 + 7  # yaşamayan süreç: ikinci istek "zaten çalışıyor"a takılmasın

    def _popen(arg, **kw):
        cagrilar.append(arg)
        return _Surec()

    monkeypatch.setattr(subprocess, "Popen", _popen)
    with tempfile.TemporaryDirectory() as tmp:
        istemci, kid, D = _istemci(tmp, spotify=False)
        metin = "\n".join(f"Sanatçı {i}" for i in range(12)) + "\nPlini — Impulse Voices"
        yanit = istemci.post("/api/aktar/liste", data={"liste": metin},
                             follow_redirects=False)
        assert yanit.status_code == 303 and yanit.headers["location"] == "/basla"
        dosya = D.KULLANICI_KOK / f"{kid}.liste.json"
        girdi = json.loads(dosya.read_text(encoding="utf-8"))
        assert {"sanatci": "Plini", "album": "Impulse Voices", "kaynak": "liste"} in girdi
        assert {"sanatci": "Sanatçı 0"} in girdi
        assert len(cagrilar) == 1 and "--json" in cagrilar[0]
        assert cagrilar[0][cagrilar[0].index("--json") + 1] == str(dosya.resolve())
        # Durum HEMEN yazılıyor: alt süreç kendi dosyasını yazmadan dönülen
        # /basla formu değil ilerlemeyi göstermeli.
        from python.aktarim import durum_oku
        durum = durum_oku(kid)
        assert durum["pid"] == _Surec.pid and durum["kaynak"] == "liste"

        # Eşzamanlı aktarım tavanı dolunca yeni süreç açılmaz, metin korunur.
        monkeypatch.setattr(W, "AZAMI_ES_ZAMANLI_AKTARIM", 0)
        yanit = istemci.post("/api/aktar/liste", data={"liste": metin},
                             follow_redirects=False)
        assert yanit.status_code == 503 and "Sanatçı 11" in yanit.text
        assert len(cagrilar) == 1


def test_listeyle_gelen_spotify_asamasini_gormez():
    from python.aktarim import Ilerleme

    with tempfile.TemporaryDirectory() as tmp:
        istemci, kid, _ = _istemci(tmp, spotify=False)
        i = Ilerleme(kid, sessiz=True)
        i.veri["kaynak"] = "liste"
        i.asama("eslesme", 12)
        yanit = istemci.get("/basla")
        assert "aktarılıyor" in yanit.text and "0/12" in yanit.text
        assert "Spotify kütüphanen okunuyor" not in yanit.text


def test_calistir_listeyle_albumsuz_sanatcilari_cozer(monkeypatch):
    """Liste yolu: albümsüz sanatçı LISTE_SANATCI_ALBUM albümle kütüphaneye girer."""
    import python.aktarim as A
    import python.discover.calma_listesi as C

    monkeypatch.setattr(C, "deezer_listesi", lambda: object())
    monkeypatch.setattr(A, "sanatci_albumleri", lambda istemci, s, *, adet, kaynak: [
        {"sanatci": s, "album": f"{s} {i}", "yil": None, "kaynak": kaynak}
        for i in range(adet)])
    monkeypatch.setattr(A, "gomule", lambda conn, ilerleme: {})
    with tempfile.TemporaryDirectory() as tmp:
        D, _ = _ortam(tmp)
        with pytest.raises(Exception):
            # Hasat ağa çıkmaya çalışır; buraya kadar gelmesi yeter.
            A.calistir(3, kayitlar=[_kayit("Plini", "Impulse Voices", "liste")],
                       sanatcilar=["Tool", "Casiopea"], sessiz=True)
        conn = D.baglan_kullanici(3)
        satirlar = conn.execute("SELECT artist, title, kaynak FROM albums ORDER BY title").fetchall()
        conn.close()
        assert [tuple(r) for r in satirlar] == [
            ("Casiopea", "Casiopea 0", "liste"), ("Casiopea", "Casiopea 1", "liste"),
            ("Plini", "Impulse Voices", "liste"),
            ("Tool", "Tool 0", "liste"), ("Tool", "Tool 1", "liste")]
        assert A.durum_oku(3)["kaynak"] == "liste"


def test_deezer_ulasilamazsa_hizla_durur(monkeypatch):
    """Ağ yoksa her sanatçı ~30 sn deneniyordu; art arda üç hata yeter."""
    import python.aktarim as A
    import python.discover.calma_listesi as C

    cagri = []

    def _patlayan(istemci, s, *, adet, kaynak):
        cagri.append(s)
        raise ConnectionError("ağ yok")

    monkeypatch.setattr(C, "deezer_listesi", lambda: object())
    monkeypatch.setattr(A, "sanatci_albumleri", _patlayan)
    with tempfile.TemporaryDirectory() as tmp:
        _ortam(tmp)
        with pytest.raises(A.AktarimHatasi, match="Deezer"):
            A.calistir(4, kayitlar=[], sanatcilar=[f"S{i}" for i in range(12)], sessiz=True)
        assert len(cagri) == A.AG_HATA_ESIGI
        durum = A.durum_oku(4)
        assert durum["durum"] == "hata" and "Deezer" in durum["hata"]


def test_olen_cocuk_surec_zombi_kalmaz_calisiyor_sayilmaz():
    """Sunucunun başlattığı ve ölen aktarım `<defunct>` kalıp 'çalışıyor' sayılıyordu."""
    import subprocess

    from python.aktarim import baslangic_yaz, calisiyor_mu

    with tempfile.TemporaryDirectory() as tmp:
        _ortam(tmp)
        surec = subprocess.Popen([sys.executable, "-c", "pass"])
        baslangic_yaz(8, surec.pid, "liste")
        # Bitmesini BİÇMEDEN bekle (WNOWAIT): çocuk zombi olarak kalır.
        os.waitid(os.P_PID, surec.pid, os.WEXITED | os.WNOWAIT)
        assert not calisiyor_mu(8)
        surec.returncode = 0  # Popen'in kendi wait'i ECHILD'e takılmasın
