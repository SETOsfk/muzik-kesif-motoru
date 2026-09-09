"""İcra profili (dört stem) ve rol-duyarlı benzerlik testleri.

Demucs/librosa çağrılmaz — ses gerektiren kısım ayrı, saf kısım testli.
Buradaki asıl mesele ölçüt DAVRANIŞI: kalite koruması eleme yapıyor mu, benzerlik
gerçekten icra özniteliklerine mi bakıyor.

    .venv/bin/python tests/test_davul.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import numpy as np
    import pandas as pd
except ImportError:  # pragma: no cover
    print("numpy/pandas yok — .venv/bin/python ile çalıştırın")
    raise SystemExit(0)

from python.db import baglan
from python.enrich.davul_profili import DavulOzellik, ozetle
from python.enrich.icra_profili import ROL_STEM, stem_ozellikleri
from python.muzisyen import (
    ROL_SUTUNLARI,
    benzer_icracilar,
    icra_profilleri,
    muzisyen_verisi,
)
davul_profilleri = icra_profilleri


def _ozellik(**degisiklikler) -> DavulOzellik:
    varsayilan = dict(
        nota_vurus=2.0, izgara_entropi=0.95, tekme_payi=0.25,
        trampet_payi=0.40, zil_payi=0.35, dinamik_db=20.0, tempo=120.0,
    )
    varsayilan.update(degisiklikler)
    return DavulOzellik(**varsayilan)


# --------------------------------------------------------------------------- #
# Özetleme
# --------------------------------------------------------------------------- #

def test_ozet_medyan_alir():
    ozet = ozetle([_ozellik(nota_vurus=1.0), _ozellik(nota_vurus=2.0), _ozellik(nota_vurus=9.0)])
    assert ozet["nota_vurus"] == 2.0, "aykırı klip medyanı kaçırmamalı"


def test_bos_liste_none():
    assert ozetle([]) is None


def test_ozet_tum_alanlari_tasir():
    ozet = ozetle([_ozellik()])
    assert set(ozet) == {
        "nota_vurus", "izgara_entropi", "tekme_payi",
        "trampet_payi", "zil_payi", "dinamik_db", "tempo",
    }


# --------------------------------------------------------------------------- #
# İcra benzerliği
# --------------------------------------------------------------------------- #

def _profilli_db():
    """Üç davulcu: ikisi benzer icra, biri tamamen farklı."""
    conn = baglan(":memory:")
    with conn:
        conn.executemany(
            """INSERT INTO davul_profili
               (kisi_anahtar, rol, kisi_adi, nota_vurus, izgara_entropi,
                tekme_payi, trampet_payi, zil_payi, dinamik_db, tempo,
                klip_sayisi, ornek_onizleme)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                # Yoğun, ride ağırlıklı, insan icrası
                ("a", "drums", "Yoğun A", 3.8, 0.99, 0.20, 0.25, 0.55, 20.0, 130, 2, "u1"),
                ("b", "drums", "Yoğun B", 3.6, 0.98, 0.22, 0.27, 0.51, 21.0, 128, 2, "u2"),
                # Seyrek, programlanmış, trampet ağırlıklı
                ("c", "drums", "Makine C", 1.2, 0.70, 0.38, 0.48, 0.14, 55.0, 95, 2, "u3"),
            ],
        )
    return conn


def test_benzerlik_icra_profiline_bakar():
    conn = _profilli_db()
    veri = muzisyen_verisi(conn, None)     # kredi yok → tür merkezi boş
    profiller = davul_profilleri(conn)
    conn.close()

    tablo, temel = benzer_icracilar(veri, profiller, "a", adet=5, icra_agirligi=1.0)
    assert not tablo.empty
    # Yoğun A'ya en yakın Yoğun B olmalı, Makine C değil.
    assert tablo.iloc[0]["kisi_adi"] == "Yoğun B", tablo[["kisi_adi", "benzerlik"]].to_dict()
    assert tablo.iloc[0]["benzerlik"] > tablo.iloc[-1]["benzerlik"]
    assert "stem" in temel


def test_hedef_kendisi_listede_yok():
    conn = _profilli_db()
    veri = muzisyen_verisi(conn, None)
    profiller = davul_profilleri(conn)
    conn.close()
    tablo, _ = benzer_icracilar(veri, profiller, "a", adet=5)
    assert "a" not in tablo.index


def test_profil_yoksa_anlasilir_mesaj():
    conn = baglan(":memory:")
    veri = muzisyen_verisi(conn, None)
    profiller = davul_profilleri(conn)
    conn.close()
    tablo, temel = benzer_icracilar(veri, profiller, "yok")
    assert tablo.empty
    assert "profil" in temel.lower()


def test_onizleme_url_tasinir():
    """Kullanıcı DUYABİLMELİ — benzerlik tablosu klip URL'sini taşımalı."""
    conn = _profilli_db()
    veri = muzisyen_verisi(conn, None)
    profiller = davul_profilleri(conn)
    conn.close()
    tablo, _ = benzer_icracilar(veri, profiller, "a", adet=5)
    assert "ornek_onizleme" in tablo.columns
    assert tablo["ornek_onizleme"].notna().all()


def test_standartlastirma_siralamayi_degistirir():
    """Ham kosinüs pozitif bölgede herkesi benzer yapıyordu; z ile ayrışmalı."""
    from python.muzisyen import _kosinus

    cerceve = pd.DataFrame(
        {"x": [1.0, 1.1, 5.0], "y": [1.0, 0.9, 5.0]}, index=["a", "b", "c"]
    )
    ham = _kosinus(cerceve, "a", standartlastir=False)
    z_ile = _kosinus(cerceve, "a", standartlastir=True)
    # Ham hâlde c de a'ya çok benzer görünür (aynı yön), z ile ayrışır.
    assert ham["c"] > 0.99
    assert z_ile["c"] < ham["c"]


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


# --------------------------------------------------------------------------- #
# Rol-duyarlı ölçüt kümeleri (dört stem genellemesi)
# --------------------------------------------------------------------------- #

def test_her_rol_kendi_olcutunu_kullanir():
    """Davulda perde, vokalde tekme payı aranmaz."""
    assert "izgara_entropi" in ROL_SUTUNLARI["drums"]
    assert "perde_medyan" not in ROL_SUTUNLARI["drums"]
    assert "perde_medyan" in ROL_SUTUNLARI["bass"]
    assert "vibrato_hizi" in ROL_SUTUNLARI["vocals"]
    assert "tekme_payi" not in ROL_SUTUNLARI["vocals"]
    # Aynı stem'den beslenen roller aynı ölçütü paylaşır (Demucs gitar/klavyeyi ayırmıyor).
    assert ROL_SUTUNLARI["keyboards"] == ROL_SUTUNLARI["guitar"]
    assert ROL_SUTUNLARI["percussion"] == ROL_SUTUNLARI["drums"]


def test_rol_stem_eslemesi_tam():
    """Ölçüt kümesi tanımlı her rolün bir stem karşılığı olmalı."""
    for rol in ROL_SUTUNLARI:
        assert rol in ROL_STEM, f"{rol} için stem eşlemesi yok"
    assert ROL_STEM["guitar"] == ROL_STEM["keyboards"] == "other"
    assert ROL_STEM["percussion"] == "drums"


def test_bos_stem_olcum_uretmez():
    """Neredeyse sessiz stem'de sayı uydurulmamalı — None dönmeli."""
    sessiz = np.zeros(22050 * 3, dtype=np.float32)
    assert stem_ozellikleri(sessiz, 22050, "bass", toplam_enerji=1e6) is None


def test_eksik_olcum_kisiyi_elemez():
    """Perde çıkmamış bir klip, kişinin diğer ölçütlerini çöpe atmamalı."""
    profiller = pd.DataFrame(
        {
            "kisi_adi": ["A", "B", "C"],
            "nota_vurus": [3.0, 2.9, 1.2],
            "perde_medyan": [30.0, np.nan, 31.0],   # B'nin perdesi ölçülememiş
            "perde_araligi": [12.0, 11.0, 5.0],
            "sustain_orani": [0.5, 0.52, 0.2],
            "parlaklik": [900.0, 880.0, 400.0],
            "duzluk": [0.02, 0.02, 0.1],
            "dinamik_db": [20.0, 21.0, 8.0],
        },
        index=["a", "b", "c"],
    )
    veri = muzisyen_verisi(baglan(":memory:"), None)
    tablo, _ = benzer_icracilar(veri, profiller, "a", rol="bass", adet=3, icra_agirligi=1.0)
    assert "b" in tablo.index, "eksik perde yüzünden B elenmemeli"
    assert tablo.iloc[0]["kisi_adi"] == "B"


# --------------------------------------------------------------------------- #
# sustain_orani — ikinci tanım. İlki (RMS tepenin %20'sinin üstünde kalan kare
# oranı) sürekli çalan stem'de 1.00'e yapışıyordu; bu testler yeni tanımın
# staccato ile uzun notayı gerçekten ayırdığını sabitliyor.
# --------------------------------------------------------------------------- #

def _darbe_dizisi(sr: int, cursor: float, bosluk: float, adet: int = 8) -> tuple:
    """`cursor` saniye çalıp `bosluk` saniye susan notalar; RMS zarfı ve onsetler."""
    hop = 512
    kare_sn = hop / sr
    toplam = int((cursor + bosluk) * adet / kare_sn)
    rms = np.zeros(toplam)
    onsetler = []
    for i in range(adet):
        bas_sn = i * (cursor + bosluk)
        bas = int(bas_sn / kare_sn)
        son = int((bas_sn + cursor) / kare_sn)
        if son >= toplam:
            break
        # atakta tepe, sonra üstel çürüme
        n = son - bas
        rms[bas:son] = np.exp(-np.linspace(0, 4, n))
        onsetler.append(bas_sn)
    return rms, np.array(onsetler)


def test_sustain_staccatoyu_uzun_notadan_ayirir():
    from python.enrich.icra_profili import _sustain

    sr = 22050
    # Kısa nota + uzun boşluk: enerji bir sonraki onset'ten önce sıfıra iniyor.
    kisa_rms, kisa_on = _darbe_dizisi(sr, cursor=0.05, bosluk=0.45)
    # Uzun nota, boşluk yok: enerji taşınıyor.
    uzun_rms, uzun_on = _darbe_dizisi(sr, cursor=0.48, bosluk=0.02)

    kisa = _sustain(kisa_rms, kisa_on, sr)
    uzun = _sustain(uzun_rms, uzun_on, sr)
    assert kisa < uzun, f"staccato ({kisa:.3f}) uzun notadan ({uzun:.3f}) düşük olmalı"


def test_sustain_olcum_yoksa_nan():
    """Tek onset'ten çürüme okunamaz — sayı uydurulmamalı."""
    from python.enrich.icra_profili import _sustain

    assert np.isnan(_sustain(np.ones(100), np.array([0.0]), 22050))
    assert np.isnan(_sustain(np.array([]), np.array([0.0, 1.0]), 22050))


def test_elenen_olcutler_geri_gelmesin():
    """`duzluk` ve `tepe_orani` ölçülüp elendi; sessizce geri sızmasınlar."""
    from python.enrich.icra_profili import TUM_SUTUNLAR

    assert "duzluk" not in TUM_SUTUNLAR
    assert "tepe_orani" not in TUM_SUTUNLAR
    assert "harmonik_pay" in TUM_SUTUNLAR
