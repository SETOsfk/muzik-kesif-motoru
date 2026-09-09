"""Çok boyutlu etiketleme testleri.

Etiketin işi AYIRT ETMEK. En kolay iki hata: her albüme her etiketi vermek
(etiket bilgisizleşir) ve eşiği elle yazmak (başka kütüphanede saçmalar).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from python.db import baglan
from python.etiket import KUYRUK, _lu, etiketle, tarifler, yaz

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


def _db(n=50):
    """n albüm, zil payı 0.05'ten 0.95'e düzgün dağılmış."""
    conn = baglan(":memory:")
    zil = np.linspace(0.05, 0.95, n)
    with conn:
        for i in range(n):
            conn.execute(
                "INSERT INTO albums (album_id, artist, title, year) VALUES (?,?,?,?)",
                (f"a{i}", f"S{i}", f"T{i}", 1995))
            conn.execute(
                "INSERT INTO stem_profili (album_id, tur, stem, zil_payi, "
                "tekme_payi, izgara_entropi, nota_vurus, dinamik_db, tempo) "
                "VALUES (?,'album','drums',?,?,?,?,?,?)",
                (f"a{i}", float(zil[i]), 0.2, 0.95, 1.8, 20.0, 120.0))
    return conn


def test_ortadakiler_etiket_almaz():
    """Her albüme etiket vermek etiketi bilgisizleştirir."""
    conn = _db(50)
    e = etiketle(conn)
    olcum = e[e["kaynak"] == "olcum"]
    zil_ust = set(olcum[olcum["etiket"] == "ride ağırlıklı davul"]["album_id"])
    # 50 albümün en fazla ~%20'si + eşik eşitliği payı
    assert 5 <= len(zil_ust) <= 15, f"{len(zil_ust)} albüm etiket almış"
    assert "a25" not in zil_ust, "ortadaki albüm kuyruk etiketi almamalı"


def test_esik_veriden_gelir():
    """Aynı mutlak değer, farklı kütüphanede farklı etiketlenmeli.

    Sabit eşik (örn. zil > 0.5) yazılsaydı, her şeyin zil ağırlıklı olduğu bir
    kütüphanede hepsi "zil ağırlıklı" olurdu ve etiket hiçbir şey söylemezdi.
    """
    dusuk = baglan(":memory:")
    yuksek = baglan(":memory:")
    for conn, taban in ((dusuk, 0.0), (yuksek, 0.5)):
        with conn:
            for i in range(40):
                conn.execute("INSERT INTO albums (album_id, artist, title) "
                             "VALUES (?,?,?)", (f"a{i}", "S", "T"))
                conn.execute(
                    "INSERT INTO stem_profili (album_id, tur, stem, zil_payi, "
                    "tekme_payi, izgara_entropi, nota_vurus, dinamik_db, tempo) "
                    "VALUES (?,'album','drums',?,0.2,0.95,1.8,20.0,120.0)",
                    (f"a{i}", taban + i * 0.01))
    ad = "ride ağırlıklı davul"
    d = etiketle(dusuk); y = etiketle(yuksek)
    assert len(d[d.etiket == ad]) == len(y[y.etiket == ad]), (
        "kuyruk payı kütüphaneden bağımsız aynı olmalı")


def test_az_veride_olcum_etiketi_uretilmez():
    assert etiketle(_db(10)).query("kaynak == 'olcum'").empty


def test_donem_etiketi():
    e = etiketle(_db(30))
    assert "1990'lar" in set(e[e["kaynak"] == "yil"]["etiket"])


def test_tarif_tek_albumluk_olmaz():
    conn = _db(50)
    yaz(conn, etiketle(conn))
    t = tarifler(conn, asgari_albom=2)
    if not t.empty:
        assert t["albüm"].min() >= 2, "tek albümlük tarif kategori değildir"


def test_unlu_uyumu():
    """"davullı", "söyleyişlı", "ritimlı" bozuktu — tarif okunacaksa doğru olmalı."""
    assert _lu("davul") == "davullu"
    assert _lu("söyleyiş") == "söyleyişli"
    assert _lu("ritim") == "ritimli"
    assert _lu("vokal") == "vokallı"
    assert _lu("bas") == "baslı"
    assert _lu("ton") == "tonlu"
    # Son ünlü belirleyici, ilk değil.
    assert _lu("geniş vokal") == "geniş vokallı"
    assert _lu("programlanmış ritim") == "programlanmış ritimli"


def test_kuyruk_makul():
    assert 0.05 <= KUYRUK <= 0.35, "kuyruk payı çok dar ya da çok geniş"


# --------------------------------------------------------------------------- #
# Bağlam etiketleri — çalma listesi başlıklarından
# --------------------------------------------------------------------------- #

def _liste_db(basliklar_ve_sanatcilar):
    conn = baglan(":memory:")
    with conn:
        for i, (baslik, sanatcilar) in enumerate(basliklar_ve_sanatcilar, 1):
            conn.execute("INSERT INTO calma_listesi (liste_id, baslik, parca_sayisi) "
                         "VALUES (?,?,?)", (i, baslik, len(sanatcilar)))
            conn.executemany(
                "INSERT INTO liste_parca (liste_id, sira, sanatci, sanatci_anahtar, parca) "
                "VALUES (?,?,?,?,?)",
                [(i, j, a, a.lower(), f"p{j}") for j, a in enumerate(sanatcilar)])
    return conn


def test_baglam_sozlukten_gelir():
    from python.etiket import baglam_etiketleri

    conn = _liste_db([("Evening Chill", ["A"]), ("Relaxation", ["A"])])
    e = baglam_etiketleri(conn)
    etiketler = set(e["etiket"])
    assert "sakin" in etiketler
    assert "akşam" in etiketler


def test_sanatci_adi_baglam_olmaz():
    """Başlıklarda sanatçı adı ve kişisel not var; serbest kelime toplamak
    yanlış olurdu — kontrollü sözlük bunları dışarıda bırakmalı."""
    from python.etiket import baglam_etiketleri

    conn = _liste_db([("GOJIRA DEEZER", ["A"]), ("new staff", ["A"]),
                      ("Jesse john's", ["A"]), ("Top Croatia", ["A"])])
    assert baglam_etiketleri(conn).empty


def test_baglam_kanit_sayisi_taşınır():
    """Bir listeden gelen bir kişinin kararı, beşten gelen bir örüntü.
    Etiket kaç listeden geldiğini taşımalı ki ikisi ayırt edilebilsin."""
    from python.etiket import baglam_etiketleri

    conn = _liste_db([("Chill 1", ["A"]), ("Chill 2", ["A"]),
                      ("Relaxing 3", ["A"]), ("Party", ["B"])])
    e = baglam_etiketleri(conn)
    a = e[(e.sanatci_anahtar == "a") & (e.etiket == "sakin")].iloc[0]
    b = e[(e.sanatci_anahtar == "b") & (e.etiket == "parti")].iloc[0]
    assert a["liste"] == 3 and b["liste"] == 1, (a["liste"], b["liste"])


def test_aday_etiket_esigi_kutuphaneden():
    """Aday etiketi kütüphane eşiğiyle verilmeli, aday havuzunun kendi
    dağılımıyla değil — yoksa etiket o gün üretilen adaylara göre değişir."""
    from python.etiket import aday_olcum_etiketleri

    conn = _db(50)   # kütüphane: zil 0.05–0.95
    with conn:
        # Adayların hepsi düşük zilli; kütüphane eşiğine göre hiçbiri
        # "ride ağırlıklı" olmamalı — ama kendi aralarında en yükseği vardır.
        for i in range(10):
            conn.execute(
                "INSERT INTO stem_profili (album_id, tur, stem, zil_payi, "
                "tekme_payi, izgara_entropi, nota_vurus, dinamik_db, tempo) "
                "VALUES (?,'aday','drums',?,0.2,0.95,1.8,20.0,120.0)",
                (f"x{i}", 0.10 + i * 0.005))
    etiketli = aday_olcum_etiketleri(conn)
    hepsi = {e for v in etiketli.values() for e in v}
    assert "ride ağırlıklı davul" not in hepsi, hepsi


def test_etiketler_denetimden_gecmis_olculere_dayanir():
    """Elenmiş bir ölçüte etiket asılamaz.

    Gerçek hata (2026-09-02): «yoğun davul» etiketi `nota_vurus`'a dayanıyordu
    ama o ölçüt davul için denetimde ELENMİŞTİ (artık payı 0,296 — diğer davul
    ölçütlerinin doğrusal bileşiminden ibaret). Yani kullanıcıya bağımsız bir
    bilgi gibi gösterilen şey başka etiketlerin kopyasıydı.

    `DENETLENEN`, `python -m python.enrich.olcut_denetimi` çıktısıdır. Denetim
    yeniden koşturulup küme değişirse bu test etiketlerin de gözden
    geçirilmesini zorlar.
    """
    from python.etiket import DENETLENEN, OLCUM_ETIKETLERI

    kotu = [(sutun, stem) for sutun, stem, *_ in OLCUM_ETIKETLERI
            if sutun not in DENETLENEN.get(stem, frozenset())]
    assert not kotu, f"denetimden geçmeyen ölçüte etiket: {kotu}"


def test_dort_stem_de_temsil_edilir():
    """Etiketleme davula kaymamalı — kullanıcı isteği (2026-09-02).

    Önceki küme 20 etiketin 9'unu davula ayırmış, bası TEK etiketle geçmiş,
    gitar/klavye tarafını hiç adlandırmamıştı («distorsiyonlu», «parlak»
    hangi enstrümandan geldiğini söylemiyordu). Sessizce geri kayarsa
    kullanıcı yine davulu okuyup gerisini tahmin eder.
    """
    from collections import Counter

    from python.etiket import OLCUM_ETIKETLERI

    sayim = Counter(stem for _, stem, *_ in OLCUM_ETIKETLERI)
    for stem in ("drums", "bass", "other", "vocals"):
        assert sayim[stem] >= 5, f"{stem} yetersiz temsil: {sayim[stem]}"
    # Hiçbir stem toplamın yarısından fazlasını kaplamamalı.
    assert max(sayim.values()) <= len(OLCUM_ETIKETLERI) / 2, sayim


def test_etiket_adlari_tekil():
    """İki farklı ölçüm aynı etiketi üretirse hangisinden geldiği kaybolur."""
    from python.etiket import OLCUM_ETIKETLERI

    adlar = [e for *_, e, _ in OLCUM_ETIKETLERI]
    assert len(adlar) == len(set(adlar)), \
        f"tekrar eden etiket: {[a for a in adlar if adlar.count(a) > 1]}"


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
