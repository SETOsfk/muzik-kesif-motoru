"""Öneri gerekçesi — gösterim anında, iki dilde, KANITIN GÜCÜYLE (2026-09-23).

## Neden saklanan metin değil

Gerekçe aday üretilirken Türkçe cümle olarak `adaylar.gerekce`ye yazılıyordu.
Üç sorun çıktı:

1. İki dil: saklanmış Türkçe cümle İngilizce arayüzde gösterilemez.
2. Doğal olmayan dil: "Kulağa senin X albümüne benziyor" — "sounds like"ın
   kelime kelime çevirisi. Türkçede "kulağa ... gibi gelir" ya da "... andırır".
3. Fazla iddia: melez gerekçesi "İKİ SİNYAL DE işaret ediyor. Tek başına hiçbir
   sinyal bu kadarını söylemiyordu" diyordu. Ölçüldü: Sezen Aksu'yu «grunge»
   eksenine taşıyan iki sinyal BAĞIMSIZ DEĞİLDİ — ikisi de dil sinyaliydi
   (Duman ile yalnız 3 ortak liste, ikisi "her şey karışık" kişisel listeler,
   biri "türkçe" adlı; ve Şebnem Ferah'ın sesine yakınlık). "İki sinyal"
   ifadesi kanıtı olduğundan güçlü gösteriyordu.

Sayılar `adaylar.dayanak`ta (JSON) zaten duruyor (K7). Burada o sayılardan
cümle kuruluyor: aynı veri, iki dil, ve kanıtın gücü AÇIKÇA — "yalnız 3
listeye dayanıyor" gibi. Kullanıcı sayıyı görüp kendi yargısını verebilir.

Dayanağı yetmeyen eski satırlarda (kadro grafiği stratejileri) Türkçede
saklanan metin kullanılır; İngilizcede dayanaktaki alanlardan genel bir cümle.
"""

from __future__ import annotations

import json
import re

from python.dil import dil, sayi, t

#: Bu sayıdan az ortak listeye dayanan bağ "zayıf kanıt" olarak işaretlenir.
#: 3: `asgari_liste=2` eşiğinin hemen üstü; Sezen Aksu bağı 3 listeydi.
ZAYIF_LISTE = 3

_BENZEDIGI = re.compile(r"senin «(.+?)» albüm")


def _dayanak(ham) -> dict:
    if isinstance(ham, dict):
        return ham
    try:
        return json.loads(ham or "{}")
    except (TypeError, ValueError):
        return {}


def _kaynak_adlari(anahtarlar: list[str], adlar: dict[str, str]) -> str:
    """Normalize anahtarları ("duman") okunur adlara ("Duman") çevir."""
    okunur = [adlar.get(a, a.title()) for a in anahtarlar if a][:3]
    if not okunur:
        return ""
    if len(okunur) == 1:
        return okunur[0]
    ve = t(" ve ", " and ")
    return ", ".join(okunur[:-1]) + ve + okunur[-1]


def _liste_cumlesi(d: dict, eksen: str, adlar: dict[str, str]) -> str:
    n = int(d.get("birlikte_liste") or 0)
    guc = sayi(d.get("pmi"), 2, isaret=True)
    kaynak = _kaynak_adlari(d.get("kaynak_sanatcilar") or [], adlar)
    kimle = kaynak or t(f"«{eksen}» sanatçıların", f"your «{eksen}» artists")
    cumle = t(
        f"Çalma listelerinde {kimle} ile yan yana duruyor: {n} ayrı listede "
        f"birlikte, bağ gücü {guc}.",
        f"Shows up alongside {kimle} in playlists: together in {n} separate "
        f"lists, link strength {guc}.",
    )
    if n and n <= ZAYIF_LISTE:
        cumle += " " + t(
            f"Zayıf kanıt: yalnız {n} listeye dayanıyor ve bu tür bağlar dil ya "
            f"da ruh hâli listelerinden de gelebiliyor.",
            f"Weak evidence: it rests on only {n} lists, and links like this can "
            f"come from language or mood playlists rather than style.",
        )
    return cumle


def _ses_cumlesi(benzedigi: str, d: dict | None = None) -> str:
    """Tek albüm yerine birden çok parça/albüm kanıtı varsa onu söyler."""
    d = d or {}
    albumler = [a for a in (d.get("benzedikleri") or []) if a][:3]
    parca = d.get("parca_sayisi") or 0
    if len(albumler) >= 2:
        liste = ", ".join(f"«{a}»" for a in albumler)
        parca_tr = f"{parca} parçası" if parca and parca > 1 else "Sesi"
        parca_en = f"{parca} of its tracks" if parca and parca > 1 else "Its sound"
        return t(
            f"{parca_tr} kütüphanendeki birden çok albüme yakın: {liste}. "
            f"Tek bir klibin tesadüfü değil; birkaç ses aynı yönü gösteriyor.",
            f"{parca_en} sit close to several albums in your library: {liste}. "
            f"Not one lucky clip; several sounds point the same way.")
    return t(
        f"Sesi, kütüphanendeki «{benzedigi}» albümünü andırıyor. Bu bir tür "
        f"etiketi ya da ortak kadro değil; iki albümün sesi gerçekten birbirine yakın.",
        f"Its sound is close to «{benzedigi}» from your library. Not a genre "
        f"tag or a shared lineup: the two records genuinely sound alike.",
    )


def gerekce(strateji: str, dayanak, *, eksen: str, saklanan: str = "",
            adlar: dict[str, str] | None = None) -> str:
    """Adayın gerekçesi, etkin dilde.

    `adlar`: {normalize_esleme(ad): okunur ad} — kütüphane sanatçıları.
    `saklanan`: `adaylar.gerekce` (Türkçe) — yedek olarak ve melez satırlarında
    benzediği albümün adını çıkarmak için.
    """
    d = _dayanak(dayanak)
    adlar = adlar or {}
    benzedigi = d.get("benzedigi")
    if not benzedigi and saklanan:
        m = _BENZEDIGI.search(saklanan)
        benzedigi = m.group(1) if m else None

    if strateji == "liste_birlikteligi" and "pmi" in d:
        return _liste_cumlesi(d, eksen, adlar)
    if strateji == "ses_benzerligi" and benzedigi:
        return _ses_cumlesi(benzedigi, d) + " " + t(
            "Her şeye benzeyen kayıtlar öne çıkmasın diye skor düzeltildi.",
            "The score is corrected so that tracks resembling everything don't float up.")
    if strateji == "melez":
        parcalar = []
        if "pmi" in d:
            parcalar.append(_liste_cumlesi(d, eksen, adlar))
        if benzedigi:
            parcalar.append(_ses_cumlesi(benzedigi, d))
        if parcalar:
            return " ".join(parcalar)
    # Kadro grafiği stratejileri ve eski satırlar.
    if dil() == "tr" and saklanan:
        return saklanan
    return _genel(strateji, d, eksen, saklanan)


def _genel(strateji: str, d: dict, eksen: str, saklanan: str) -> str:
    """Dayanağı yapılandırılmış olmayan satırlar için genel cümle."""
    if strateji == "kredi_sicramasi":
        kisi = d.get("kisi") or d.get("muzisyen") or d.get("kisiler")
        if isinstance(kisi, list):
            kisi = ", ".join(map(str, kisi[:3]))
        if kisi:
            return t(f"Kadrosunda {kisi} var; aynı müzisyen senin «{eksen}» tarzındaki albümlerde de çalıyor.",
                     f"{kisi} plays on it, who also plays on records in your «{eksen}» style.")
        return t(f"«{eksen}» tarzındaki müzisyenlerin başka bir kaydı.",
                 f"Another record by musicians from your «{eksen}» style.")
    if strateji == "sahne_komsulugu":
        return t(f"«{eksen}» tarzındaki sanatçıları dinleyenlerin sık açtığı bir isim.",
                 f"An artist often played by people who listen to your «{eksen}» artists.")
    if strateji == "bilincli_uzaklik":
        return t(f"Bilerek biraz uzağa: «{eksen}» tarzının komşularının komşusu.",
                 f"A deliberate step away: a neighbour of your «{eksen}» neighbours.")
    return saklanan or t("Gerekçe kaydı yok.", "No recorded reason.")


def geri_bildirim_cumlesi(yon: str, sanatci: str) -> str:
    """Kararların sıralamaya etkisi — "aynı sesten" değil: benzerlik göreli."""
    if yon == "arti":
        return t(f"👍 dediğin «{sanatci}» ile benzer bir sesi var",
                 f"Sounds closer to «{sanatci}», which you liked")
    return t(f"👎 dediğin «{sanatci}» ile benzer bir sesi var",
             f"Sounds closer to «{sanatci}», which you passed on")


STRATEJI_ADI = {
    "melez": ("liste + ses", "playlists + sound"),
    "liste_birlikteligi": ("çalma listelerinden", "from playlists"),
    "ses_benzerligi": ("sesi benziyor", "similar sound"),
    "kredi_sicramasi": ("kadrondaki müzisyenler", "musicians you know"),
    "sahne_komsulugu": ("1 adım: komşular", "1 step: neighbours"),
    "bilincli_uzaklik": ("2 adım: bilinçli uzaklık", "2 steps: deliberate distance"),
}


def strateji_adi(strateji: str) -> str:
    tr, en = STRATEJI_ADI.get(strateji, (strateji, strateji))
    return t(tr, en)
