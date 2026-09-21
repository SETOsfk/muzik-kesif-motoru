"""Spotify jetonu şifreleme (`python/sifre.py`)."""

import os


def test_jeton_duz_metin_saklanmaz_ve_geri_cozulur():
    from python.sifre import ONEK, coz, sifrele

    s = sifrele("gizli-jeton")
    assert s.startswith(ONEK) and "gizli-jeton" not in s
    assert coz(s) == "gizli-jeton"
    assert sifrele(s) == s, "iki kez sarıldı"


def test_eski_duz_metin_okunmaya_devam_eder():
    from python.sifre import coz

    assert coz("eski-duz-jeton") == "eski-duz-jeton"
    assert coz(None) is None


def test_anahtar_degisirse_jeton_yok_sayilir(monkeypatch):
    """Kurcalanmış ya da başka anahtarla şifrelenmiş metin sessizce yanlış
    çözülmez: None döner, kullanıcı yeniden bağlanır."""
    from cryptography.fernet import Fernet

    import python.sifre as S

    s = S.sifrele("jeton")
    monkeypatch.setenv(S.ANAHTAR_DEGISKENI, Fernet.generate_key().decode("ascii"))
    assert S.coz(s) is None


def test_anahtar_yoksa_uretilir_ve_yazdirilmaz(tmp_path, monkeypatch, capsys):
    import python.sifre as S

    monkeypatch.delenv(S.ANAHTAR_DEGISKENI)
    monkeypatch.setattr(S, "ENV_DOSYASI", tmp_path / ".env")
    s = S.sifrele("jeton")
    anahtar = os.environ[S.ANAHTAR_DEGISKENI]
    assert f"{S.ANAHTAR_DEGISKENI}={anahtar}" in (tmp_path / ".env").read_text()
    cikti = capsys.readouterr()
    assert anahtar not in cikti.out + cikti.err, "anahtar ekrana yazıldı"
    assert oct((tmp_path / ".env").stat().st_mode)[-3:] == "600"
    assert S.coz(s) == "jeton"
