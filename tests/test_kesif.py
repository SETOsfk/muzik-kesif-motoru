"""Keşfet destesi, Listem, medya, gerekçe ve iki dil (2026-09-23).

Hepsi geçici dizinde, ağsız: medya çözücüsüne sahte bir Deezer istemcisi
veriliyor. Gerçek `data/` klasörüne dokunan tek bir satır yok — bugünkü
gölge tablo olayı (karar günlüğü 2026-09-23) tam olarak bunun ihlaliydi.
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

import python.db as D
from python import kesif
from python.dil import AKTIF_DIL, istekten_dil, sayi, yuzde, bas_harf_buyuk


# --------------------------------------------------------------------------- #
# Kurulum
# --------------------------------------------------------------------------- #

CALISMA = "20260923T000000-test"


@pytest.fixture
def kum(tmp_path, monkeypatch):
    """Geçici kullanıcı + ortak veritabanı, küçük ama gerçekçi bir çalışma."""
    monkeypatch.setattr(D, "KULLANICI_KOK", tmp_path / "kullanici")
    monkeypatch.setattr(D, "VARSAYILAN_ORTAK", tmp_path / "ortak.sqlite")
    conn = D.baglan_kullanici(1)
    with conn:
        conn.executemany(
            "INSERT INTO albums (album_id, artist, title, year) VALUES (?,?,?,?)",
            [("k1", "Duman", "Belki Alışman Lazım", 1999),
             ("k2", "Meshuggah", "Obzen", 2008),
             ("k3", "Casiopea", "Mint Jams", 1982)])
        conn.executemany(
            "INSERT INTO clusters (kume_id, calisma_id, kullanici_adi, stabil_mi) VALUES (?,?,?,1)",
            [(0, CALISMA, "metal"), (1, CALISMA, None)])
        satirlar = [
            # (aday_id, eksen, strateji, artist, title, skor, parca_id, dayanak)
            ("a0000001", 0, "melez", "Car Bomb", "Hela", 0.9, 111,
             {"pmi": 0.67, "birlikte_liste": 5, "kaynak_sanatcilar": ["meshuggah"],
              "benzedigi": "Meshuggah — Obzen"}),
            ("a0000002", 0, "melez", "Car Bomb", "Lights Out", 0.8, 112, {}),
            ("a0000003", 0, "liste_birlikteligi", "Gojira", "Stranded", 0.7, 113,
             {"pmi": 0.5, "birlikte_liste": 2, "kaynak_sanatcilar": ["meshuggah"]}),
            ("a0000004", 0, "ses_benzerligi", "Tesseract", "Concealing Fate", 0.6, 114,
             {"benzedigi": "Meshuggah — Obzen", "clap_skor": 0.2}),
            ("a0000005", 1, "melez", "Sezen Aksu", "Kaybolan Yıllar", 0.5, 115,
             {"pmi": 0.53, "birlikte_liste": 3, "kaynak_sanatcilar": ["duman"]}),
            ("a0000006", 1, "ses_benzerligi", "T-Square", "Truth", 0.4, None,
             {"benzedigi": "Casiopea — Mint Jams"}),
        ]
        for aid, eksen, st, artist, title, skor, pid, day in satirlar:
            conn.execute(
                """INSERT INTO adaylar (aday_id, calisma_id, eksen, strateji, artist,
                   title, skor, gerekce, dayanak, birim, parca_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (aid, CALISMA, eksen, st, artist, title, skor,
                 "İKİ SİNYAL DE işaret ediyor ... kulağa senin «Meshuggah — Obzen» albümüne benziyor.",
                 json.dumps(day), "parca" if pid else "album", pid))
    yield conn
    conn.close()


def _kimlikler(deste):
    return [k["aday_id"] for k in deste["kartlar"]]


# --------------------------------------------------------------------------- #
# Deste
# --------------------------------------------------------------------------- #

def test_deste_sanatci_basina_tek_kart(kum):
    d = kesif.deste(kum, CALISMA, adet=20)
    sanatcilar = [k["artist"] for k in d["kartlar"]]
    assert len(sanatcilar) == len(set(sanatcilar)), sanatcilar
    assert "Car Bomb" in sanatcilar
    car = next(k for k in d["kartlar"] if k["artist"] == "Car Bomb")
    # Kart sanatçının bu çalışmadaki TÜM aday satırlarını taşır (karar hepsine).
    assert set(car["kimlikler"]) == {"a0000001", "a0000002"}


def test_deste_eksenler_arasi_doner(kum):
    """İlk iki kart iki farklı eksenden gelmeli (round-robin)."""
    d = kesif.deste(kum, CALISMA, adet=2)
    assert {k["eksen"] for k in d["kartlar"]} == {0, 1}


def test_deste_adlandirilmis_eksen_once(kum):
    d = kesif.deste(kum, CALISMA, adet=1)
    assert d["kartlar"][0]["eksen"] == 0     # "metal" adlı eksen


def test_deste_tekrarlanabilir(kum):
    """Aynı durum aynı desteyi verir (Thompson tohumu karar sayısından)."""
    assert _kimlikler(kesif.deste(kum, CALISMA, adet=10)) == \
        _kimlikler(kesif.deste(kum, CALISMA, adet=10))


def test_deste_haric_ve_karar_verilenleri_atlar(kum):
    kesif.karar_kaydet(kum, CALISMA, "a0000001", "tutmadi")
    d = kesif.deste(kum, CALISMA, adet=20, haric={"a0000003"})
    sanatcilar = {k["artist"] for k in d["kartlar"]}
    assert "Car Bomb" not in sanatcilar, "karar verilmiş sanatçı bir daha gelmemeli"
    assert "Gojira" not in sanatcilar, "istemci kuyruğundaki sanatçı tekrar gelmemeli"


def test_thompson_tutan_kaynagi_one_alir(kum):
    """Gerçek kararlarda bir kaynak açıkça tutuyorsa destede öne çıkar.

    `ses_benzerligi` 12/0, `melez` 0/12: 0. eksenin ilk kartı ses kaynağından
    gelmeli (Beta(13,1) çekilişi Beta(1,13)'ü neredeyse her zaman geçer)."""
    with kum:
        for i in range(12):
            for st, karar in (("ses_benzerligi", "begendim"), ("melez", "tutmadi")):
                aid = f"{st[:3]}{i:05d}"
                kum.execute(
                    "INSERT INTO adaylar (aday_id, calisma_id, eksen, strateji, artist, title, skor, gerekce) "
                    "VALUES (?,?,?,?,?,?,?,?)", (aid, "eski", 0, st, f"{st}-{i}", "x", 0.1, ""))
                kum.execute(
                    "INSERT INTO feedback (aday_id, calisma_id, eksen, karar, tarih) VALUES (?,?,?,?,date('now'))",
                    (aid, "eski", 0, karar))
    d = kesif.deste(kum, CALISMA, eksen=0, adet=1)
    assert d["kartlar"][0]["strateji"] == "ses_benzerligi", d["kartlar"][0]


def test_sonsallar_sanatci_duzeyinde(kum):
    """İki albümlük sanatçıya verilen TEK karar iki karar sayılmamalı."""
    kesif.karar_kaydet(kum, CALISMA, "a0000001", "begendim")
    assert kesif.strateji_sonsallari(kum)["melez"] == (1, 0)


# --------------------------------------------------------------------------- #
# Karar, geri alma, liste
# --------------------------------------------------------------------------- #

def test_karar_sanatci_duzeyinde_yazilir(kum):
    v = kesif.karar_kaydet(kum, CALISMA, "a0000001", "begendim")
    assert v["adet"] == 2 and v["liste"] == 1
    kararlar = dict(kum.execute("SELECT aday_id, karar FROM feedback").fetchall())
    assert kararlar == {"a0000001": "begendim", "a0000002": "begendim"}
    satir = kum.execute("SELECT aday_id, durum, dayanak FROM liste").fetchone()
    assert satir["aday_id"] == "a0000001" and satir["durum"] == "yeni"
    assert json.loads(satir["dayanak"])["pmi"] == 0.67, "kanıt listeye kopyalanmalı"


def test_gecilen_listeye_girmez(kum):
    kesif.karar_kaydet(kum, CALISMA, "a0000003", "tutmadi")
    assert kesif.liste_sayisi(kum) == 0


def test_gecersiz_karar_reddedilir(kum):
    with pytest.raises(ValueError):
        kesif.karar_kaydet(kum, CALISMA, "a0000001", "harika")
    with pytest.raises(LookupError):
        kesif.karar_kaydet(kum, CALISMA, "yok00000", "begendim")


def test_geri_al_edinilmisi_silmez(kum):
    kesif.karar_kaydet(kum, CALISMA, "a0000001", "begendim")
    kesif.durum_guncelle(kum, "a0000001", "edinildi")
    kesif.karar_geri_al(kum, CALISMA, "a0000001")
    assert kum.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 0
    assert kesif.liste_sayisi(kum) == 1, "edinilmiş öğe bir geri al ile kaybolmamalı"


def test_geri_al_yeniyi_siler(kum):
    kesif.karar_kaydet(kum, CALISMA, "a0000004", "begendim")
    kesif.karar_geri_al(kum, CALISMA, "a0000004")
    assert kesif.liste_sayisi(kum) == 0


def test_liste_kutuphanede_bayragi(kum):
    """Listedeki albüm kütüphaneye taranınca «kütüphanende» görünür."""
    with kum:
        kum.execute(
            "INSERT INTO adaylar (aday_id, calisma_id, eksen, strateji, artist, title, skor, gerekce, birim) "
            "VALUES ('a0000009', ?, 0, 'kredi_sicramasi', 'Opeth', 'Damnation', 0.3, '', 'album')", (CALISMA,))
    kesif.karar_kaydet(kum, CALISMA, "a0000009", "begendim")
    assert not kesif.liste_ogeleri(kum)[0]["kutuphanede"]
    with kum:
        kum.execute("INSERT INTO albums (album_id, artist, title) VALUES ('k9', 'Opeth', 'Damnation')")
    assert kesif.liste_ogeleri(kum)[0]["kutuphanede"]


def test_durum_dogrulanir(kum):
    with pytest.raises(ValueError):
        kesif.durum_guncelle(kum, "a0000001", "satildi")


# --------------------------------------------------------------------------- #
# Dışa aktarım
# --------------------------------------------------------------------------- #

def test_disa_aktar_bicimleri(kum):
    kesif.karar_kaydet(kum, CALISMA, "a0000004", "begendim")
    kesif.karar_kaydet(kum, CALISMA, "a0000006", "begendim")
    ogeler = kesif.liste_ogeleri(kum)

    icerik, tur = kesif.disa_aktar(ogeler, "csv")
    assert icerik.startswith("﻿") and "text/csv" in tur
    assert icerik.splitlines()[0].lstrip("﻿").startswith("sanatçı,albüm")

    belirtec = AKTIF_DIL.set("en")
    try:
        icerik_en, _ = kesif.disa_aktar(ogeler, "csv")
    finally:
        AKTIF_DIL.reset(belirtec)
    assert icerik_en.splitlines()[0].lstrip("﻿").startswith("artist,album")

    txt, _ = kesif.disa_aktar(ogeler, "txt")
    assert "T-Square — Truth" in txt
    veri = json.loads(kesif.disa_aktar(ogeler, "json")[0])
    assert {v["sanatci"] for v in veri} == {"Tesseract", "T-Square"}
    with pytest.raises(ValueError):
        kesif.disa_aktar(ogeler, "m3u")


def test_edinme_baglantilari_satin_alma_once():
    b = kesif.edinme_baglantilari({"artist": "Casiopea", "album": "Mint Jams"})
    assert [ad for ad, _ in b[:2]] == ["Bandcamp", "Qobuz"]
    assert all(url.startswith("https://") for _, url in b)


# --------------------------------------------------------------------------- #
# Günlük seri
# --------------------------------------------------------------------------- #

def test_seri_bugun_karar_yokken_bozulmaz(kum):
    from datetime import date
    with kum:
        # Kararın sayılması için adayın `adaylar`da olması gerekir (sanatçı
        # düzeyinde sayım JOIN ile yapılıyor).
        for aid, gun in (("a0000001", "2026-09-20"), ("a0000003", "2026-09-21"),
                         ("a0000004", "2026-09-22")):
            kum.execute("INSERT INTO feedback (aday_id, calisma_id, eksen, karar, tarih) VALUES (?,?,0,'tutmadi',?)",
                        (aid, CALISMA, gun))
    assert kesif.gunluk_ozet(kum, bugun=date(2026, 9, 23))["seri"] == 3
    assert kesif.gunluk_ozet(kum, bugun=date(2026, 9, 24))["seri"] == 0


# --------------------------------------------------------------------------- #
# Gerekçe
# --------------------------------------------------------------------------- #

def test_gerekce_zayif_kaniti_soyler():
    from python.gerekce import gerekce
    metin = gerekce("liste_birlikteligi",
                    {"pmi": 0.53, "birlikte_liste": 3, "kaynak_sanatcilar": ["duman"]},
                    eksen="grunge", adlar={"duman": "Duman"})
    assert "Duman" in metin and "Zayıf kanıt" in metin
    guclu = gerekce("liste_birlikteligi",
                    {"pmi": 0.6, "birlikte_liste": 12, "kaynak_sanatcilar": ["duman"]}, eksen="x")
    assert "Zayıf" not in guclu


def test_gerekce_dogal_turkce_ve_ingilizce():
    from python.gerekce import gerekce
    tr = gerekce("ses_benzerligi", {"benzedigi": "Rush — Hemispheres"}, eksen="rush")
    assert "andırıyor" in tr and "Kulağa senin" not in tr
    belirtec = AKTIF_DIL.set("en")
    try:
        en = gerekce("ses_benzerligi", {"benzedigi": "Rush — Hemispheres"}, eksen="rush")
    finally:
        AKTIF_DIL.reset(belirtec)
    assert en.startswith("Its sound is close to «Rush — Hemispheres»")


def test_melez_gerekcesi_eski_satirdan_albumu_cikarir():
    """Eski melez satırlarında benzediği albüm yalnız Türkçe metnin içinde."""
    from python.gerekce import gerekce
    eski = "İKİ SİNYAL DE ... VE kulağa senin «Şebnem Ferah — 10 Mart 2007» albümüne benziyor."
    metin = gerekce("melez", {"pmi": 0.5, "birlikte_liste": 4, "kaynak_sanatcilar": []},
                    eksen="grunge", saklanan=eski)
    assert "Şebnem Ferah — 10 Mart 2007" in metin
    assert "İKİ SİNYAL" not in metin, "bağımsızlık iddiası kaldırıldı"


# --------------------------------------------------------------------------- #
# Medya — sahte Deezer, ağ yok
# --------------------------------------------------------------------------- #

class _SahteDeezer:
    servis = "deezer"

    def __init__(self, yanitlar):
        self.yanitlar, self.cagrilar = yanitlar, []

    def get_json(self, yol, params=None, *, yenile=False):
        self.cagrilar.append(yol)
        return self.yanitlar.get(yol, {})


def test_medya_parca_ve_yedek(kum):
    from python.medya import medya_coz
    istemci = _SahteDeezer({
        "track/115": {"title": "Kaybolan Yıllar", "preview": "",
                      "album": {"id": 9, "title": "Deniz Yıldızı", "cover_xl": "https://c/x.jpg"},
                      "artist": {"id": 77, "picture_xl": "https://c/a.jpg"}},
        "artist/77/top": {"data": [{"id": 5, "title": "Firuze", "preview": "https://p/5.mp3"}]},
    })
    m = medya_coz(kum, {"aday_id": "a0000005", "artist": "Sezen Aksu",
                        "title": "Kaybolan Yıllar", "parca_id": 115}, istemci=istemci)
    assert m["kapak"] == "https://c/x.jpg"
    assert m["yedek"] == 1 and m["parca_adi"] == "Firuze", "önizlemesiz parçada yedek AÇIKÇA işaretlenmeli"
    kayit = kum.execute("SELECT * FROM medya WHERE aday_id='a0000005'").fetchone()
    assert kayit["durum"] == "bulundu" and kayit["parca_id"] == 5


def test_medya_yanlis_sanatciyi_reddeder(kum):
    """Yanlış albümün kapağını göstermek, hiç göstermemekten kötü."""
    from python.medya import medya_coz
    istemci = _SahteDeezer({"search/album": {"data": [
        {"id": 1, "title": "Truth", "artist": {"name": "Başka Grup"}, "cover_xl": "https://c/yanlis.jpg"}]}})
    m = medya_coz(kum, {"aday_id": "a0000006", "artist": "T-Square", "title": "Truth"},
                  istemci=istemci)
    assert m["kapak"] is None
    assert kum.execute("SELECT durum FROM medya WHERE aday_id='a0000006'").fetchone()[0] == "yok"


def test_medya_ikinci_cagrida_tablodan(kum):
    from python.medya import medya_coz
    istemci = _SahteDeezer({
        "search/album": {"data": [{"id": 3, "title": "Truth", "artist": {"name": "T-Square"},
                                   "cover_xl": "https://c/t.jpg"}]},
        "album/3/tracks": {"data": [{"id": 30, "title": "Truth", "preview": "https://p/30", "rank": 9},
                                    {"id": 31, "title": "Intro", "preview": "https://p/31", "rank": 1}]},
        "track/30": {"preview": "https://p/30-taze"},
    })
    aday = {"aday_id": "a0000006", "artist": "T-Square", "title": "Truth"}
    ilk = medya_coz(kum, aday, istemci=istemci)
    assert ilk["parca_id"] == 30, "albümün en popüler parçası çalınmalı"
    istemci.cagrilar.clear()
    ikinci = medya_coz(kum, aday, istemci=istemci)
    assert istemci.cagrilar == ["track/30"], "ikinci çağrı yalnız taze önizleme ister"
    assert ikinci["onizleme"] == "https://p/30-taze"


# --------------------------------------------------------------------------- #
# Dil
# --------------------------------------------------------------------------- #

def test_dil_secimi():
    assert istekten_dil("en", "tr-TR") == "en"
    assert istekten_dil(None, "tr-TR,tr;q=0.9") == "tr"
    assert istekten_dil(None, "de-DE,de;q=0.9") == "en"
    assert istekten_dil("fr", None) == "tr"


def test_sayi_ve_yuzde_dile_gore():
    assert sayi(0.53) == "0,53" and yuzde(0.25) == "%25"
    belirtec = AKTIF_DIL.set("en")
    try:
        assert sayi(0.53) == "0.53" and yuzde(0.25) == "25%"
        assert bas_harf_buyuk("insan") == "Insan"
    finally:
        AKTIF_DIL.reset(belirtec)
    assert bas_harf_buyuk("insan") == "İnsan" and bas_harf_buyuk("ızgara") == "Izgara"


def test_yer_tutucu_benzersiz_ve_kacirilmis():
    from web.yer_tutucu import yer_tutucu_svg
    a, b = str(yer_tutucu_svg("<Guns & Roses>")), str(yer_tutucu_svg("<Guns & Roses>"))
    assert "<Guns" not in a and "&lt;Guns" in a
    kimlik = lambda s: s.split('id="yt-')[1].split('"')[0]  # noqa: E731
    assert kimlik(a) != kimlik(b), "aynı sayfada iki kez basılan kapak kimlik çakıştırmamalı"


# --------------------------------------------------------------------------- #
# Koruma: gölge tablo olayı tekrar etmesin
# --------------------------------------------------------------------------- #

def test_baglan_kullanici_klasorunu_kok_disinda_reddeder(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "KULLANICI_KOK", tmp_path / "baska" / "kullanici")
    hedef = tmp_path / "gercek" / "kullanici" / "1.sqlite"
    hedef.parent.mkdir(parents=True)
    with pytest.raises(ValueError):
        D.baglan(hedef)
    assert not hedef.exists(), "reddedilen yola dosya bile açılmamalı"


def test_oturum_her_istekte_yazmaz(tmp_path, monkeypatch):
    from python import hesap
    monkeypatch.setattr(D, "VARSAYILAN_ORTAK", tmp_path / "ortak.sqlite")
    conn = D.baglan_ortak()
    kid = hesap.kullanici_olustur(conn, "T", eposta="t@t.t", parola="parola123")
    jeton = hesap.oturum_ac(conn, kid)
    once = conn.total_changes
    assert hesap.oturum_coz(conn, jeton) == kid
    assert conn.total_changes == once, "10 dakika dolmadan son_gorulme yazılmamalı"
    conn.close()


# --------------------------------------------------------------------------- #
# Web
# --------------------------------------------------------------------------- #

def _istemci(tmp):
    """Oturumlu istemci + tohumlanmış veri (test_web._oturumlu_istemci gibi)."""
    from starlette.testclient import TestClient
    from python.hesap import CEREZ_ADI, kullanici_olustur, oturum_ac

    kok = Path(tmp)
    D.KULLANICI_KOK = kok / "kullanici"
    D.VARSAYILAN_ORTAK = kok / "ortak.sqlite"
    ortak = D.baglan_ortak()
    kid = kullanici_olustur(ortak, "Test", eposta="k@k.k", parola="parola123")
    jeton = oturum_ac(ortak, kid)
    ortak.close()
    conn = D.baglan_kullanici(kid)
    with conn:
        conn.execute("INSERT INTO albums (album_id, artist, title) VALUES ('k2', 'Meshuggah', 'Obzen')")
        conn.execute("INSERT INTO clusters (kume_id, calisma_id, kullanici_adi, stabil_mi) VALUES (0, ?, 'metal', 1)", (CALISMA,))
        conn.execute(
            """INSERT INTO adaylar (aday_id, calisma_id, eksen, strateji, artist, title, skor, gerekce, dayanak, birim)
               VALUES ('a0000001', ?, 0, 'melez', 'Car Bomb', 'Hela', 0.9, '', ?, 'album')""",
            (CALISMA, json.dumps({"pmi": 0.6, "birlikte_liste": 6, "kaynak_sanatcilar": ["meshuggah"]})))
    conn.close()
    from web import sunucu
    sunucu._onbellekleri_bosalt()
    istemci = TestClient(sunucu.uygulama)
    istemci.cookies.set(CEREZ_ADI, jeton)
    return istemci


def test_kesfet_akisi_uctan_uca():
    with tempfile.TemporaryDirectory() as tmp:
        c = _istemci(tmp)
        assert c.get("/kesfet").status_code == 200
        d = c.get("/api/kesfet/deste").json()
        assert [k["artist"] for k in d["kartlar"]] == ["Car Bomb"]
        assert "yer_tutucu" in d["kartlar"][0] and "<svg" in d["kartlar"][0]["yer_tutucu"]
        v = c.post("/api/kesfet/karar", json={"aday_id": "a0000001", "calisma_id": CALISMA,
                                              "karar": "begendim"}).json()
        assert v["liste"] == 1 and v["bugun"]["begendim"] == 1
        assert c.get("/api/kesfet/deste").json()["kartlar"] == []
        assert "Car Bomb" in c.get("/listem").text
        c.post("/api/kesfet/geri-al", json={"aday_id": "a0000001", "calisma_id": CALISMA})
        assert c.get("/api/kesfet/deste").json()["kartlar"][0]["artist"] == "Car Bomb"


def test_api_girdileri_dogrulanir():
    with tempfile.TemporaryDirectory() as tmp:
        c = _istemci(tmp)
        assert c.get("/api/medya/../../etc").status_code in (400, 404)
        assert c.get("/api/medya/ZZZ").status_code == 400
        assert c.post("/api/kesfet/karar", json={"aday_id": "a0000001", "karar": "x"}).status_code == 400
        assert c.post("/api/liste/durum", json={"aday_id": "a0000001", "durum": "x"}).status_code == 400
        assert c.get("/listem/disa-aktar/exe").status_code == 404


def test_dil_degistirme_ve_acik_yonlendirme_yok():
    with tempfile.TemporaryDirectory() as tmp:
        c = _istemci(tmp)
        y = c.get("/dil/en?geri=/kesfet", follow_redirects=False)
        assert y.headers["location"] == "/kesfet" and "kesif_dil=en" in y.headers["set-cookie"]
        y = c.get("/dil/en?geri=//kotu.example.com", follow_redirects=False)
        assert y.headers["location"] == "/", "başka siteye yönlendirmemeli"
        sayfa = c.get("/kesfet").text        # /dil/en çerezi bıraktı
        assert '<html lang="en">' in sayfa and "Discover" in sayfa
        c.get("/dil/tr?geri=/kesfet")
        assert '<html lang="tr">' in c.get("/kesfet").text


def test_butun_sayfalar_iki_dilde_acilir():
    with tempfile.TemporaryDirectory() as tmp:
        c = _istemci(tmp)
        for dil in ("tr", "en"):
            c.get(f"/dil/{dil}")
            for yol in ("/kesfet", "/listem", "/oneriler", "/profil", "/ogrenme",
                        "/muzisyenler", "/kumeler", "/veri", "/eslestirme",
                        "/etiketler", "/ses-kumeleri", "/sozluk"):
                y = c.get(yol)
                assert y.status_code == 200, f"{dil} {yol} → {y.status_code}"


def test_guvenlik_basliklari():
    with tempfile.TemporaryDirectory() as tmp:
        y = _istemci(tmp).get("/kesfet")
        assert y.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in y.headers["content-security-policy"]
        assert y.headers["x-frame-options"] == "DENY"


def test_api_oturumsuz_401_doner():
    """Fetch çağrısı giriş sayfasının HTML'ini JSON sanmasın."""
    from starlette.testclient import TestClient
    from web.sunucu import uygulama
    y = TestClient(uygulama).get("/api/kesfet/deste", follow_redirects=False)
    assert y.status_code == 401


def test_albumu_bulunamayan_aday_sanatci_fotografiyla_gelir():
    """Albüm Deezer'da yoksa kart gri kalmasın: sanatçı fotoğrafı + çalınabilir
    parça (yedek). Kapak BOŞ kalır — başka albümün kapağı yanlış olurdu.
    Deezer'ın fotoğrafsız sanatçı silueti görsel sayılmaz."""
    from python import medya as M

    class _Sahte:
        def get_json(self, yol, params=None, *, yenile=False):
            if yol == "search/album":
                return {"data": []}
            if yol == "search/artist":
                return {"data": [{"id": 9, "name": "Car Bomb",
                                  "picture_xl": "https://e-cdns-images.dzcdn.net/images/artist/abc/1000x1000.jpg"}]}
            if yol == "artist/9/top":
                return {"data": [{"id": 5, "title": "Lights Out", "preview": "https://x/p.mp3"}]}
            return None

    m = M.albumden(_Sahte(), "Car Bomb", "Olmayan Albüm")
    assert m.kapak is None and m.sanatci_gorsel.endswith("1000x1000.jpg")
    assert m.parca_id == 5 and m.yedek == 1 and m.bulundu
    assert M._gercek_gorsel("https://e-cdns-images.dzcdn.net/images/artist//1000x1000.jpg") is None


# --------------------------------------------------------------------------- #
# Müzisyene göre deste (2026-09-28)
# --------------------------------------------------------------------------- #

def _muzisyen_kurulumu(conn):
    """Bir hedef davulcu, dört kütüphane davulcusu ve dört aday. Adaylardan
    ikisi hedefe çok benziyor, biri orta, biri tam tersi."""
    import pandas as pd
    from python.muzisyen import ROL_SUTUNLARI

    sut = [s for s in ROL_SUTUNLARI["drums"]]
    rng = np.random.default_rng(3)
    temel = rng.normal(size=len(sut))
    kisiler = {"duplantier": temel, **{f"k{i}": rng.normal(size=len(sut)) for i in range(4)}}
    profiller = pd.DataFrame(kisiler, index=sut).T
    profiller["kisi_adi"] = ["Mario Duplantier", "A", "B", "C", "D"]
    adaylar = {"b0000001": temel + 0.05, "b0000002": temel * 0.9 + 0.1,
               "b0000003": temel * 0.3 + rng.normal(size=len(sut)), "b0000004": -temel}
    with conn:
        for i, (aid, v) in enumerate(adaylar.items()):
            conn.execute(
                f"INSERT INTO stem_profili (album_id, tur, stem, {','.join(sut)}) "
                f"VALUES (?, 'aday', 'drums', {','.join('?' * len(sut))})", (aid, *map(float, v)))
            conn.execute(
                """INSERT INTO adaylar (aday_id, calisma_id, eksen, strateji, artist, title,
                   skor, gerekce, dayanak, birim) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (aid, CALISMA, 0, "melez", f"Grup {i}", f"Albüm {i}", 0.1, "", "{}", "album"))
    return profiller


import numpy as np  # noqa: E402


def test_muzisyen_destesi_esigin_altini_gostermez(kum):
    profiller = _muzisyen_kurulumu(kum)
    d = kesif.muzisyen_destesi(kum, profiller, "duplantier", "drums", adet=10)
    sanatcilar = [k["artist"] for k in d["kartlar"]]
    assert sanatcilar[:2] == ["Grup 0", "Grup 1"], sanatcilar
    assert "Grup 3" not in sanatcilar                  # tam tersi çalan asla
    assert all(k["benzerlik"] >= kesif.MUZISYEN_ESIGI for k in d["kartlar"])
    assert d["bitis"] == "esik" and d["kalan"] == 0
    assert "Mario Duplantier" in d["kartlar"][0]["gerekce"]
    assert d["kartlar"][0]["calisma_id"] == CALISMA


def test_muzisyen_destesi_karari_kaydeder_ve_tekrar_gostermez(kum):
    profiller = _muzisyen_kurulumu(kum)
    ilk = kesif.muzisyen_destesi(kum, profiller, "duplantier", "drums", adet=1)
    assert ilk["kalan"] >= 1 and ilk["bitis"] is None
    kart = ilk["kartlar"][0]
    kesif.karar_kaydet(kum, kart["calisma_id"], kart["aday_id"], "begendim")
    sonra = kesif.muzisyen_destesi(kum, profiller, "duplantier", "drums", adet=10)
    assert kart["artist"] not in [k["artist"] for k in sonra["kartlar"]]


def test_muzisyen_profili_yoksa_bitis_nedeni_soylenir(kum):
    import pandas as pd
    d = kesif.muzisyen_destesi(kum, pd.DataFrame(), "yok", "drums")
    assert d["kartlar"] == [] and d["bitis"] == "profil_yok"
