"""«Sayılarla sen» ve müzisyen fotoğrafı."""

import pytest

import python.db as D
from python import istatistik as ist
from python import kisi_gorsel as kg
from python.ceviri import olcut_adi, roller_adi


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "KULLANICI_KOK", tmp_path / "kullanici")
    monkeypatch.setattr(D, "VARSAYILAN_ORTAK", tmp_path / "ortak.sqlite")
    c = D.baglan_kullanici(1)
    yield c
    c.close()


def _albumler(conn, kayitlar, calisma="c1"):
    """kayitlar: (sanatçı, yıl, üyelik0, tempo)"""
    with conn:
        for i, (sanatci, yil, u0, tempo) in enumerate(kayitlar):
            aid = f"a{i}"
            conn.execute("INSERT INTO albums (album_id, artist, title, year) VALUES (?,?,?,?)",
                         (aid, sanatci, f"T{i}", yil))
            conn.execute("INSERT INTO memberships VALUES (?,?,?,?)", (aid, 0, u0, calisma))
            conn.execute("INSERT INTO memberships VALUES (?,?,?,?)", (aid, 1, 1 - u0, calisma))
            if tempo:
                conn.execute("INSERT INTO audio_features (album_id, kaynak, tempo_medyan) "
                             "VALUES (?, 'yerel', ?)", (aid, tempo))
        for k in (0, 1):
            conn.execute("INSERT INTO clusters VALUES (?,?,?,?,?)", (k, calisma, f"t{k}", 0.8, 1))


def test_uyelik_netligi_ve_kopru(conn):
    _albumler(conn, [("A", 1990, 0.9, None), ("B", 1991, 0.55, None), ("C", 2001, 0.2, None)])
    t = ist.tarzlar(conn, "c1")
    assert t["net"] == 2 and t["arada"] == 1          # 0.9 ve 0.8 net; 0.55 arada
    assert [k["artist"] for k in t["kopruler"]] == ["B"]
    assert {k["kume"]: k["album"] for k in t["liste"]} == {0: 2, 1: 1}
    assert t["stabil_sayisi"] == 2


def test_zaman_bos_onyillari_sifirla_doldurur(conn):
    _albumler(conn, [("A", 1971, 0.9, None), ("B", 1995, 0.9, None), ("C", 1996, 0.9, None)])
    z = ist.zaman(conn)
    assert z["onyillar"] == [(1970, 1), (1980, 0), (1990, 2)]


def test_cesitlilik_esit_dagilimda_etkin_sayi_sanatci_sayisi(conn):
    _albumler(conn, [(s, 2000, 0.9, None) for s in "ABCD" for _ in range(2)])
    c = ist.cesitlilik(conn)
    assert c["etkin"] == pytest.approx(4) and c["denge"] == pytest.approx(1)


def test_ses_tek_kaynaktan_ve_azsa_yok(conn):
    _albumler(conn, [("A", 2000, 0.9, 100 + i) for i in range(12)])
    with conn:
        conn.execute("UPDATE audio_features SET kaynak = 'onizleme' WHERE album_id IN ('a0', 'a1')")
    s = ist.ses(conn)
    assert s["kaynak"] == "yerel" and s["n"] == 10    # kaynaklar karışmaz (K11)
    with conn:
        conn.execute("DELETE FROM audio_features WHERE album_id > 'a5'")
    assert ist.ses(conn) is None                      # 10'dan az ölçüm


def test_olcut_ve_rol_adlari_okunur():
    assert olcut_adi("tekme_payi") in ("Tekme Payı", "Kick Share")
    assert "_" not in olcut_adi("bilinmeyen_sutun")
    assert "_" not in roller_adi("drums, backing_vocals")


class _Sahte:
    def __init__(self, yanitlar):
        self.yanitlar, self.cagrilar = yanitlar, []

    def get_json(self, yol, params=None, **_):
        self.cagrilar.append(yol)
        return self.yanitlar.get(yol, {})


MBID = "5b11f4ce-a62d-471e-81fc-a69a8278c7da"


def _kredi(conn, ad, kimlik):
    with conn:
        conn.execute("INSERT INTO credits VALUES ('a1', ?, ?, 'drums', 'musicbrainz')", (kimlik, ad))


def test_kisi_gorseli_kimlikle_wikidatadan(conn):
    _kredi(conn, "Neil Peart", MBID)
    mb = _Sahte({f"artist/{MBID}": {"relations": [
        {"type": "wikidata", "url": {"resource": "https://www.wikidata.org/wiki/Q312715"}}]}})
    wd = _Sahte({"wiki/Special:EntityData/Q312715.json": {"entities": {"Q312715": {"claims": {
        "P18": [{"mainsnak": {"datavalue": {"value": "Neil Peart 2004.jpg"}}}]}}}}})
    dz = _Sahte({})
    k = kg.coz(conn, "neil peart", mb=mb, wd=wd, dz=dz)
    assert k["kaynak"] == "wikidata" and "Neil_Peart_2004.jpg" in k["gorsel"]
    assert dz.cagrilar == []
    # İkinci çağrı ağa çıkmaz.
    kg.coz(conn, "neil peart", mb=mb, wd=wd, dz=dz)
    assert len(mb.cagrilar) == 1


def test_deezer_yalniz_tam_ad_esitliginde(conn):
    _kredi(conn, "Matt Cameron", "discogs:1")
    dz = _Sahte({"search/artist": {"data": [
        {"name": "Matt Cameron Band", "picture_big": "https://e-cdns-images.dzcdn.net/images/artist/x/1.jpg"}]}})
    assert kg.coz(conn, "matt cameron", mb=_Sahte({}), wd=_Sahte({}), dz=dz) is None
    assert kg.oku(conn, "matt cameron")["durum"] == "yok"


def test_ag_hatasi_yok_diye_yazilmaz(conn):
    from python.onbellek import AgYok

    class _Kopuk:
        def get_json(self, *a, **k):
            raise AgYok("yok")

    _kredi(conn, "Ian Paice", MBID)
    assert kg.coz(conn, "ian paice", mb=_Kopuk(), wd=_Kopuk(), dz=_Kopuk()) is None
    assert kg.oku(conn, "ian paice") is None


def test_tarz_sagligi_ve_ayrisma(conn):
    _albumler(conn, [("A", 1990, 0.95, None)] * 1 + [("B", 1991, 0.9, None), ("C", 1992, 0.05, None)])
    t = ist.tarzlar(conn, "c1")
    assert t["ayrisma"] > 0.8                           # neredeyse keskin
    assert ist.saglik(0.9, True) == "saglam"
    assert ist.saglik(0.5, True) == "karisik"
    assert ist.saglik(0.9, False) == "oynak"


def test_kopru_ciftleri_sayilir(conn):
    _albumler(conn, [("A", 2000, 0.55, None), ("B", 2000, 0.6, None), ("C", 2000, 0.9, None)])
    t = ist.tarzlar(conn, "c1")
    assert t["ciftler"] == [(0, 1, 2)]


def test_tarz_konumlari_yuzdelik_ve_sira():
    import pandas as pd
    from python.profil import tarz_konumlari

    veri = pd.DataFrame({"album_id": [f"a{i}" for i in range(12)], "stem": "drums",
                         "tempo": list(range(12))})
    U = pd.DataFrame({0: [1.0] * 6 + [0.0] * 6, 1: [0.0] * 6 + [1.0] * 6},
                     index=[f"a{i}" for i in range(12)])
    k = tarz_konumlari(veri, U, {0: "ağır", 1: "hızlı"}, "davul")
    tempo = next(e for e in k if e["sutun"] == "tempo")
    orta = {r["ad"]: r["orta"] for r in tempo["satirlar"]}
    assert orta["ağır"] < 0.5 < orta["hızlı"]
    assert all(0 <= r["q1"] <= r["orta"] <= r["q3"] <= 1 for r in tempo["satirlar"])


def test_grafikler_bos_veride_cokmez():
    from web import grafik
    assert "<svg" in grafik.yigin_cubuk([]).svg
    assert "<svg" in grafik.konum_seridi([], sol="a", sag="b").svg
    svg = grafik.konum_seridi([("çok uzun bir tarz adı burada", 0.5, 0.2, 0.8, "ipucu")],
                              sol="a", sag="b").svg
    assert "…" in svg and "ipucu" in svg


def test_tarz_haritasi_benzer_tarzlari_yakin_koyar():
    import numpy as np
    # 0 ve 1 albümlerini paylaşıyor, 2 ayrı.
    U = np.array([[0.5, 0.5, 0.0]] * 5 + [[0.6, 0.4, 0.0]] * 5 + [[0.0, 0.0, 1.0]] * 5)
    X = ist.tarz_haritasi(U)
    d01 = np.linalg.norm(X[0] - X[1])
    d02 = np.linalg.norm(X[0] - X[2])
    assert d01 < d02


def test_pano_tarz_basina_veri_ve_renk_sirasi(conn):
    _albumler(conn, [("A", 1990, 0.9, 120)] * 1 + [("B", 1991, 0.8, 130), ("C", 2005, 0.1, 90),
                                                  ("D", 2006, 0.2, 95), ("E", 2007, 0.15, 100)])
    p = ist.pano(conn, "c1")
    assert [t["kume"] for t in p["tarzlar"]] == [1, 0]        # büyükten küçüğe
    assert [t["renk"] for t in p["tarzlar"]] == [0, 1]
    assert p["tarzlar"][0]["tempo"][0] == 95
    assert p["onyillar"] == [1990, 2000]
    assert p["sanatci_tarzi"]["A"] == 0


def test_pano_grafikleri_data_tarz_tasir():
    from web import grafik
    tarzlar = [{"kume": 0, "renk": 0, "album": 5, "x": 0.1, "y": 0.2, "onyil": {1990: 3},
                "tempo": (120.0, 110.0, 130.0)},
               {"kume": 1, "renk": 1, "album": 3, "x": 0.9, "y": 0.8, "onyil": {1990: 1},
                "tempo": None}]
    adlar = {0: "metal", 1: "caz"}
    harita = grafik.tarz_haritasi(tarzlar, [(0, 1, 2)], adlar).svg
    assert 'data-tarz="0"' in harita and 'data-tarz="0 1"' in harita
    assert grafik.TARZ_RENKLERI[0] in harita
    assert 'data-tarz="1"' in grafik.onyil_tarz([1990], tarzlar, adlar).svg
    assert "caz" not in grafik.tempo_seridi(tarzlar, adlar, (90, 150)).svg   # tempo yok → satır yok
    assert grafik.tarz_rengi(None) == grafik.DIGER and grafik.tarz_rengi(12) == grafik.DIGER
