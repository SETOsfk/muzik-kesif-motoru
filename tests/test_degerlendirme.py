"""Değerlendirme düzeneği testleri.

Bu düzeneğin işi sayı üretmek, o yüzden en tehlikeli hata yanlış çalışması
değil, YANLIŞ SAYI üretip inandırıcı görünmesi. Testler o yüzden ölçüm
geçerliliğini koruyor:

1. SIZINTI — gizlenen sanatçının kendi verisi sorguya ya da hubness tabanına
   karışırsa motor kendi cevabını görmüş olur ve sayılar şişer.
2. GİZLENEN ADAY OLABİLMELİ — saklanmış PMI tablosu kütüphane sanatçılarını
   aday havuzundan çıkarıyor; o tablo kullanılırsa recall zorunlu olarak sıfır
   çıkar ve bu "motor kötü" diye okunur. Gerçekte ölçüm bozuktur.
3. PAYDALAR — recall'un iki paydası var (tüm gizlenenler / havuzda olanlar);
   karışırlarsa kapsama boşluğu sıralama başarısı gibi görünür.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


def _v(*x):
    v = np.array(x, dtype="float32")
    return v / np.linalg.norm(v)


def _ortam(tmp, kutuphane, havuz, listeler=()):
    """kutuphane: {sanatçı: vektör}. havuz: {sanatçı: vektör}.

    `listeler`: [(liste_id, [sanatçı, ...])] — PMI için.
    """
    import python.etiket_clap as C
    import python.degerlendirme as D
    from python.db import baglan

    kok = Path(tmp)
    (kok / "clap").mkdir(parents=True, exist_ok=True)
    (kok / "clap_parca").mkdir(parents=True, exist_ok=True)
    C.GOMU_KLASOR = D.GOMU_KLASOR = kok / "clap"
    C.PARCA_GOMU = D.PARCA_GOMU = kok / "clap_parca"

    conn = baglan(":memory:")
    parca_id = 1000
    with conn:
        for ad, v in kutuphane.items():
            conn.execute(
                "INSERT INTO albums (album_id, artist, title) VALUES (?,?,?)",
                (f"alb_{ad}", ad, f"{ad} albümü"))
            np.save(kok / "clap" / f"alb_{ad}.npy", v.astype("float32"))

        conn.execute("INSERT INTO calma_listesi (liste_id, baslik) VALUES (9,'havuz')")
        for ad, v in havuz.items():
            parca_id += 1
            conn.execute(
                "INSERT INTO liste_parca (liste_id, sira, sanatci, "
                "sanatci_anahtar, parca, parca_id) VALUES (9,?,?,?,?,?)",
                (parca_id, ad, ad.lower(), f"{ad} parçası", parca_id))
            np.save(kok / "clap_parca" / f"{parca_id}.npy", v.astype("float32"))

        for liste_id, uyeler in listeler:
            conn.execute(
                "INSERT OR IGNORE INTO calma_listesi (liste_id, baslik) VALUES (?,?)",
                (liste_id, f"liste {liste_id}"))
            for sira, ad in enumerate(uyeler):
                conn.execute(
                    "INSERT INTO liste_parca (liste_id, sira, sanatci, "
                    "sanatci_anahtar, parca) VALUES (?,?,?,?,?)",
                    (liste_id, sira, ad, ad.lower(), f"{ad} p{sira}"))
    return conn


# --------------------------------------------------------------------------- #
# 1. Sızıntı
# --------------------------------------------------------------------------- #

def test_gizlenenin_kendi_gomusu_sorguya_karismaz():
    """Gizlenen sanatçının albümü sorguda kalırsa kendini bulur — sayı şişer.

    Kurgu: x'in kütüphane albümü ile havuzdaki parçası AYNI vektör. Sızıntı
    varsa x kendine 1.0 benzerlikle birinci olur. Doğru davranışta x'in
    vektörü sorgudan çıkar, x havuzda a'ya benzemediği için y'nin gerisinde
    kalır.
    """
    from python.degerlendirme import SesErisimi, gomu_haritalari

    with tempfile.TemporaryDirectory() as tmp:
        conn = _ortam(
            tmp,
            kutuphane={"a": _v(1, 0, 0), "b": _v(0, 1, 0), "x": _v(0, 0, 1)},
            havuz={"x": _v(0, 0, 1), "y": _v(1, 0, 0)},
        )
        kutup, havuz = gomu_haritalari(conn)
        siralama = SesErisimi(kutup, havuz).sirala("x", {"a", "b"})
        assert siralama.index("y") < siralama.index("x"), (
            f"x kendi gömüsünü görmüş olabilir: {siralama}")


def test_gizlenen_hubness_tabanina_girmez():
    """Taban gizleneni içerirse düzeltme onun lehine kayar.

    Doğrudan kontrol: `sirala` içindeki `kalan` maskesi gizlenenin satırlarını
    dışarıda bırakmalı. Kütüphanede x'in İKİ albümü varsa ikisi de düşmeli.
    """
    from python.degerlendirme import SesErisimi, gomu_haritalari
    from python.db import baglan

    with tempfile.TemporaryDirectory() as tmp:
        conn = _ortam(tmp, kutuphane={"a": _v(1, 0, 0), "x": _v(0, 0, 1)},
                      havuz={"y": _v(1, 1, 0)})
        with conn:
            conn.execute(
                "INSERT INTO albums (album_id, artist, title) VALUES (?,?,?)",
                ("alb_x2", "x", "x ikinci albüm"))
        np.save(Path(tmp) / "clap" / "alb_x2.npy", _v(0, 0, 1))

        kutup, havuz = gomu_haritalari(conn)
        e = SesErisimi(kutup, havuz)
        assert e.kutup_sahip.count("x") == 2, "kurgu hatalı"
        kalan = np.array(e.kutup_sahip) != "x"
        assert kalan.sum() == 1, "gizlenenin tüm albümleri düşmeli"


# --------------------------------------------------------------------------- #
# 2. Gizlenen aday olabilmeli
# --------------------------------------------------------------------------- #

def test_kutuphane_sanatcisi_pmi_adayi_olabilir():
    """Saklanmış tablo bunu yapmıyor; değerlendirmenin yeniden hesaplaması şart.

    `calma_listesi.birliktelik` aday havuzundan kütüphaneyi çıkarıyor (ölçüldü:
    1.615 aday anahtarının 0'ı kütüphanede). Aynı davranış buraya sızarsa
    gizlenen sanatçı asla bulunamaz ve recall yapısal olarak 0 olur.
    """
    from python.degerlendirme import pmi_tablosu

    with tempfile.TemporaryDirectory() as tmp:
        # a ile x altı listede birlikte; ikisi de kütüphanede.
        listeler = [(i, ["a", "x", f"dolgu{i}"]) for i in range(10, 16)]
        listeler += [(i, [f"baska{i}"]) for i in range(20, 26)]
        conn = _ortam(tmp, kutuphane={"a": _v(1, 0, 0), "x": _v(0, 1, 0)},
                      havuz={}, listeler=listeler)
        tablo = pmi_tablosu(conn, {"a", "x"})
        assert "x" in tablo.get("a", {}), (
            f"kütüphane sanatçısı aday olarak görünmüyor: {dict(tablo)}")


def test_gizlenen_havuzdan_elenmez():
    """`sahip` içindekiler elenir ama gizlenen elenmez — sınamanın hedefi o."""
    from python.degerlendirme import SesErisimi, gomu_haritalari

    with tempfile.TemporaryDirectory() as tmp:
        conn = _ortam(tmp, kutuphane={"a": _v(1, 0, 0), "x": _v(0, 1, 0)},
                      havuz={"x": _v(0, 1, 0), "a": _v(1, 0, 0), "y": _v(0, 0, 1)})
        kutup, havuz = gomu_haritalari(conn)
        siralama = SesErisimi(kutup, havuz).sirala("x", {"a"})
        assert "x" in siralama, "gizlenen aday olarak dönmeli"
        assert "a" not in siralama, "sahip olunan sanatçı elenmeli"


# --------------------------------------------------------------------------- #
# 3. Paydalar ve sıra
# --------------------------------------------------------------------------- #

def test_sira_bir_tabanli():
    from python.degerlendirme import sira_bul

    assert sira_bul(["a", "b", "c"], "a") == 1
    assert sira_bul(["a", "b", "c"], "c") == 3
    assert sira_bul(["a", "b"], "yok") is None


def test_ozet_iki_paydayi_ayirir():
    """recall tüm gizlenenlere, recall_eris havuzda olanlara bölünür.

    Karışırlarsa kapsama boşluğu (havuzda yok) sıralama başarısızlığı gibi
    okunur ve yanlış işe yatırım yapılır.
    """
    from python.degerlendirme import ozet

    # 4 gizlenen, 2'si havuzda erişilebilir, 1'i ilk sırada bulundu.
    o = ozet([1, None, None, None], erisilebilir=2)
    assert o["gizlenen"] == 4 and o["bulunan"] == 1
    assert abs(o["recall@1"] - 0.25) < 1e-9
    assert abs(o["recall@1_eris"] - 0.50) < 1e-9
    assert abs(o["mrr"] - 0.25) < 1e-9


def test_mrr_siraya_duyarli():
    """MRR yalnız "bulundu mu"ya değil, KAÇINCI bulunduğuna bakmalı."""
    from python.degerlendirme import ozet

    bas = ozet([1, 1], erisilebilir=2)["mrr"]
    son = ozet([10, 10], erisilebilir=2)["mrr"]
    assert bas > son, "MRR sıraya duyarsız"
    assert abs(son - 0.1) < 1e-9


# --------------------------------------------------------------------------- #
# 4. Eksen kapsamı
# --------------------------------------------------------------------------- #

def test_eksen_haritasi_kendini_icermez():
    """Sanatçının komşuları arasında kendisi olursa sorguya sızar."""
    from python.degerlendirme import eksen_haritasi

    with tempfile.TemporaryDirectory() as tmp:
        conn = _ortam(tmp, kutuphane={"a": _v(1, 0, 0), "b": _v(0, 1, 0)},
                      havuz={})
        with conn:
            conn.execute("INSERT INTO clusters (calisma_id, kume_id, stabil_mi) "
                         "VALUES ('c1', 0, 1)")
            for ad in ("a", "b"):
                conn.execute(
                    "INSERT INTO memberships (album_id, kume_id, uyelik, "
                    "calisma_id) VALUES (?,0,0.9,'c1')", (f"alb_{ad}",))
        harita = eksen_haritasi(conn, "c1")
        assert harita["a"] == {"b"}, harita
        assert "a" not in harita["a"]


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
