"""Saklanan sırların şifrelenmesi — şimdilik Spotify yenileme jetonu.

## Neden

Yenileme jetonu süresiz bir yetki: onu ele geçiren, kullanıcı iptal edene
kadar kütüphanesini okuyabilir. `kullanici.spotify_yenile` düz metin
duruyordu ve yayın planında veritabanı dosyası sunucuya TAŞINIYOR
(CLAUDE.md, "Sunmak için 47 MB yeter"). Dosyanın bir kopyası jetonların
kopyası demekti.

## Nasıl

Fernet (`cryptography`): AES-128-CBC + HMAC-SHA256, doğrulamalı — kurcalanmış
metin sessizce yanlış çözülmez, reddedilir. Elde yazılmış bir şifreleme
yerine standart ve denetlenmiş bir yapı; bağımlılık ücretsiz (K2).

Anahtar VERİTABANINDA DEĞİL, ortam değişkeninde (`KESIF_JETON_ANAHTARI`,
`.env`). Anahtarla şifreli metin aynı dosyada dursaydı şifrelemenin anlamı
kalmazdı. Anahtar yoksa ilk ihtiyaçta üretilip `.env`'ye eklenir; değeri
hiçbir yere YAZDIRILMAZ (değişmez kısıt).

## Geçiş ve kayıp

- Eski düz metin satırlar okunmaya devam eder (`coz` öneki tanır);
  `python -m python.hesap jetonlari-sifrele` hepsini şifreler.
- Anahtar kaybolursa jetonlar çözülemez → `coz` None döner ve kullanıcı
  Spotify'a yeniden bağlanır. Kayıp kurtarılabilir türden; bilinçli seçim.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ANAHTAR_DEGISKENI = "KESIF_JETON_ANAHTARI"
ONEK = "fernet:"

#: Anahtarın ekleneceği dosya. Modül geneli: testler yönlendirebilsin.
ENV_DOSYASI = Path(".env")


def _fernet():
    from cryptography.fernet import Fernet

    from python.onbellek import _env

    anahtar = _env(ANAHTAR_DEGISKENI)
    if not anahtar:
        anahtar = Fernet.generate_key().decode("ascii")
        yeni = not ENV_DOSYASI.exists()
        with ENV_DOSYASI.open("a", encoding="utf-8") as f:
            f.write(f"\n# Spotify jetonlarını şifreler (python/sifre.py). "
                    f"Kaybolursa kullanıcılar Spotify'a yeniden bağlanır.\n"
                    f"{ANAHTAR_DEGISKENI}={anahtar}\n")
        if yeni:
            ENV_DOSYASI.chmod(0o600)
        os.environ[ANAHTAR_DEGISKENI] = anahtar
        print(f"  {ANAHTAR_DEGISKENI} üretildi ve {ENV_DOSYASI} dosyasına eklendi",
              file=sys.stderr)
    return Fernet(anahtar.encode("ascii"))


def sifrele(duz: str | None) -> str | None:
    if not duz:
        return duz
    if duz.startswith(ONEK):
        return duz  # zaten şifreli; iki kez sarılmasın
    return ONEK + _fernet().encrypt(duz.encode("utf-8")).decode("ascii")


def coz(saklanan: str | None) -> str | None:
    """Şifreliyse çöz, eski düz metinse olduğu gibi. Çözülemiyorsa None."""
    if not saklanan:
        return None
    if not saklanan.startswith(ONEK):
        return saklanan
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(saklanan[len(ONEK):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None
