"""Metin normalizasyonu ve albüm kimliği.

Hem tarayıcı hem dinleme logu aynı normalizasyonu kullanır: aksi halde
"Meddle (2011 Remaster)" ile "Meddle" farklı albüm sayılır.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

# NFKD Türkçe 'ı' ve 'ğ' için işe yaramaz; elle eşlenir.
_TR_HARF = str.maketrans(
    {
        "ı": "i", "İ": "i", "I": "i",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u",
        "ö": "o", "Ö": "o",
        "ç": "c", "Ç": "c",
    }
)

# Parantez içi ancak bu kelimelerden birini içeriyorsa atılır. Körlemesine
# parantez silmek "III (Wisdom)" gibi anlamlı başlıkları bozar.
GURULTU_SOZCUKLERI = frozenset(
    {
        "remaster", "remastered", "remasterizado", "deluxe", "edition", "expanded",
        "reissue", "bonus", "tracks", "track", "disc", "disk", "cd", "vinyl", "lp",
        "anniversary", "version", "special", "limited", "japanese", "japan",
        "import", "mono", "stereo", "explicit", "single", "ep", "digipak",
    }
)

_PARANTEZ = re.compile(r"[\(\[\{]([^\(\)\[\]\{\}]*)[\)\]\}]")
_ALFANUMERIK_DISI = re.compile(r"[^a-z0-9]+")
_YIL = re.compile(r"(\d{4})")


def _gurultu_mu(parca: str) -> bool:
    """Parantez içi ya da tire sonrası parça sadece gürültüden mi ibaret?"""
    sozcukler = [s for s in _ALFANUMERIK_DISI.split(parca.lower()) if s]
    if not sozcukler:
        return True
    return all(s in GURULTU_SOZCUKLERI or s.isdigit() for s in sozcukler)


def normalize(metin: str | None) -> str:
    """Eşleştirme için kanonik biçim: aksansız, küçük harf, gürültüsüz."""
    if not metin:
        return ""
    metin = _PARANTEZ.sub(lambda m: "" if _gurultu_mu(m.group(1)) else f" {m.group(1)} ", metin)

    # "Aja - 2011 Remaster" → "Aja"
    if " - " in metin:
        bas, _, son = metin.rpartition(" - ")
        if bas.strip() and _gurultu_mu(son):
            metin = bas

    metin = metin.translate(_TR_HARF)
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(k for k in metin if not unicodedata.combining(k))
    ascii_hali = _ALFANUMERIK_DISI.sub(" ", metin.lower()).strip()

    # CJK ve benzeri Latin dışı yazılar ASCII süzgecinden tamamen boş çıkıyor:
    # "ウチュウノアバレンボー" → "". Boş anahtar felakettir — bütün Japonca
    # başlıklar birbirine eşit sayılır ve yanlış eşleşir. Böyle durumda özgün
    # metnin temizlenmiş hâline geri düşülür (harfler korunur).
    # Kütüphanede şu an etkilenen albüm YOK (ölçüldü), yani album_id'ler oynamaz.
    if not ascii_hali:
        korunmus = re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", metin, flags=re.UNICODE))
        return korunmus.strip().lower()
    metin = ascii_hali

    # Yalnızca baştaki artikel atılır; "The The" bozulmasın diye içeridekiler kalır.
    for artikel in ("the ", "a ", "an "):
        if metin.startswith(artikel) and len(metin) > len(artikel):
            metin = metin[len(artikel):]
            break
    return metin


# --------------------------------------------------------------------------- #
# Eşleştirme normalizasyonu — kimlikten AYRI ve gelişmeye açık
# --------------------------------------------------------------------------- #
# `normalize()` album_id üretiminde kullanılır ve DONDURULMUŞTUR: değiştirilirse
# kütüphanedeki albümlerin kimliği değişir, mevcut krediler/etiketler sahipsiz
# kalır (ölçüldü: TOOL — Ænima ligatür yüzünden kimlik değiştirirdi).
#
# Dış kaynaklarla eşleştirme ise sürekli iyileşmesi gereken bir iş. O yüzden
# aşağıdaki geniş normalizasyon ayrı tutuldu: burada istediğimiz kadar kural
# ekleyebiliriz, hiçbir albümün kimliği oynamaz.

_LIGATUR = str.maketrans({
    "œ": "oe", "Œ": "oe", "æ": "ae", "Æ": "ae",
    "ß": "ss", "ø": "o", "Ø": "o", "đ": "d", "ð": "d", "þ": "th", "ł": "l",
})

# Parantez içi bu öneklerden biriyle başlayan sözcük içeriyorsa gürültü sayılır.
# "Remasterisé", "Remastered", "Remasterizado" tek kuralla kapsanır.
GURULTU_ONEKLERI = ("remaster", "anniversar", "jubilee", "reissue", "digipak")

_FEAT = re.compile(r"\s*\b(feat|ft|featuring|with)\b\.?\s.*$", re.IGNORECASE)


def _gurultu_mu_genis(parca: str) -> bool:
    sozcukler = [s for s in _ALFANUMERIK_DISI.split(parca.lower()) if s]
    if not sozcukler:
        return True
    # 1–2 harfli bağlaçlar karar vermez: "(Remasterisé en 2016)" içindeki "en"
    # yüzünden parantezin tamamı anlamlı sayılmamalı. Ama hepsi bu kadarsa
    # (örn. "(II)") anlamlı kabul edilir — bilgi taşıyor olabilir.
    anlamlilar = [s for s in sozcukler if len(s) > 2]
    if not anlamlilar:
        return False
    return all(
        s in GURULTU_SOZCUKLERI or s.isdigit() or s.startswith(GURULTU_ONEKLERI)
        for s in anlamlilar
    )


def normalize_esleme(metin: str | None) -> str:
    """Dış kaynak eşleştirmesi için geniş normalizasyon.

    `normalize()`ye ek olarak: ligatürler açılır (Ænima → aenima), "feat ..."
    kuyruğu atılır, gürültü sözcükleri önek olarak eşleşir.

    album_id üretiminde KULLANILMAZ — kimlik `normalize()`ye bağlı kalmalı.
    """
    if not metin:
        return ""
    metin = _FEAT.sub("", metin.translate(_LIGATUR))
    metin = _PARANTEZ.sub(
        lambda m: "" if _gurultu_mu_genis(m.group(1)) else f" {m.group(1)} ", metin
    )
    if " - " in metin:
        bas, _, son = metin.rpartition(" - ")
        if bas.strip() and _gurultu_mu_genis(son):
            metin = bas
    return normalize(metin)


def ayni_kisi_mi(a: str | None, b: str | None) -> bool:
    """Sanatçı adları aynı kişiyi mi gösteriyor?

    Sözcük sırası yok sayılır: MusicBrainz kimi kaydı sıralama adıyla döndürür
    ("Borlai Gergő" ↔ "Gergő Borlai"). Kapsama sayılmaz — "Jeff Beck" ile
    "Jeff Beck Group" farklı varlıklardır ve insana sorulmalıdır.
    """
    na, nb = normalize_esleme(a), normalize_esleme(b)
    if not na or not nb:
        return False
    return na == nb or sorted(na.split()) == sorted(nb.split())


def yil_ayikla(ham: str | int | None) -> int | None:
    """'1977-10-14', '1977', 1977 → 1977. Ayrıştırılamazsa None."""
    if ham is None:
        return None
    if isinstance(ham, int):
        return ham if 1500 < ham < 2200 else None
    eslesme = _YIL.search(str(ham))
    if not eslesme:
        return None
    yil = int(eslesme.group(1))
    return yil if 1500 < yil < 2200 else None


def album_anahtari(artist: str | None, album: str | None, yil: int | None = None) -> str:
    """Normalize edilmiş eşleştirme anahtarı (insan okuyabilir, kimlik değil)."""
    return f"{normalize(artist)}|{normalize(album)}|{yil or ''}"


def album_kimligi(artist: str | None, album: str | None, yil: int | None = None) -> str:
    """album_id — sanatçı+albüm+yıl üzerinden yerel, kararlı hash."""
    ham = album_anahtari(artist, album, yil)
    return hashlib.sha1(ham.encode("utf-8")).hexdigest()[:16]
