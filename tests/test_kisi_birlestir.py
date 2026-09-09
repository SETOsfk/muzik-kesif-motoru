"""Alias birleştirme testleri.

İki risk var ve ikisi de sessizce zarar verir:
1. MusicBrainz'in geniş alias listesinden kütüphanede olmayan adların sızması.
2. Grup aliaslarının kişi grafiğine karışması.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from python.enrich import kisi_birlestir as K
from python.muzisyen import _anahtar

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


class _SahteMB:
    """Alias yanıtlarını taklit eder — ağa çıkmadan mantığı sınamak için."""

    def __init__(self, yanitlar):
        self.yanitlar = yanitlar

    def get_json(self, yol, parametre=None):
        return self.yanitlar.get(yol.split("/")[-1])


def _db(krediler):
    from python.db import baglan

    conn = baglan(":memory:")
    with conn:
        conn.execute(
            "INSERT INTO albums (album_id, artist, title) VALUES ('a1','S','T')"
        )
        conn.executemany(
            "INSERT INTO credits (album_id, person_id, person_name, role, kaynak) "
            "VALUES ('a1',?,?,?,'musicbrainz')",
            krediler,
        )
    return conn


def test_kutuphanede_olmayan_alias_sizmaz():
    """MusicBrainz'in bilmediğimiz bir kişiye dair iddiası yazılmamalı."""
    conn = _db([("mb1", "神保彰", "drums")])   # Akira Jimbo kütüphanede YOK
    mb = _SahteMB({"mb1": {"name": "神保彰", "type": "Person",
                           "aliases": [{"name": "Akira Jimbo"}]}})
    assert K.eslesmeleri_kur(conn, mb, ilerleme=False) == {}


def test_iki_taraf_da_varsa_birlesir():
    conn = _db([("mb1", "神保彰", "drums"), ("dc1", "Akira Jimbo", "drums")])
    mb = _SahteMB({"mb1": {"name": "神保彰", "type": "Person",
                           "aliases": [{"name": "Akira Jimbo"}]}})
    eslesme = K.eslesmeleri_kur(conn, mb, ilerleme=False)
    assert eslesme, "iki taraf da kütüphanede — birleşmeliydi"
    assert set(eslesme.values()) == {"akira jimbo"} or set(eslesme.values()) == {"神保彰"}
    assert len(set(eslesme.values())) == 1, "tek kanonik ad kalmalı"


def test_grup_aliaslari_karismaz():
    """`type=Group` olan sanatçının aliasları kişi grafiğini bozmamalı."""
    conn = _db([("mb1", "Rush", "guitar"), ("dc1", "RUSH", "guitar")])
    mb = _SahteMB({"mb1": {"name": "Rush", "type": "Group",
                           "aliases": [{"name": "RUSH"}]}})
    assert K.eslesmeleri_kur(conn, mb, ilerleme=False) == {}


def test_kanonik_cok_kredili_olan():
    """Az yazım çok yazıma katılmalı — mevcut profillerin çoğu korunsun."""
    from python.db import baglan

    conn = baglan(":memory:")
    with conn:
        conn.executemany(
            "INSERT INTO albums (album_id, artist, title) VALUES (?,'S','T')",
            [("a1",), ("a2",), ("a3",)],
        )
        # "Yaygin Ad" üç albümde, "Nadir Ad" bir albümde
        conn.executemany(
            "INSERT INTO credits (album_id, person_id, person_name, role, kaynak) "
            "VALUES (?,?,?,'drums','musicbrainz')",
            [("a1", "mb1", "Yaygin Ad"), ("a2", "mb1", "Yaygin Ad"),
             ("a3", "dc1", "Nadir Ad")],
        )
    mb = _SahteMB({"mb1": {"name": "Yaygin Ad", "type": "Person",
                           "aliases": [{"name": "Nadir Ad"}]}})
    eslesme = K.eslesmeleri_kur(conn, mb, ilerleme=False)
    assert eslesme == {"nadir ad": "yaygin ad"}, eslesme


def test_esleme_yoksa_davranis_degismez():
    """Tablo boşken anahtar üretimi eskisiyle birebir aynı olmalı."""
    seri = pd.Series(["Neil Peart", "Mario Duplantier"])
    assert list(_anahtar(seri)) == list(_anahtar(seri, {}))
    assert list(_anahtar(seri, None)) == ["neil peart", "mario duplantier"]


def test_esleme_uygulaniyor():
    seri = pd.Series(["Akira Jimbo", "神保彰", "Neil Peart"])
    sonuc = list(_anahtar(seri, {"神保彰": "akira jimbo"}))
    assert sonuc == ["akira jimbo", "akira jimbo", "neil peart"], sonuc


def test_esik_bolunmeyi_gizlememeli():
    """Varsayılan eşik 1 olmalı: bölünme kişinin albümlerini ikiye ayırıyor,
    her yarı ≥2 eşiğinin altında kalıp taramadan düşebiliyordu."""
    import inspect

    imza = inspect.signature(K.hedef_kisiler)
    assert imza.parameters["asgari_album"].default == 1


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
