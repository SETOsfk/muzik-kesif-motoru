"""Çok sesli ses kuralı ve müzisyen bağlam süzgeci (2026-09-28)."""

import numpy as np

from python.etiket_clap import komsu_cogunlugu, sanatci_sirala


def test_tek_albume_benzeyen_parca_elenir():
    """Gabi Hartmann vakası: en yakın TEK albüm eksende, ama öbür komşular değil."""
    # 5 kütüphane albümü; ilk ikisi eksende.
    eksende = np.array([True, True, False, False, False])
    tum = np.array([
        [0.9, 0.1, 0.8, 0.7, 0.0],   # en yakın eksende ama 3 komşunun 1'i eksende
        [0.9, 0.8, 0.1, 0.0, 0.7],   # 3 komşunun 2'si eksende → geçer
    ])
    sayi, ort = komsu_cogunlugu(tum, eksende)
    assert list(sayi) == [1, 2]
    assert ort[1] == np.mean([0.9, 0.8])


def test_sanatci_birden_cok_parcayla_onerilir():
    sahipler = ["tek", "iki", "iki", "biri_gecen", "biri_gecen", "tek_sert"]
    sayi = np.array([2, 2, 3, 2, 0, 3])
    skor = np.array([0.9, 0.5, 0.7, 0.8, 0.9, 0.4])
    sonuc = sanatci_sirala(skor, sayi, sahipler)
    assert "tek" not in sonuc                    # tek parça, 3/3 değil
    assert sonuc["tek_sert"] == 0.4              # tek parça ama 3/3 eksende
    assert sonuc["iki"] == np.mean([0.7, 0.5])   # iki geçen parçanın ortalaması
    assert "biri_gecen" not in sonuc             # iki parçadan yalnız biri geçti


def test_muzisyen_destesi_uzak_sesi_eler(monkeypatch):
    import pandas as pd

    from python import kesif

    sonuc = pd.DataFrame({
        "aday_id": ["a1", "a2", "a3"], "artist": ["Gojira", "Lana Del Rey", "Bilinmez"],
        "title": ["x", "y", "z"], "year": [2016, 2012, 2020],
        "benzerlik": [0.7, 0.9, 0.6], "baglam": [0.9, 0.1, float("nan")],
    })
    monkeypatch.setattr("python.muzisyen.muzisyene_benzeyen_adaylar",
                        lambda *a, **k: (sonuc, 3))
    monkeypatch.setattr(kesif, "yargilanan_anahtarlar", lambda conn: set())
    monkeypatch.setattr(kesif, "kutuphane_adlari", lambda conn: {})

    class _Conn:
        def execute(self, *a, **k):
            class _R:
                def fetchone(self_):
                    return None
                def __iter__(self_):
                    return iter(())
            return _R()

    d = kesif.muzisyen_destesi(_Conn(), pd.DataFrame(), "joe duplantier", "vocals")
    # Kart kurulumu veritabanı ister; burada sıralama/süzgeç sayısına bakıyoruz.
    assert d["toplam"] == 2                      # Lana (bağlam 0,1) elendi; bilinmeyen kaldı
