"""İki dil — Türkçe ve İngilizce (2026-09-23).

## Neden anahtar kataloğu değil, satır içi çift

İki dilli bir arayüzün klasik yolu `_("oneriler.baslik")` gibi anahtarlar ve
ayrı çeviri dosyalarıdır. Burada iki dil var ve ikisi de DOĞAL görünmek
zorunda; anahtar kataloğunda çevirmen cümleyi bağlamından kopuk görür ve
"sounds like"tan "kulağa benziyor" gibi kelime kelime çeviriler doğar
(arayüzde gerçekten vardı). `t("Türkçe", "English")` iki cümleyi yan yana
tutar: biri değişince öteki gözün önünde.

## Etkin dil

İstek başına bir bağlam değişkeninde (`AKTIF_DIL`), tıpkı etkin kullanıcı
gibi: web ara katmanı çerezden (yoksa tarayıcının `Accept-Language`'ından)
okuyup yerleştirir. Böylece `python/` altındaki cümle üreten işlevler
(gerekçe, profil cümleleri) imza değiştirmeden iki dilde konuşur. Komut
satırında değişken ayarlanmaz; varsayılan Türkçe.

## Sayılar

Türkçede ondalık ayırıcı virgül (0,53), İngilizcede nokta (0.53). `sayi()`
ikisini de doğru yazar; ekranda "0.53" gören Türk okur yabancı bir metin
okuduğunu hisseder.
"""

from __future__ import annotations

from contextvars import ContextVar

DILLER = ("tr", "en")
VARSAYILAN_DIL = "tr"
DIL_CEREZI = "kesif_dil"

AKTIF_DIL: ContextVar[str] = ContextVar("aktif_dil", default=VARSAYILAN_DIL)


def dil() -> str:
    return AKTIF_DIL.get()


def t(tr: str, en: str) -> str:
    """Etkin dile göre metin. İki dil de her zaman yazılır — biri boş kalamaz."""
    return en if AKTIF_DIL.get() == "en" else tr


def istekten_dil(cerez: str | None, kabul: str | None) -> str:
    """Çerez varsa o; yoksa tarayıcının ilk tercih ettiği desteklenen dil.

    `Accept-Language: en-US,en;q=0.9,tr;q=0.8` → en. Türkçe dışındaki her
    dil İngilizceye düşer: Almanca konuşan biri için İngilizce, Türkçeden
    daha büyük olasılıkla okunur.
    """
    if cerez in DILLER:
        return cerez
    for parca in (kabul or "").split(","):
        kod = parca.split(";")[0].strip().lower()[:2]
        if kod == "tr":
            return "tr"
        if kod:
            return "en"
    return VARSAYILAN_DIL


def sayi(deger, basamak: int = 2, *, isaret: bool = False) -> str:
    """Dile göre ondalık: 0,53 / 0.53. None ve NaN → «—»."""
    if deger is None:
        return "—"
    try:
        x = float(deger)
    except (TypeError, ValueError):
        return str(deger)
    if x != x:          # NaN
        return "—"
    metin = f"{x:+.{basamak}f}" if isaret else f"{x:.{basamak}f}"
    return metin.replace(".", ",") if AKTIF_DIL.get() == "tr" else metin


def yuzde(deger, basamak: int = 0) -> str:
    """%53 (Türkçe, işaret önde) / 53% (İngilizce, işaret sonda)."""
    if deger is None:
        return "—"
    metin = sayi(float(deger) * 100, basamak)
    return f"%{metin}" if AKTIF_DIL.get() == "tr" else f"{metin}%"


def bas_harf_buyuk(metin: str) -> str:
    """İlk harfi büyüt — Türkçede i→İ, ı→I. `str.capitalize()` "insan"ı
    "Insan" yapar ve geri kalanı küçültür; ikisi de Türkçede yanlış."""
    if not metin:
        return metin
    ilk = metin[0]
    if AKTIF_DIL.get() == "tr":
        ilk = {"i": "İ", "ı": "I"}.get(ilk, ilk.upper())
    else:
        ilk = ilk.upper()
    return ilk + metin[1:]
