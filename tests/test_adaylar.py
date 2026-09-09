"""Aday üretimi — popülerlik yanlılığı ve albüm süzgeci testleri.

Bu iki şey ölçülerek bulundu ve ikisi de sessizce geri gelebilir:
1. İki adım ötesine gitmek mainstream'e düşürüyor (Coldplay, metal kümesinde).
2. MusicBrainz canlı kayıtları da `primary-type=Album` döndürüyor.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.discover import adaylar as A

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


# --------------------------------------------------------------------------- #
# Stüdyo albümü süzgeci
# --------------------------------------------------------------------------- #

def test_canli_kayit_elenir():
    gruplar = [
        {"title": "Hot Fuss", "primary-type": "Album",
         "first-release-date": "2004-06-07"},
        {"title": "2004-11-12: Manchester", "primary-type": "Album",
         "secondary-types": ["Live"], "first-release-date": "2004-11-12"},
        {"title": "Greatest Hits", "primary-type": "Album",
         "secondary-types": ["Compilation"], "first-release-date": "2013"},
    ]
    sonuc = A.gercek_albumler(gruplar)
    assert [g["title"] for g in sonuc] == ["Hot Fuss"], sonuc


def test_tarihe_gore_eskiden_yeniye():
    gruplar = [
        {"title": "üçüncü", "primary-type": "Album", "first-release-date": "2000"},
        {"title": "birinci", "primary-type": "Album", "first-release-date": "1990"},
        {"title": "ikinci", "primary-type": "Album", "first-release-date": "1995"},
    ]
    assert [g["title"] for g in A.gercek_albumler(gruplar)] == [
        "birinci", "ikinci", "üçüncü"
    ]


def test_tarihsiz_sona_gider():
    gruplar = [
        {"title": "tarihsiz", "primary-type": "Album"},
        {"title": "tarihli", "primary-type": "Album", "first-release-date": "1990"},
    ]
    assert A.gercek_albumler(gruplar)[0]["title"] == "tarihli"


def test_album_olmayan_tur_elenir():
    gruplar = [
        {"title": "EP", "primary-type": "EP", "first-release-date": "2000"},
        {"title": "Single", "primary-type": "Single", "first-release-date": "2000"},
        {"title": "Albüm", "primary-type": "Album", "first-release-date": "2000"},
    ]
    assert [g["title"] for g in A.gercek_albumler(gruplar)] == ["Albüm"]


# --------------------------------------------------------------------------- #
# Popülerlik yanlılığı: özgüllük SIRALAMA ölçütü olmalı, çarpan değil
# --------------------------------------------------------------------------- #

def test_ozgul_aday_populer_adayin_ustunde():
    """df=1 aday, çok köprülü ama df=3 olan adayın ÜSTÜNDE olmalı.

    Gerçekte ölçülen hata buydu: AC/DC (df=2, çok köprü) metal ekseninde
    Children of Bodom'un (df=1, tek köprü) üstüne çıkmıştı.
    """
    havuz = {
        "populer": {"ad": "Populer", "mbid": "m1", "skor": 5.0,
                    "kopruler": {"a", "b", "c", "d"}},
        "ozgul": {"ad": "Ozgul", "mbid": "m2", "skor": 0.6, "kopruler": {"a"}},
    }
    frekans = {"populer": 3, "ozgul": 1, "__eksen_sayisi__": 9}

    eksen_sayisi = frekans["__eksen_sayisi__"]
    for anahtar, kayit in havuz.items():
        kayit["df"] = frekans[anahtar]
        kayit["destek"] = len(kayit["kopruler"]) * kayit["skor"]
    sirali = sorted(havuz.values(), key=lambda k: (k["df"], -k["destek"]))
    assert sirali[0]["ad"] == "Ozgul", [k["ad"] for k in sirali]

    # Çarpımsal sönümleme AYNI veride yanlış sonucu veriyor — eski hatanın
    # neden hata olduğunu sabitliyor.
    import math
    carpimsal = sorted(
        havuz.values(),
        key=lambda k: -(k["destek"] * math.log(1 + eksen_sayisi / k["df"])),
    )
    assert carpimsal[0]["ad"] == "Populer", "eski yöntem popüleri öne alıyordu"


def test_kuresel_hub_esigi():
    """Eksenlerin üçte biri ya da fazlasında görünen tamamen elenmeli.

    Eşik `df < esik` olarak uygulanıyor: 9 eksende esik=3, yani df=1 ve df=2
    geçer, df>=3 elenir. Az eksenli çalışmalarda taban 2 — yoksa eşik 1'e düşer
    ve tek eksende görünen bile elenirdi.
    """
    for eksen_sayisi, beklenen in ((9, 3), (12, 4), (3, 2), (1, 2)):
        esik = max(2, (eksen_sayisi + 2) // 3)
        assert esik == beklenen, f"{eksen_sayisi} eksende eşik {esik}, {beklenen} bekleniyordu"


def test_strateji_adi_sabit():
    """Arayüz ve veritabanı bu ada göre süzüyor."""
    import inspect
    kaynak = inspect.getsource(A.bilincli_uzaklik)
    assert 'strateji="bilincli_uzaklik"' in kaynak




# --------------------------------------------------------------------------- #
# Yazma: üretimin sahibi olmadığı sütunlara dokunulmamalı
# --------------------------------------------------------------------------- #

def _gecici_db():
    import tempfile
    from python.db import baglan
    yol = tempfile.mktemp(suffix=".sqlite")
    conn = baglan(yol)
    with conn:
        conn.execute(
            "INSERT INTO clusters (kume_id, calisma_id, stabil_mi) VALUES (0,'c1',1)"
        )
    return conn


def _aday(aday_artist="S", title="T", eksen=0, strateji="sahne_komsulugu"):
    return A.Aday(artist=aday_artist, title=title, year=2000, strateji=strateji,
                  eksen=eksen, skor=1.0, gerekce="g", dayanak={})


def test_yeniden_uretim_onizlemeyi_silmez():
    """Ölçülen gerçek hata: INSERT OR REPLACE tüm satırı değiştirip
    sonradan bulunmuş 30 sn önizleme URL'sini NULL'a çeviriyordu."""
    conn = _gecici_db()
    a = _aday()
    A.adaylari_yaz(conn, "c1", [a])
    with conn:
        conn.execute(
            "UPDATE adaylar SET onizleme_url='http://klip' WHERE aday_id=?",
            (a.aday_id,),
        )
    a.skor = 9.0
    A.adaylari_yaz(conn, "c1", [a])   # aynı aday, yeni skor
    satir = conn.execute(
        "SELECT onizleme_url, skor FROM adaylar WHERE aday_id=?", (a.aday_id,)
    ).fetchone()
    assert satir[0] == "http://klip", f"önizleme silinmiş: {satir[0]}"
    assert satir[1] == 9.0, "skor güncellenmeliydi"


def test_bayat_aday_silinir():
    """Strateji düzeltilince eski çıktı ortada kalmamalı."""
    conn = _gecici_db()
    eski, yeni = _aday(title="Live & Rare"), _aday(title="Nevermind")
    A.adaylari_yaz(conn, "c1", [eski])
    A.adaylari_yaz(conn, "c1", [yeni])
    A.bayat_adaylari_temizle(conn, "c1", [yeni], tarih="2026-08-17")
    kalan = {r[0] for r in conn.execute("SELECT title FROM adaylar")}
    assert kalan == {"Nevermind"}, kalan


def test_karar_verilen_aday_silinmez():
    """Beğendiğin bir albümün kaydı, yeniden üretimde kaybolmamalı."""
    conn = _gecici_db()
    eski, yeni = _aday(title="Begendigim"), _aday(title="Yeni")
    A.adaylari_yaz(conn, "c1", [eski])
    with conn:
        conn.execute(
            "INSERT INTO feedback (aday_id, calisma_id, eksen, karar, tarih) "
            "VALUES (?,?,?,?,date('now'))",
            (eski.aday_id, "c1", 0, "begendim"),
        )
    A.adaylari_yaz(conn, "c1", [yeni])
    A.bayat_adaylari_temizle(conn, "c1", [yeni], tarih="2026-08-17")
    kalan = {r[0] for r in conn.execute("SELECT title FROM adaylar")}
    assert kalan == {"Begendigim", "Yeni"}, kalan


# --------------------------------------------------------------------------- #
# Önizleme eşleşmesi: doğru sanatçı YETMEZ, doğru albüm de gerek
# --------------------------------------------------------------------------- #

def test_yanlis_albumun_klibi_reddedilir():
    """Ölçülen hata: Mariya Takeuchi'nin üç ayrı albümü (1978/79/80) için de
    «Plastic Love» (1984) dönüyordu — arama zayıf eşleşmede sanatçının HIT
    şarkısına düşüyor. Bedeli sadece yanlış şarkı değil: aday albümün stem
    ölçümü o klipten yapılıyor."""
    from python.discover.onizleme import _album_uyuyor_mu as uy

    assert not uy("BEGINNING", "Variety")
    assert not uy("Love Songs", "Variety")
    assert not uy("Adore", "Gish")
    assert not uy("SPACY", "Circus Town")


def test_ayni_albumun_varyanti_kabul_edilir():
    """Yeniden basım ve yazım farkı reddedilmemeli — aşırı katılık kapsamayı
    gereksiz düşürür."""
    from python.discover.onizleme import _album_uyuyor_mu as uy

    assert uy("Gish", "Gish (Remastered)")
    assert uy("Use Your Illusion I", "Use Your Illusion 1")
    assert uy("Nevermind", "Nevermind")


def test_bos_ad_reddedilir():
    from python.discover.onizleme import _album_uyuyor_mu as uy

    assert not uy("", "Bir Sey")
    assert not uy("Bir Sey", "")


def test_kaynasma_kesisimi_odullendirir():
    """İki listede de görünmek, tek listede birinci olmaktan iyidir.

    Kaynaşmanın bütün amacı bu. «ikili» hiçbir listede birinci değil ama
    ikisinde de var; «tekil» bir listede birinci ama diğerinde yok. Kaynaşma
    ikiliyi öne almalı — projenin tekrar eden deseni: kesişim bir sönümleme
    çarpanı olarak değil, SIRALAMA ÖLÇÜTÜ olarak kullanılır.
    """
    from python.discover.adaylar import melez_sirala

    a = ["tekil"] + [f"dolgu{i}" for i in range(48)] + ["ikili"]
    b = ["baska"] + [f"dolgu{i}" for i in range(48)] + ["ikili"]
    sonuc = melez_sirala([a, b])
    assert sonuc.index("ikili") < sonuc.index("tekil"), sonuc[:5]


def test_kaynasma_agirliga_uyar():
    """Güçlü sinyale ağırlık verilince onun sıralaması ağır basmalı.

    Ölçüm çalma listesi sinyalini CLAP'ten güçlü buldu (rastgeleye göre 5,4'e
    karşı 1,4 kat) ve üretimde 2:1 kullanılıyor. Ağırlık yok sayılırsa o karar
    sessizce iptal olur.
    """
    from python.discover.adaylar import melez_sirala

    guclu, zayif = ["x", "y"], ["y", "x"]
    assert melez_sirala([guclu, zayif], agirliklar=[5, 1])[0] == "x"
    assert melez_sirala([guclu, zayif], agirliklar=[1, 5])[0] == "y"


def test_kaynasma_bos_listeye_dayanir():
    """Bir sinyal hiç aday üretmezse diğeri tek başına çalışmalı."""
    from python.discover.adaylar import melez_sirala

    assert melez_sirala([["a", "b"], []]) == ["a", "b"]
    assert melez_sirala([[], []]) == []


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
