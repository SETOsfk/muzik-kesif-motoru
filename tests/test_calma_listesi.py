"""Çalma listesi hasadı ve PMI testleri.

İki şey ölçülerek bulundu ve ikisi de sessizce geri gelebilir:
1. Tek sanatçılık derlemeler («100% Meshuggah») birliktelik sinyali taşımıyor.
2. Ham birliktelik popüleri öne çıkarıyor — 22 listelik ilk örneklemde
   Van Halen ↔ Madonna/Haddaway çıkmıştı (80'ler parti listeleri).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python.db import baglan
from python.discover import calma_listesi as C

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


def _parcalar(*adlar):
    return [{"artist": {"name": a}, "title": f"p{i}"} for i, a in enumerate(adlar)]


def test_tek_sanatcilik_derleme_elenir():
    """«100% Meshuggah» — 50 parçanın 50'si aynı gruptan, sinyal sıfır."""
    assert not C._karisik_mi(_parcalar(*["Meshuggah"] * 12))


def test_karisik_liste_gecer():
    assert C._karisik_mi(_parcalar(
        "Meshuggah", "Gojira", "Opeth", "TOOL", "Car Bomb",
        "Haken", "Devin Townsend", "Klone", "Leprous"))


def test_esik_yarisindan_fazlasi():
    """Kural "yarısından FAZLASI" — tam yarı geçer, bir fazlası elenir.

    Sınırın hangi tarafta olduğu keyfi değil: yarısı bir sanatçı, yarısı
    başkaları olan bir liste hâlâ birliktelik taşıyor. Bir fazlası artık
    o sanatçının derlemesi.
    """
    tam_yari = ["A"] * 6 + ["B", "C", "D", "E", "F", "G"]
    bir_fazla = ["A"] * 7 + ["B", "C", "D", "E", "F"]
    assert C._karisik_mi(_parcalar(*tam_yari)), "tam yarı geçmeli"
    assert not C._karisik_mi(_parcalar(*bir_fazla)), "yarıdan fazlası elenmeli"


def test_kisa_liste_degerlendirilmez():
    assert not C._karisik_mi(_parcalar("A", "B", "C"))


def _db(listeler):
    """listeler: {liste_id: [sanatçı, ...]}  — biri kütüphanede olacak."""
    conn = baglan(":memory:")
    with conn:
        conn.execute("INSERT INTO albums (album_id, artist, title) "
                     "VALUES ('a1','Sahip','T')")
        for liste_id, sanatcilar in listeler.items():
            conn.execute(
                "INSERT INTO calma_listesi (liste_id, baslik, parca_sayisi) "
                "VALUES (?,?,?)", (liste_id, f"L{liste_id}", len(sanatcilar)))
            conn.executemany(
                "INSERT INTO liste_parca "
                "(liste_id, sira, sanatci, sanatci_anahtar, parca, onizleme) "
                "VALUES (?,?,?,?,?,?)",
                [(liste_id, i, a, a.lower(), f"parca{i}", "http://x")
                 for i, a in enumerate(sanatcilar)])
    return conn


def test_pmi_populeri_sonumler():
    """Her listede olan sanatçı, yalnız bizimkiyle görüleni GEÇMEMELİ.

    Ölçülen hata buydu: ham sayıda Metallica hep önde çıkıyordu.
    """
    listeler = {i: ["Sahip", "Populer"] for i in range(1, 9)}
    # Nis yalnız iki listede, ama o iki listenin ikisinde de Sahip var.
    listeler[1] = ["Sahip", "Populer", "Nis"]
    listeler[2] = ["Sahip", "Populer", "Nis"]
    # Populer ayrıca bizimle ilgisiz listelerde de var → P(b) büyür.
    for i in range(9, 15):
        listeler[i] = ["Populer", f"Baska{i}"]

    conn = _db(listeler)
    sonuc = {b: pmi for a, b, adet, pmi in C.birliktelik(conn) if a == "sahip"}
    assert "nis" in sonuc and "populer" in sonuc, sonuc
    assert sonuc["nis"] > sonuc["populer"], (
        f"niş {sonuc['nis']:.2f} popülerden {sonuc['populer']:.2f} yüksek olmalı")


def test_tek_listede_gorulen_elenir():
    """Bir kez yan yana gelmek tesadüf; iki ayrı liste iki ayrı insan demek."""
    conn = _db({i: ["Sahip", "Ortak"] for i in range(1, 7)} | {7: ["Sahip", "Tek"]})
    adaylar = {b for a, b, _, _ in C.birliktelik(conn) if a == "sahip"}
    assert "ortak" in adaylar
    assert "tek" not in adaylar, "tek listelik birliktelik yazılmamalı"


def test_sahip_olunan_aday_olmaz():
    conn = _db({i: ["Sahip", "Yeni"] for i in range(1, 6)})
    adaylar = {b for _, b, _, _ in C.birliktelik(conn)}
    assert "sahip" not in adaylar


def test_az_veride_sonuc_uretilmez():
    """Beş listenin altında PMI kararsız — hiç sonuç verme."""
    assert C.birliktelik(_db({1: ["Sahip", "X"], 2: ["Sahip", "X"]})) == []


def test_aday_parcalar_onizlemesiz_getirmez():
    conn = _db({i: ["Sahip", "Yeni"] for i in range(1, 8)})
    C.birliktelik_yaz(conn, C.birliktelik(conn))
    with conn:
        conn.execute("UPDATE liste_parca SET onizleme = NULL "
                     "WHERE sanatci_anahtar = 'yeni' AND sira % 2 = 0")
    for p in C.aday_parcalar(conn, ["Sahip"]):
        assert p["onizleme"], "önizlemesiz parça aday olmamalı"


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
