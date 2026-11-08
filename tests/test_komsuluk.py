"""Komşuluk yolları (2026-11-07): kadro grafiği, Deezer benzerleri, tohum birleşimi.

Ağsız: sahte istemciler. Cynic örneği gerçek MusicBrainz yapısını taklit ediyor
(grup açısından üyeler «backward», kişi açısından grupları «forward»).
"""

from python.discover import komsuluk as K


def _uye(mbid, ad, yon, tur="member of band", ens=()):
    return {"type": tur, "direction": yon, "artist": {"id": mbid, "name": ad},
            "attributes": list(ens)}


class SahteMB:
    def __init__(self):
        self.veri = {
            "artist": {"artists": [{"id": "cynic", "name": "Cynic", "sort-name": "Cynic"}]},
            "artist/cynic": {"type": "Group", "relations": [
                _uye("malone", "Sean Malone", "backward", ens=["bass guitar"]),
                _uye("reinert", "Sean Reinert", "backward", ens=["drums (drum set)", "original"]),
                _uye("tur", "Turne Gitaristi", "backward", tur="supporting musician")]},
            "artist/malone": {"type": "Person", "relations": [
                _uye("cynic", "Cynic", "forward"), _uye("gk", "Gordian Knot", "forward"),
                _uye("aghora", "Aghora", "forward")]},
            "artist/reinert": {"type": "Person", "relations": [
                _uye("cynic", "Cynic", "forward"), _uye("aghora", "Aghora", "forward"),
                _uye("aeon", "Aeon Spoke", "forward")]},
            "artist/tur": {"type": "Person", "relations": [_uye("baska", "Başka Grup", "forward")]},
        }

    def get_json(self, yol, params=None, **_):
        return self.veri.get(yol, {})


def test_kadro_iki_uyeli_grup_one():
    sira = K.kadro_komsulari(SahteMB(), "Cynic")
    adlar = [k["ad"] for k in sira]
    assert "Cynic" not in adlar                       # tohum kendisi aday değil
    assert adlar[0] == "Aghora"                       # iki üyesi ortak
    aghora = sira[0]
    assert aghora["skor"] == 2.0 and {k for k, _ in aghora["kisiler"]} == {"Sean Malone", "Sean Reinert"}
    skor = {k["ad"]: k["skor"] for k in sira}
    assert skor["Gordian Knot"] == 1.0 and skor["Başka Grup"] == 0.5   # turne bağı yarım
    assert skor["Sean Malone"] == 0.5                # üyenin kendisi (solo) zayıf aday


class SahteDZ:
    def get_json(self, yol, params=None, **_):
        if yol == "search/artist":
            return {"data": [{"id": 1, "name": "Tool Shed", "nb_fan": 9},
                             {"id": 2, "name": "TOOL", "nb_fan": 5000},
                             {"id": 3, "name": "Tool", "nb_fan": 10}]}
        if yol == "artist/2/related":
            return {"data": [{"name": "A Perfect Circle", "nb_fan": 1}, {"name": "Puscifer"}]}
        return {}


def test_deezer_tam_ad_ve_en_cok_hayran():
    benzer = K.deezer_benzer(SahteDZ(), "Tool")
    assert [b["ad"] for b in benzer] == ["A Perfect Circle", "Puscifer"]
    assert benzer[0]["sira"] == 1


def test_tohumlardan_sira_ortak_komsu_one_ve_haric():
    komsular = {"a": [{"ad": "X"}, {"ad": "Y"}, {"ad": "Sahip"}],
                "b": [{"ad": "Y"}, {"ad": "Z"}]}
    sira = K.tohumlardan_sira(komsular, haric={"sahip"})
    assert sira[0] == "y"                            # iki tohumun ortak komşusu
    assert "sahip" not in sira and set(sira) == {"x", "y", "z"}


def test_komsular_topla_hata_bos_liste():
    class Bozuk:
        def get_json(self, *a, **k):
            raise RuntimeError("503")
    sonuc = K.komsular_topla(["Cynic"], dz=Bozuk(), mb=Bozuk(), lb=Bozuk())
    assert sonuc == {"deezer_benzer": {"cynic": []}, "listenbrainz": {"cynic": []},
                     "kadro": {"cynic": []}}
