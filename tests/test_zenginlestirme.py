"""Zenginleştirme testleri — OKUBENI.md 1. öncelik (rol normalizasyonu) ve
3. öncelik (önbellek) merkezde. Ağa çıkılmaz: HTTP katmanı sahte yanıtla değiştirilir.

    pytest tests/test_zenginlestirme.py
    python tests/test_zenginlestirme.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.db import baglan
from python.enrich.etiketler import (
    discogs_etiketleri,
    etiket_normalize,
    mb_etiketleri,
    normalize_agirliklar,
)
from python.enrich.krediler import (
    discogs_kredileri,
    discogs_kunye,
    kredileri_yaz,
    mb_kredileri,
    release_sec,
)
from python.enrich.mbid_eslestir import Aday, adaylari_coz, karar_ver
from python.enrich.rol_eslemesi import KANONIK_ROLLER, rol_normalize, rollere_ayir
from python.enrich.ses_ozellikleri import ParcaOzellik, album_ozeti
from python.onbellek import AgYok, ApiIstemci, IstekBasarisiz


# --------------------------------------------------------------------------- #
# 1. Rol normalizasyonu (OKUBENI #1)
# --------------------------------------------------------------------------- #

def test_discogs_varyantlari_tek_role_iner():
    for ham in ("Drums", "drums", "Drums [Additional]", "Drum Kit", "Drums 2",
                "Batterie", "Acoustic Drums", "Drums*"):
        assert rollere_ayir(ham).roller == ("drums",), ham


def test_cok_rollu_dize_ayrilir():
    assert rollere_ayir("Bass, Backing Vocals").roller == ("backing_vocals", "bass")
    assert rollere_ayir("Written-By, Producer").roller == ("producer", "songwriter")
    assert rollere_ayir("Guitar / Vocals").roller == ("guitar", "vocals")
    # Nitelik içindeki virgül ayırıcı sanılmamalı.
    assert rollere_ayir("Guitar [Rhythm, Lead]").roller == ("guitar",)


def test_ozgul_rol_genel_role_yenilmez():
    assert rollere_ayir("Bass Guitar").roller == ("bass",)      # guitar değil
    assert rollere_ayir("Drum Programming").roller == ("programming",)  # drums değil
    assert rollere_ayir("Backing Vocals").roller == ("backing_vocals",)  # vocals değil


def test_muzikal_olmayan_roller_atilir_ama_bilinmeyen_sayilmaz():
    for ham in ("Artwork", "Design", "Photography", "Executive Producer", "Management"):
        ayrim = rollere_ayir(ham)
        assert ayrim.roller == (), ham
        assert ayrim.bilinmeyen == (), ham


def test_bilinmeyen_rol_sessizce_yutulmaz():
    ayrim = rollere_ayir("Zither")
    assert ayrim.roller == ()
    assert ayrim.bilinmeyen == ("zither",)


def test_uretilen_roller_kanonik_kumede():
    ornekler = [
        "Electric Guitar", "Hammond Organ", "Tenor Saxophone", "Mixed By",
        "Mastered By", "Conductor", "Bağlama", "Minimoog", "Assistant", "Effects",
    ]
    for ham in ornekler:
        for rol in rollere_ayir(ham).roller:
            assert rol in KANONIK_ROLLER, f"{ham} → {rol}"


def test_rol_normalize_tek_deger():
    assert rol_normalize("drums (drum set)") == "drums"
    assert rol_normalize(None) is None


# --------------------------------------------------------------------------- #
# 2. Önbellek ve rate limit (OKUBENI #3)
# --------------------------------------------------------------------------- #

class SahteYanit:
    def __init__(self, govde, durum=200):
        self._govde = govde
        self.status_code = durum
        self.ok = durum < 400
        self.headers: dict[str, str] = {}
        self.text = str(govde)

    def json(self):
        return self._govde


class SahteOturum:
    def __init__(self, govde=None, durum=200):
        self.govde = govde if govde is not None else {"tamam": True}
        self.durum = durum
        self.cagri = 0
        self.headers: dict[str, str] = {}

    def get(self, url, params=None, timeout=None):
        self.cagri += 1
        return SahteYanit(self.govde, self.durum)


def _istemci(kok: Path, oturum: SahteOturum) -> ApiIstemci:
    istemci = ApiIstemci(
        servis="test", temel_url="https://ornek.test", istek_araligi=0.0, onbellek_kok=kok
    )
    istemci._oturum = oturum
    return istemci


def test_ayni_sorgu_iki_kez_aga_gitmez():
    with tempfile.TemporaryDirectory() as gecici:
        kok = Path(gecici)
        oturum = SahteOturum({"deger": 42})
        istemci = _istemci(kok, oturum)

        assert istemci.get_json("kaynak", {"q": "x"}) == {"deger": 42}
        assert istemci.get_json("kaynak", {"q": "x"}) == {"deger": 42}
        assert oturum.cagri == 1                      # ikincisi önbellekten
        assert istemci.sayac.isabet == 1
        assert istemci.sayac.istek == 1

        # Farklı parametre = farklı anahtar.
        istemci.get_json("kaynak", {"q": "y"})
        assert oturum.cagri == 2


def test_bos_sonuc_da_onbelleklenir():
    with tempfile.TemporaryDirectory() as gecici:
        oturum = SahteOturum(durum=404)
        istemci = _istemci(Path(gecici), oturum)
        assert istemci.get_json("yok") is None
        assert istemci.get_json("yok") is None
        assert oturum.cagri == 1


def test_cevrimdisi_onbellegi_kullanir_yenisini_reddeder():
    with tempfile.TemporaryDirectory() as gecici:
        kok = Path(gecici)
        oturum = SahteOturum({"deger": 1})
        _istemci(kok, oturum).get_json("kaynak", {"q": "x"})

        cevrimdisi = _istemci(kok, SahteOturum())
        cevrimdisi.cevrimdisi = True
        assert cevrimdisi.get_json("kaynak", {"q": "x"}) == {"deger": 1}
        try:
            cevrimdisi.get_json("kaynak", {"q": "baska"})
        except AgYok:
            pass
        else:
            raise AssertionError("çevrimdışıyken yeni istek AgYok vermeliydi")


def test_kalici_hata_yukselir():
    with tempfile.TemporaryDirectory() as gecici:
        istemci = _istemci(Path(gecici), SahteOturum(durum=403))
        try:
            istemci.get_json("gizli")
        except IstekBasarisiz:
            pass
        else:
            raise AssertionError("403 IstekBasarisiz vermeliydi")


# --------------------------------------------------------------------------- #
# 3. MBID eşleştirme kararı
# --------------------------------------------------------------------------- #

def _aday(baslik, sanatci="Rush", yil=1981, skor=100, mbid="m1"):
    return Aday(mbid=mbid, artist=sanatci, title=baslik, yil=yil, skor=skor)


def test_tek_tam_eslesme_kesin():
    karar = karar_ver("Rush", "Moving Pictures", 1981, [_aday("Moving Pictures")])
    assert karar.durum == "kesin"
    assert karar.aday.mbid == "m1"


def test_yil_farki_tek_adayda_engel_degil():
    # Etiket yeniden basımın yılını taşıyor; rakip aday yoksa kabul edilir.
    karar = karar_ver("Şebnem Ferah", "Perdeler", 2005, [_aday("Perdeler", "Şebnem Ferah", 2001)])
    assert karar.durum == "kesin"
    assert "yıl farkı" in karar.not_


def test_iki_tam_eslesmede_yil_ayirir():
    adaylar = [
        _aday("Moving Pictures", yil=1981, mbid="studyo"),
        _aday("Moving Pictures", yil=2010, mbid="canli"),
    ]
    assert karar_ver("Rush", "Moving Pictures", 1981, adaylar).aday.mbid == "studyo"
    # Yıl bilinmiyorsa ayrım yapılamaz → insana sorulur.
    assert karar_ver("Rush", "Moving Pictures", None, adaylar).durum == "supheli"


def test_ayni_adli_album_ve_single_ayrilir():
    """MB'de aynı ad + aynı yıl: biri albüm, biri single."""
    adaylar = [
        Aday(mbid="alb", artist="Duran Duran", title="Notorious", yil=1986,
             skor=100, tur="Album"),
        Aday(mbid="sgl", artist="Duran Duran", title="Notorious", yil=1986,
             skor=100, tur="Single"),
    ]
    karar = karar_ver("Duran Duran", "Notorious", 1986, adaylar, 10)
    assert karar.durum == "kesin" and karar.aday.mbid == "alb"


def test_az_parca_single_kanitlamaz():
    """Kullanıcıda albümden tek parça olması, yayının single olduğunu göstermez."""
    adaylar = [
        Aday(mbid="alb", artist="Deftones", title="Diamond Eyes", yil=2010,
             skor=100, tur="Album"),
        Aday(mbid="sgl", artist="Deftones", title="Diamond Eyes", yil=2010,
             skor=100, tur="Single"),
    ]
    karar = karar_ver("Deftones", "Diamond Eyes (Deluxe)", 2010, adaylar, 1)
    assert karar.durum == "supheli", "az parçada tür çıkarımı yapılmamalı"


def test_ligatur_ve_ad_sirasi_eslesir():
    from python.metin import ayni_kisi_mi, normalize_esleme
    assert normalize_esleme("Crèvecœur (EP.I)") == normalize_esleme("Crèvecoeur (EP.I)")
    assert normalize_esleme("Ænima") == "aenima"
    assert ayni_kisi_mi("Borlai Gergő", "Gergő Borlai")
    assert ayni_kisi_mi("DANGERDOOM feat. Talib Kweli", "Dangerdoom")
    # Kapsama eşleşme sayılmaz: farklı varlıklar.
    assert not ayni_kisi_mi("Jeff Beck", "Jeff Beck Group")


def test_kimlik_normalizasyonu_dondurulmus():
    """album_id normalizasyonu eşleştirme kurallarından etkilenmemeli."""
    from python.metin import album_kimligi, normalize
    assert normalize("Ænima") == "nima"          # ligatür AÇILMAZ (kimlik)
    assert album_kimligi("TOOL", "Ænima", 1996) == album_kimligi("TOOL", "Ænima", 1996)


def test_normalize_baslik_tam_eslesme_sayilir():
    karar = karar_ver("Pink Floyd", "Meddle (2011 Remaster)", 1971,
                      [_aday("Meddle", "Pink Floyd", 1971)])
    assert karar.durum == "kesin"


def test_zayif_aday_supheli_veya_yok():
    assert karar_ver("Rush", "Hemispheres", 1978, []).durum == "yok"
    assert karar_ver("Rush", "Hemispheres", 1978, [_aday("Permanent Waves")]).durum == "supheli"
    # Skoru düşük aday hiç sayılmaz.
    assert karar_ver("Rush", "Hemispheres", 1978, [_aday("Hemispheres", skor=40)]).durum == "yok"


def test_adaylari_coz():
    govde = {
        "release-groups": [
            {
                "id": "abc",
                "title": "Hemispheres",
                "score": 100,
                "first-release-date": "1978-10-29",
                "artist-credit": [{"artist": {"name": "Rush"}}],
                "primary-type": "Album",
            }
        ]
    }
    (aday,) = adaylari_coz(govde)
    assert (aday.mbid, aday.artist, aday.yil, aday.skor) == ("abc", "Rush", 1978, 100)
    assert adaylari_coz(None) == []


# --------------------------------------------------------------------------- #
# 4. Kredi çıkarımı
# --------------------------------------------------------------------------- #

MB_RELEASE = {
    "relations": [
        {"type": "producer", "artist": {"id": "p1", "name": "Terry Brown"}},
        {"type": "mix", "artist": {"id": "p1", "name": "Terry Brown"}},
        {"type": "artwork", "artist": {"id": "p9", "name": "Hugh Syme"}},
    ],
    "media": [
        {
            "tracks": [
                {
                    "recording": {
                        "relations": [
                            {"type": "instrument", "attributes": ["drums"],
                             "artist": {"id": "np", "name": "Neil Peart"}},
                            {"type": "instrument", "attributes": ["bass guitar"],
                             "artist": {"id": "gl", "name": "Geddy Lee"}},
                        ]
                    }
                },
                {
                    "recording": {
                        "relations": [
                            {"type": "instrument", "attributes": ["drums"],
                             "artist": {"id": "np", "name": "Neil Peart"}},
                            {"type": "instrument", "attributes": ["zither"],
                             "artist": {"id": "zz", "name": "Kim Mitchell"}},
                        ]
                    }
                },
            ]
        }
    ],
}


def test_mb_kredileri_iki_katmandan_toplanir():
    krediler, bilinmeyen = mb_kredileri(MB_RELEASE)
    ikili = {(k.person_name, k.role) for k in krediler}
    assert ("Neil Peart", "drums") in ikili
    assert ("Geddy Lee", "bass") in ikili          # "bass guitar" → bass
    assert ("Terry Brown", "producer") in ikili
    assert ("Terry Brown", "mix") in ikili
    assert not any(ad == "Hugh Syme" for ad, _ in ikili)  # artwork atıldı
    assert "zither" in bilinmeyen
    # Aynı kredi iki parçada geçse de tek satır.
    assert sum(1 for k in krediler if k.person_name == "Neil Peart") == 1
    assert all(k.kaynak == "musicbrainz" for k in krediler)


def test_mb_kredileri_bos_girdi():
    assert mb_kredileri(None) == ([], [])
    assert mb_kredileri({}) == ([], [])


def test_release_sec_resmi_ve_en_eskiyi_alir():
    govde = {
        "releases": [
            {"id": "r2", "status": "Official", "date": "1997-05-01"},
            {"id": "r1", "status": "Official", "date": "1981-02-12"},
            {"id": "r0", "status": "Bootleg", "date": "1980-01-01"},
        ]
    }
    assert release_sec(govde) == "r1"
    assert release_sec({"releases": []}) is None
    assert release_sec(None) is None


DISCOGS_RELEASE = {
    "labels": [{"name": "Anthem"}],
    "country": "Canada",
    "year": 1981,
    "extraartists": [
        {"id": 123, "name": "Terry Brown", "role": "Producer, Engineer"},
        {"id": 456, "name": "Hugh Syme (2)", "role": "Artwork"},
    ],
    "tracklist": [
        {"extraartists": [{"id": 789, "name": "Neil Peart", "role": "Drums, Percussion"}]}
    ],
}


def test_discogs_kredileri():
    krediler, _ = discogs_kredileri(DISCOGS_RELEASE)
    ikili = {(k.person_name, k.role) for k in krediler}
    assert ikili == {
        ("Terry Brown", "producer"),
        ("Terry Brown", "engineer"),
        ("Neil Peart", "drums"),
        ("Neil Peart", "percussion"),
    }
    assert all(k.person_id.startswith("discogs:") for k in krediler)


class YonlendirenOturum:
    """URL'ye göre farklı gövde döndüren sahte oturum."""

    def __init__(self, yollar: dict[str, dict]):
        self.yollar = yollar
        self.cagrilar: list[tuple[str, dict]] = []
        self.headers: dict[str, str] = {}

    def get(self, url, params=None, timeout=None):
        self.cagrilar.append((url, dict(params or {})))
        for parca, govde in self.yollar.items():
            if parca in url:
                return SahteYanit(govde)
        return SahteYanit({}, 404)


def test_discogs_release_bul_dogru_adayi_secer():
    from python.enrich.krediler import discogs_release_bul

    oturum = YonlendirenOturum(
        {
            "database/search": {
                "results": [
                    {"id": 1, "title": "Rush - Moving Pictures (Live)", "year": "2011"},
                    {"id": 2, "title": "Rush - Moving Pictures", "year": "1981"},
                ]
            },
            "releases/2": DISCOGS_RELEASE,
        }
    )
    with tempfile.TemporaryDirectory() as gecici:
        istemci = _istemci(Path(gecici), oturum)
        release = discogs_release_bul(istemci, "Rush", "Moving Pictures", 1981)
    assert release == DISCOGS_RELEASE  # başlığı tam tutan aday seçildi
    assert any("releases/2" in url for url, _ in oturum.cagrilar)


def test_discogs_release_bul_yilsiz_tekrar_dener():
    from python.enrich.krediler import discogs_release_bul

    class BosSonraDolu(YonlendirenOturum):
        def get(self, url, params=None, timeout=None):
            self.cagrilar.append((url, dict(params or {})))
            if "database/search" in url:
                # Yıl filtresi varken boş, yılsız sorguda dolu.
                if "year" in (params or {}):
                    return SahteYanit({"results": []})
                return SahteYanit({"results": [{"id": 2, "title": "Rush - Moving Pictures"}]})
            return SahteYanit(DISCOGS_RELEASE)

    oturum = BosSonraDolu({})
    with tempfile.TemporaryDirectory() as gecici:
        istemci = _istemci(Path(gecici), oturum)
        release = discogs_release_bul(istemci, "Rush", "Moving Pictures", 1981)
    assert release == DISCOGS_RELEASE
    assert sum(1 for url, _ in oturum.cagrilar if "database/search" in url) == 2


def test_discogs_kunye():
    kunye = discogs_kunye(DISCOGS_RELEASE)
    assert kunye == {"label": "Anthem", "country": "Canada", "year": 1981}


def test_kredi_yazimi_tekrarda_cogalmaz():
    conn = baglan(":memory:")
    with conn:
        conn.execute(
            "INSERT INTO albums (album_id, artist, title) VALUES ('a1', 'Rush', 'Moving Pictures')"
        )
    krediler, _ = mb_kredileri(MB_RELEASE)
    kredileri_yaz(conn, "a1", krediler)
    ilk = conn.execute("SELECT COUNT(*) FROM credits").fetchone()[0]
    kredileri_yaz(conn, "a1", krediler)
    assert conn.execute("SELECT COUNT(*) FROM credits").fetchone()[0] == ilk
    assert ilk == len(krediler)


# --------------------------------------------------------------------------- #
# 5. Etiketler
# --------------------------------------------------------------------------- #

def test_etiket_normalize_copu_eler():
    assert etiket_normalize("Progressive Rock") == "progressive rock"
    assert etiket_normalize("Rock & Roll") == "rock and roll"
    for cop in ("seen live", "80s", "1981", "1–4 wochen", "english", "hipgnosis cover", "x"):
        assert etiket_normalize(cop) is None, cop


def test_mb_etiketleri_oy_doyuma_ugrar():
    govde = {
        "tags": [{"name": "progressive rock", "count": 40}, {"name": "rock", "count": 1}],
        "genres": [{"name": "hard rock", "count": 4}],
    }
    agirliklar = mb_etiketleri(govde)
    # 40 oy, 1 oyun 40 katı değil.
    assert agirliklar["progressive rock"] < 8 * agirliklar["rock"]
    assert agirliklar["hard rock"] > agirliklar["rock"]


def test_agirliklar_toplami_bir():
    normalize_edilmis = normalize_agirliklar({"a": 3.0, "b": 1.0})
    assert abs(sum(normalize_edilmis.values()) - 1.0) < 1e-9
    assert normalize_agirliklar({}) == {}


def test_discogs_style_genreden_agir():
    agirliklar = discogs_etiketleri({"genres": ["Rock"], "styles": ["Prog Rock"]})
    assert agirliklar["prog rock"] > agirliklar["rock"]


# --------------------------------------------------------------------------- #
# 6. Ses özniteliği özeti (librosa'sız)
# --------------------------------------------------------------------------- #

def test_album_ozeti_medyan_ve_iqr():
    parcalar = [
        ParcaOzellik(tempo=100, dinamik_aralik=10, nabiz_netligi=8.0, vurus_degiskenligi=0.02, spektral_merkez=2000),
        ParcaOzellik(tempo=120, dinamik_aralik=12, nabiz_netligi=6.0, vurus_degiskenligi=0.04, spektral_merkez=2500),
        ParcaOzellik(tempo=140, dinamik_aralik=14, nabiz_netligi=4.0, vurus_degiskenligi=0.06, spektral_merkez=3000),
    ]
    ozet = album_ozeti(parcalar)
    assert ozet["tempo_medyan"] == 120
    # method="inclusive" ara değer hesaplar: Q1=110, Q3=130.
    assert ozet["tempo_iqr"] == 20
    assert ozet["spektral_merkez"] == 2500
    assert album_ozeti([]) is None


def test_album_ozeti_tek_parca():
    tek = [ParcaOzellik(tempo=95, dinamik_aralik=8, nabiz_netligi=7.0, vurus_degiskenligi=0.03, spektral_merkez=1800)]
    ozet = album_ozeti(tek)
    assert ozet["tempo_medyan"] == 95
    assert ozet["tempo_iqr"] == 0.0  # tek parçada açıklık tanımsız değil, sıfır


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
