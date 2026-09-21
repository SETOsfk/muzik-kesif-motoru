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
