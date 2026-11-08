"""Tüm testler için ortak koruma.

Şifreleme anahtarı yoksa `python/sifre.py` onu üretip `.env`'ye YAZAR. Testler
gerçek `.env`'ye dokunmamalı: anahtar test başına geçici bir dosyaya
yönlendirilir ve ortam değişkeninde geçici bir anahtar tutulur.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def _gecici_sifre_anahtari(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet

    import python.sifre as S

    monkeypatch.setattr(S, "ENV_DOSYASI", tmp_path / ".env")
    monkeypatch.setenv(S.ANAHTAR_DEGISKENI, Fernet.generate_key().decode("ascii"))
    yield


@pytest.fixture(autouse=True)
def _aktarim_sureci_baslatilmaz(monkeypatch):
    """Testte GERÇEK aktarım süreci açılmaz.

    Alt süreç test yönlendirmelerini (KULLANICI_KOK) miras almaz ve varsayılan
    `data/` yoluna yazar. Ölçüldü (2026-09-28): Spotify girişi aktarımı kendiliğinden
    başlatınca bir test depo kökünde `data/db/kullanici/1.sqlite` yarattı. Kendi
    `Popen` sahtesini kuran testler bunu zaten ezer.
    """
    import subprocess

    gercek = subprocess.Popen

    class _Sahte:
        pid = 2 ** 22 + 11  # yaşamayan süreç

    def _koruma(arg, *a, **k):
        if isinstance(arg, (list, tuple)) and "python.aktarim" in arg:
            return _Sahte()
        return gercek(arg, *a, **k)

    monkeypatch.setattr(subprocess, "Popen", _koruma)


@pytest.fixture(autouse=True)
def _veri_kokleri_gecici(tmp_path, monkeypatch):
    """Hiçbir test depo kökündeki `data/`ya yazmaz: ortak ve kullanıcı
    veritabanı yolları her testte geçici dizine yönlenir. Ölçüldü (2026-11-08):
    iki web testi oturum ara katmanı üzerinden `data/db/ortak.sqlite` yaratıyordu;
    Mac'te bu, gerçek ortak veritabanıydı."""
    import python.db as D

    monkeypatch.setattr(D, "VARSAYILAN_ORTAK", tmp_path / "veri" / "ortak.sqlite")
    monkeypatch.setattr(D, "KULLANICI_KOK", tmp_path / "veri" / "kullanici")
