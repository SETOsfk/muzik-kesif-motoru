"""Geri bildirim testleri.

İki tuzak var ve ikisi de sessizce yanlış sonuç verir:
1. Üç kararı tek bir "iyi–kötü" ekseninde toplamak.
2. Küçük n'de ham oranı kesin bir sonuçmuş gibi sunmak.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from python.geri_bildirim import (
    ASGARI_N, ozet_cumleleri, strateji_isabeti, wilson,
)

_gecen, _kalan = [], []


def _kosul(ad, fn):
    try:
        fn()
        _gecen.append(ad)
        print(f"ok   {ad}")
    except AssertionError as h:
        _kalan.append((ad, h))
        print(f"HATA {ad}: {h}")


def _veri(**sayilar):
    """strateji -> {karar: adet} sözlüğünden çerçeve kur."""
    satirlar = []
    i = 0
    for strateji, kararlar in sayilar.items():
        for karar, adet in kararlar.items():
            for _ in range(adet):
                i += 1
                satirlar.append({"aday_id": f"a{i}", "karar": karar,
                                 "eksen": 0, "tarih": "2026-08-17",
                                 "strateji": strateji, "artist": "S",
                                 "title": "T"})
    return pd.DataFrame(satirlar)


def test_wilson_tek_gozlemde_kesinlik_iddia_etmez():
    """1/1 için ham oran %100; Wilson alt sınırı %100 OLMAMALI."""
    p, alt, ust = wilson(1, 1)
    assert p == 1.0
    assert alt < 0.8, f"alt sınır {alt} — tek gözlemde kesinlik iddiası"
    p, alt, ust = wilson(80, 80)
    assert alt > 0.9, f"80/80'de alt sınır {alt} — yüksek olmalıydı"


def test_wilson_sifirda_da_calisir():
    p, alt, ust = wilson(0, 3)
    assert p == 0.0 and alt == 0.0 and 0.0 < ust < 1.0


def test_zaten_biliyorum_zevk_paydasina_girmez():
    """8 «zaten biliyorum» + 2 «beğendim» → zevk isabeti 2/2, 2/10 değil."""
    isabet = strateji_isabeti(
        _veri(sahne={"begendim": 2, "zaten_biliyorum": 8})
    ).iloc[0]
    assert isabet["zevk_n"] == 2, isabet["zevk_n"]
    assert isabet["zevk_isabeti"] == 1.0
    # Ama keşif oranı düşük olmalı — asıl başarısızlık orada.
    assert abs(isabet["kesif_orani"] - 0.2) < 1e-9, isabet["kesif_orani"]


def test_tutmadi_kesif_sayilir():
    """Tutmayan bir albüm YENİ bir şeydi — keşif başarılı, zevk başarısız."""
    isabet = strateji_isabeti(_veri(s={"tutmadi": 4})).iloc[0]
    assert isabet["kesif_orani"] == 1.0
    assert isabet["zevk_isabeti"] == 0.0


def test_zevk_karari_yoksa_isabet_none():
    isabet = strateji_isabeti(_veri(s={"zaten_biliyorum": 3})).iloc[0]
    assert isabet["zevk_isabeti"] is None
    assert isabet["zevk_n"] == 0


def test_az_veride_cumle_kurulmaz():
    """Tek kararlık strateji, on kararlıkla aynı alarmı almamalı.

    Bu gerçekten oldu: `kesif_ust < 0.75` koşulu n=1'de de geçiyordu.
    """
    tek = ozet_cumleleri(strateji_isabeti(_veri(az={"zaten_biliyorum": 1})))
    assert all("az" not in c for c in tek), tek
    assert any("yeterli" in c or "yok" in c for c in tek), tek

    cok = ozet_cumleleri(
        strateji_isabeti(_veri(cok={"zaten_biliyorum": 8, "begendim": 2}))
    )
    assert any("cok" in c for c in cok), cok


def test_asgari_n_makul():
    assert ASGARI_N >= 3, "üçten az kararla strateji hakkında konuşulmamalı"


def _etki_ortami(tmp, kararlar, havuz):
    """Sahte gömü ortamı. kararlar: [(sanatçı, karar)], havuz: {sanatçı: vektör}."""
    import numpy as np
    import python.etiket_clap as C
    import python.ses_kume as S
    from python.db import baglan

    kok = Path(tmp)
    (kok / "clap").mkdir(parents=True, exist_ok=True)
    (kok / "clap_parca").mkdir(parents=True, exist_ok=True)
    C.GOMU_KLASOR = S.GOMU_KLASOR = kok / "clap"
    C.PARCA_GOMU = S.PARCA_GOMU = kok / "clap_parca"

    conn = baglan(":memory:")
    pid = 500
    with conn:
        conn.execute("INSERT INTO calma_listesi (liste_id, baslik) VALUES (1,'L')")
        for ad, v in havuz.items():
            pid += 1
            conn.execute(
                "INSERT INTO liste_parca (liste_id, sira, sanatci, "
                "sanatci_anahtar, parca, parca_id) VALUES (1,?,?,?,?,?)",
                (pid, ad, ad.lower(), f"{ad} p", pid))
            np.save(kok / "clap_parca" / f"{pid}.npy", v.astype("float32"))
        for i, (ad, karar) in enumerate(kararlar):
            aday_id = f"ad{i}"
            conn.execute(
                "INSERT INTO adaylar (aday_id, calisma_id, eksen, strateji, "
                "artist, title, skor, gerekce) VALUES (?,'c1',0,'x',?,?,1,'g')",
                (aday_id, ad, f"{ad} albümü"))
            conn.execute(
                "INSERT INTO feedback (aday_id, karar, tarih, calisma_id) "
                "VALUES (?,?,'2026-09-06','c1')", (aday_id, karar))
    return conn


def _bv(*x):
    import numpy as np
    v = np.array(x, dtype="float32")
    return v / np.linalg.norm(v)


def test_karar_yoksa_etki_yok():
    """Hiç beğendim/tutmadı yoksa sıralama dokunulmadan kalmalı."""
    import tempfile

    from python.geri_bildirim import yakinlik_etkisi

    with tempfile.TemporaryDirectory() as tmp:
        conn = _etki_ortami(tmp, [], {"a": _bv(1, 0, 0)})
        assert yakinlik_etkisi(conn) == {}


def test_begenilene_benzeyen_yukari_tutmayana_benzeyen_asagi():
    """Döngünün kendisi: karar sıralamayı doğru YÖNDE kaydırmalı."""
    import tempfile

    from python.geri_bildirim import yakinlik_etkisi

    with tempfile.TemporaryDirectory() as tmp:
        conn = _etki_ortami(
            tmp,
            kararlar=[("Sevilen", "begendim"), ("Sevilmeyen", "tutmadi")],
            havuz={"Sevilen": _bv(1, 0, 0), "Sevilmeyen": _bv(0, 1, 0),
                   "SevilenGibi": _bv(0.98, 0.2, 0),
                   "SevilmeyenGibi": _bv(0.2, 0.98, 0)},
        )
        etki = yakinlik_etkisi(conn)
        assert etki["sevilengibi"][0] > 0, etki
        assert etki["sevilmeyengibi"][0] < 0, etki


def test_yargilanan_sanatci_kendi_etkisini_almaz():
    """Karar verdiğin sanatçının kendi kararı var; benzerlikle ikinci kez itilmez."""
    import tempfile

    from python.geri_bildirim import yakinlik_etkisi

    with tempfile.TemporaryDirectory() as tmp:
        conn = _etki_ortami(
            tmp, [("Sevilen", "begendim")],
            {"Sevilen": _bv(1, 0, 0), "Baska": _bv(0.9, 0.4, 0)},
        )
        etki = yakinlik_etkisi(conn)
        assert "sevilen" not in etki, etki


def test_etki_sinirli():
    """Etki [-1, +1] dışına çıkmamalı; tavan sunucuda σ ile çarpılıyor."""
    import tempfile

    from python.geri_bildirim import ETKI_TAVANI, yakinlik_etkisi

    assert 0 < ETKI_TAVANI <= 1, "tavan kararları devirecek kadar büyük"
    with tempfile.TemporaryDirectory() as tmp:
        conn = _etki_ortami(
            tmp, [("Sevilen", "begendim"), ("Sevilmeyen", "tutmadi")],
            {"Sevilen": _bv(1, 0, 0), "Sevilmeyen": _bv(0, 1, 0),
             "X": _bv(1, 0.05, 0), "Y": _bv(0.05, 1, 0), "Z": _bv(0, 0, 1)},
        )
        for pay, _ in yakinlik_etkisi(conn).values():
            assert -1.0 <= pay <= 1.0, pay


for _ad, _fn in sorted(list(globals().items())):
    if _ad.startswith("test_") and callable(_fn):
        _kosul(_ad, _fn)

print("—" * 40)
if _kalan:
    print(f"{len(_kalan)} test kaldı")
    raise SystemExit(1)
print("tüm testler geçti")
