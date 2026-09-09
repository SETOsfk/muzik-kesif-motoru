"""Ses kümeleri testleri — etiketsiz tür keşfi.

Kullanıcının çerçevesi: "sahip olduğumu seviyorum, bu yüzden kümeliyoruz.
j-fusion önerisi istediğimde elimde olmayan bir öneri gelsin."

Yani kütüphane POZİTİF sinyal, iş de basit: bu sese yakın olup sende
olmayanları getirmek. Testler üç şeyi koruyor.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


def _ortam(tmp, kutuphane, havuz_albom=(), havuz_parca=()):
    """Sahte gömü klasörleri kur. kutuphane: {album_id: vektör}."""
    import python.etiket_clap as C
    import python.ses_kume as S
    from python.db import baglan

    kok = Path(tmp)
    (kok / "clap").mkdir(parents=True, exist_ok=True)
    (kok / "clap_parca").mkdir(parents=True, exist_ok=True)
    C.GOMU_KLASOR = S.GOMU_KLASOR = kok / "clap"
    C.PARCA_GOMU = S.PARCA_GOMU = kok / "clap_parca"

    conn = baglan(":memory:")
    with conn:
        for aid, v in kutuphane.items():
            conn.execute("INSERT INTO albums (album_id, artist, title) VALUES (?,?,?)",
                         (aid, aid.upper(), f"{aid} albümü"))
            np.save(kok / "clap" / f"{aid}.npy", v.astype("float32"))
        for aid, artist, v in havuz_albom:
            conn.execute(
                "INSERT INTO adaylar (aday_id, calisma_id, eksen, strateji, "
                "artist, title, skor, gerekce) VALUES (?,?,0,'x',?,?,1,'g')",
                (aid, "c1", artist, f"{artist} albümü"))
            np.save(kok / "clap" / f"{aid}.npy", v.astype("float32"))
        for pid, artist, parca, v in havuz_parca:
            conn.execute("INSERT INTO calma_listesi (liste_id, baslik) VALUES (?,?)",
                         (pid, "L"))
            conn.execute(
                "INSERT INTO liste_parca (liste_id, sira, sanatci, "
                "sanatci_anahtar, parca, parca_id) VALUES (?,0,?,?,?,?)",
                (pid, artist, artist.lower(), parca, pid))
            np.save(kok / "clap_parca" / f"{pid}.npy", v.astype("float32"))
    return conn


def _v(*x):
    v = np.array(x, dtype="float32")
    return v / np.linalg.norm(v)


def test_sahip_olunan_onerilmez():
    """Kullanıcı zaten sahibi; öneri "sende OLMAYAN" demek."""
    import tempfile

    from python.ses_kume import kumeye_yakinlar

    with tempfile.TemporaryDirectory() as tmp:
        conn = _ortam(tmp,
            {"a1": _v(1, 0, 0), "a2": _v(0.9, 0.1, 0)},
            havuz_parca=[(10, "A1", "p", _v(1, 0, 0))])   # sanatçı adı sahip
        uyeler = pd.DataFrame({"album_id": ["a1", "a2"], "kume": [0, 0],
                               "merkez_uzakligi": [0.0, 0.1]})
        for o in kumeye_yakinlar(conn, uyeler, adet=10):
            assert o["sanatci"].lower() != "a1", "sahip olunan sanatçı önerilmemeli"


def test_tekrar_eden_parca_bir_kez():
    """Aynı parça birden çok listede farklı kimlikle gömülmüş olabiliyor —
    «Green Onions» iki kez çıkmıştı."""
    import tempfile

    from python.ses_kume import kumeye_yakinlar

    with tempfile.TemporaryDirectory() as tmp:
        conn = _ortam(tmp, {"a1": _v(1, 0, 0), "a2": _v(0.9, 0.1, 0)},
            havuz_parca=[(10, "Booker T", "Green Onions", _v(0.95, 0.05, 0)),
                         (11, "Booker T", "Green Onions", _v(0.94, 0.06, 0)),
                         (12, "Azymuth", "Dear Limmertz", _v(0.8, 0.2, 0))])
        uyeler = pd.DataFrame({"album_id": ["a1", "a2"], "kume": [0, 0],
                               "merkez_uzakligi": [0.0, 0.1]})
        adlar = [(o["sanatci"], o["ad"]) for o in kumeye_yakinlar(conn, uyeler, adet=10)]
        assert len(adlar) == len(set(adlar)), adlar


def test_benzedigi_albom_bildiriliyor():
    """Gerekçe doğrulanabilir olmalı: hangi albümüne benzediği yazılsın ki
    kullanıcı ikisini arka arkaya dinleyebilsin."""
    import tempfile

    from python.ses_kume import kumeye_yakinlar

    with tempfile.TemporaryDirectory() as tmp:
        conn = _ortam(tmp, {"a1": _v(1, 0, 0), "a2": _v(0, 1, 0)},
                      havuz_parca=[(10, "Yeni", "p", _v(0.05, 0.99, 0))])
        uyeler = pd.DataFrame({"album_id": ["a1", "a2"], "kume": [0, 0],
                               "merkez_uzakligi": [0.0, 0.1]})
        sonuc = kumeye_yakinlar(conn, uyeler, adet=5)
        assert sonuc and "A2" in sonuc[0]["benzedigi"], sonuc


def test_az_albumde_kumelenmez():
    """Küme sayısının iki katından az albümle kümeleme anlamsız."""
    import tempfile

    from python.ses_kume import kumele

    with tempfile.TemporaryDirectory() as tmp:
        conn = _ortam(tmp, {f"a{i}": _v(i + 1, 1, 0) for i in range(5)})
        assert kumele(conn, kume_sayisi=12).empty


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
