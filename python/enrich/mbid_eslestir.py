"""Her albümü bir MusicBrainz release-group'a bağla.

MBID kanonik kimliktir: kredi, etiket ve ileride aday üretimi hep onun üzerinden
yürür. Yanlış bağlanmış bir albüm, yanlış kredileri kütüphaneye taşır — bu yüzden
otomatik kabul eşiği yüksek tutulur ve şüpheli olan her şey rapora düşer.

Karar:
  kesin   → normalize başlık ve sanatçı birebir tutuyor, yıl da uyuşuyor
  supheli → aday var ama tam tutmuyor (CSV'ye, elle onaya)
  yok     → hiç aday yok (CSV'ye)

Elle düzeltme döngüsü:
    python -m python.enrich.mbid_eslestir                      # eşleştir + rapor
    (CSV'deki mbid sütunu doldurulur)
    python -m python.enrich.mbid_eslestir --uygula rapor.csv   # elle kararı yaz

Kaldığı yerden devam eder: yalnızca `mbid IS NULL` olan albümlere bakar, ağdan
gelen her yanıt önbelleğe yazılır (K5).
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.metin import ayni_kisi_mi, normalize, normalize_esleme, yil_ayikla
from python.onbellek import AgYok, ApiIstemci, musicbrainz

VARSAYILAN_RAPOR = Path("data/raporlar/mbid_eslesmeyen.csv")

# MusicBrainz'in kendi skoru 0–100. 70 altındaki adaylara bakmaya değmez.
ASGARI_SKOR = 70


@dataclass(frozen=True)
class Aday:
    mbid: str
    artist: str
    title: str
    yil: int | None
    skor: int
    tur: str | None = None

    def ozet(self) -> str:
        return (
            f"{self.artist} — {self.title} ({self.yil or '?'}) "
            f"<{self.tur or '?'}> [{self.skor}] {self.mbid}"
        )


@dataclass
class Karar:
    durum: str  # kesin | supheli | yok
    aday: Aday | None
    adaylar: list[Aday]
    not_: str = ""


def adaylari_coz(govde: dict | None) -> list[Aday]:
    """MB arama yanıtını Aday listesine çevir."""
    if not govde:
        return []
    adaylar = []
    for ham in govde.get("release-groups", []):
        sanatcilar = " ".join(
            (kredi.get("artist") or {}).get("name", "") + (kredi.get("joinphrase") or "")
            for kredi in ham.get("artist-credit", [])
        ).strip()
        adaylar.append(
            Aday(
                mbid=ham["id"],
                artist=sanatcilar or "?",
                title=ham.get("title", ""),
                yil=yil_ayikla(ham.get("first-release-date")),
                skor=int(ham.get("score", 0)),
                tur=ham.get("primary-type"),
            )
        )
    return adaylar


def _tur_ile_ayir(tam_tutanlar: list[Aday], parca_sayisi: int | None) -> list[Aday]:
    """Aynı adlı albüm ve single'ı ayır.

    MusicBrainz'de "Notorious" hem albüm hem aynı adlı single olarak iki ayrı
    release-group. İkisi de aynı yıl olduğu için yıl ayıramıyor; ayıran şey
    parça sayısı: elimizde 12 parça varsa bu single değildir.

    Çıkarım TEK YÖNLÜ. "Çok parça → single değil" sağlam; tersi değil, çünkü
    parça sayısı yayının değil kullanıcının elindekinin ölçüsüdür. Deftones'un
    "Diamond Eyes (Deluxe)" albümünden tek parçası olan biri single almış olmaz —
    bu kural iki yönlü uygulandığında o albümü yanlışlıkla single'a bağlamıştı.
    """
    if parca_sayisi is None or parca_sayisi < 4:
        return tam_tutanlar  # az parça bir şey kanıtlamaz, insana bırak
    uyanlar = [a for a in tam_tutanlar if (a.tur or "") == "Album"]
    return uyanlar or tam_tutanlar


#: Baskı/sürüm süsü. MusicBrainz'in yayın grubu başlığında bunlar yok; etikette
#: neredeyse her zaman var. `normalize_esleme` bunların bir kısmını atıyor ama
#: apostrofu da boşluğa çeviriyor ("we're" → "we re") ve o hâliyle arama sorgusu
#: bozuluyor. Bu yüzden ARAMAYA ÖZEL bir temizleyici gerekiyor; kimlik
#: normalizasyonu (python/metin.py) dondurulmuş ve öyle kalmalı.
_SUS = re.compile(
    r"\s*[\(\[][^)\]]*\b(?:remaster(?:ed|isé|ise)?|remix|mono|stereo|deluxe|"
    r"expanded|edition|version|anniversary|bonus|reissue|ex-us|uk|us|japan|"
    r"\d{4})\b[^)\]]*[\)\]]",
    re.IGNORECASE,
)


def arama_basligi(title: str, artist: str = "") -> str:
    """Aramaya uygun başlık: baskı süsü atılmış, apostrof KORUNMUŞ.

    Üç şey yapıyor, üçü de ölçülmüş bir başarısızlıktan geliyor:
    - «We're An American Band (Remastered)» → «We're An American Band».
      `normalize_esleme` bunu «we re an american band» yapıyordu ve MusicBrainz
      bölünmüş sözcükle bulamıyordu.
    - «Françoise Hardy (L'amitié)» → «L'amitié». Sanatçı adı başlığa yapışmış;
      atılmazsa sorgu sanatçıyı iki kez arıyor.
    - Süs atılınca başlık boşalıyorsa (başlığın tamamı parantezdeydi) özgün
      hâl korunuyor.
    """
    temiz = _SUS.sub("", title).strip(" -–—·")
    if artist:
        n_art = normalize_esleme(artist)
        # «Sanatçı (Albüm)» ya da «Sanatçı - Albüm» kalıbı
        for ayrac in ("(", "-", "–", "—"):
            if ayrac in temiz:
                bas, _, kalan = temiz.partition(ayrac)
                if normalize_esleme(bas) == n_art and kalan.strip(" )"):
                    temiz = kalan.strip(" )")
                    break
    return temiz or title


#: MusicBrainz tipografik tire ve kesme işareti kullanıyor; dosya etiketleri
#: ASCII. «T‐SQUARE» (U+2010) ile «T-SQUARE» normalize edilince farklı sözcük
#: veriyordu. Kimlik normalizasyonu (python/metin.py) DONDURULMUŞ — albüm
#: kimlikleri ona bağlı — bu yüzden birleştirme yalnız burada, karşılaştırma
#: anında yapılıyor.
_TIRE = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015/&+"), " ")


def _sozcukler(ad: str) -> list[str]:
    """Karşılaştırma için sözcükler: tipografik ayraçlar boşluğa çevrilmiş."""
    return normalize_esleme(ad.translate(_TIRE)).split()


def _kadro_uyumu(etiket_ad: str, mb_ad: str) -> bool:
    """«Jeff Beck» ile «Jeff Beck Group» aynı kaydı gösteriyor mu?

    Dosya etiketi çoğu zaman GRUP LİDERİNİN adını taşıyor, MusicBrainz ise
    yayının kredilendiği kadro adını. Ölçüldü: «Jeff Beck — Truth» ve
    «Jimi Hendrix — Axis: Bold As Love» MusicBrainz'de skor 100 ve başlık
    birebir tutarken yalnızca bu yüzden şüpheli kalıyordu.

    Kural dar tutuldu: kısa adın HER SÖZCÜĞÜ uzun adda geçmeli ve kısa ad en
    az iki sözcük olmalı. «Beck» ⊂ «Jeff Beck» kabul edilmez; tek sözcüklük ad
    kapsama ile eşleştirilirse yanlış eşleşme kaçınılmaz.

    Ardışıklık ARANMIYOR ve bu ölçülmüş bir gerekçeye dayanıyor: «Yngwie
    Malmsteen» ↔ «Yngwie J. Malmsteen's Rising Force» — araya baş harf giriyor.
    Gevşemenin bedeli, `karar_ver`'in bu kuralı yalnız BAŞLIK BİREBİR TUTUYOR
    ve MusicBrainz skoru ≥95 iken kullanmasıyla ödeniyor.
    """
    a = set(_sozcukler(etiket_ad))
    b = set(_sozcukler(mb_ad))
    kisa, uzun = (a, b) if len(a) <= len(b) else (b, a)
    if len(kisa) < 2:
        return False
    # Kümeler EŞİTSE de doğru: aynı sözcükler, farklı sıra ya da tekrar.
    # «THE SQUARE / T-SQUARE» ile «T‐SQUARE» ikisi de {square, t} veriyor
    # (normalize «the»yi atıyor, tire boşluğa dönüyor) ve bunlar aynı grup.
    # Önceki sürümde buradaki «eşitse reddet» koruması onları reddediyordu.
    return kisa <= uzun


def karar_ver(
    artist: str,
    title: str,
    yil: int | None,
    adaylar: list[Aday],
    parca_sayisi: int | None = None,
) -> Karar:
    """Adaylar arasından seç. Emin değilse kesin deme — supheli de."""
    adaylar = [a for a in adaylar if a.skor >= ASGARI_SKOR]
    if not adaylar:
        return Karar("yok", None, [])

    # Eşleştirmede geniş normalizasyon: ligatür, "feat", sözcük sırası.
    # (Kimlik normalizasyonu ayrı ve dondurulmuş — bkz. python/metin.py)
    n_baslik = normalize_esleme(title)

    def _baslik_tutar(mb_baslik: str) -> bool:
        """Birebir, ya da MB başlığı bizimkiyle BAŞLAYIP alt başlıkla sürüyor.

        «Periphery II» ↔ «Periphery II: This Time It's Personal». Etiketler alt
        başlığı çoğu zaman taşımıyor. Önek kuralı dar: MB başlığı bizimkinden
        uzun olacak ve kalan kısım ayraçla (: - ( [) başlayacak — yoksa
        «Truth» ile «Truthful» eşleşirdi.
        """
        n = normalize_esleme(mb_baslik)
        if n == n_baslik:
            return True
        if not n.startswith(n_baslik + " "):
            return False
        kalan = mb_baslik[len(mb_baslik) - len(mb_baslik):]  # okunurluk için
        ham = mb_baslik.strip()
        kes = ham[len(title.strip()):].lstrip() if ham.lower().startswith(
            title.strip().lower()) else ""
        return kes[:1] in {":", "-", "–", "—", "(", "["} if kes else False

    tam_tutanlar = [
        a
        for a in adaylar
        if ayni_kisi_mi(a.artist, artist) and _baslik_tutar(a.title)
    ]

    if tam_tutanlar:
        # Tek bir tam eşleşme varsa yıl tutmasa da kabul: karıştırılacak rakip yok.
        # Etiketteki yıl çoğu zaman yeniden basımın yılıdır, MB ise ilk çıkışı verir;
        # bu farkı şüphe saymak reissue'su bol bir kütüphanede raporu şişirir.
        if len(tam_tutanlar) == 1:
            aday = tam_tutanlar[0]
            not_ = ""
            if yil and aday.yil and abs(aday.yil - yil) > 1:
                not_ = f"yıl farkı: etiket {yil}, MB {aday.yil}"
            return Karar("kesin", aday, adaylar[:5], not_)

        # Birden fazla tam eşleşme. Sırayla eleme: yayın türü → tam yıl → ±1 yıl.
        # Her adımda tek aday kalırsa kesin; sonuna kadar ayrışmazsa insan baksın.
        kalanlar = _tur_ile_ayir(tam_tutanlar, parca_sayisi)
        if len(kalanlar) == 1:
            return Karar("kesin", kalanlar[0], adaylar[:5], "tür ile ayrıldı")

        if yil:
            for tolerans, aciklama in ((0, "yıl birebir"), (1, "yıl ±1")):
                uyanlar = [
                    a for a in kalanlar if a.yil and abs(a.yil - yil) <= tolerans
                ]
                if len(uyanlar) == 1:
                    return Karar("kesin", uyanlar[0], adaylar[:5], aciklama)

        # YENİDEN BASIM YILI. Etiketteki yıl adayların HEPSİNDEN belirgin
        # sonraysa (>1 yıl), etiket bir yeniden basımı gösteriyor demektir;
        # MusicBrainz'in yayın grubu ise ilk çıkışı verir. Ölçüldü: «Pantera —
        # Cowboys From Hell» etikette 2010, MB'de 1990 ve 1994 — yıl eşlemesi
        # ikisini de tutturamıyordu. Böyle durumda EN ESKİ yayın grubu doğru
        # olan; kalanlar reissue kümeleri.
        yillilar = [a for a in kalanlar if a.yil]
        if yil and yillilar and all(yil - a.yil > 1 for a in yillilar):
            en_eski = min(yillilar, key=lambda a: a.yil)
            return Karar("kesin", en_eski, adaylar[:5],
                         f"yeniden basım: etiket {yil}, ilk çıkış {en_eski.yil}")

        return Karar(
            "supheli", kalanlar[0], adaylar[:5], "birden fazla tam eşleşme"
        )

    # KADRO ADI KAPSAMASI. Başlık birebir tutuyor ve MusicBrainz emin (≥95)
    # ise, sanatçı farkı büyük ihtimalle lider-adı/kadro-adı farkıdır.
    # Başlığın birebir tutması şartı bu kuralı dar tutan şey: «Beck — Odelay»
    # Jeff Beck'e bağlanamaz çünkü öyle bir Jeff Beck albümü yok.
    kadro = [
        a for a in adaylar
        if a.skor >= 95 and normalize_esleme(a.title) == n_baslik
        and _kadro_uyumu(artist, a.artist)
    ]
    if len(kadro) == 1:
        return Karar("kesin", kadro[0], adaylar[:5],
                     f"kadro adı: etiket «{artist}», MB «{kadro[0].artist}»")

    return Karar("supheli", adaylar[0], adaylar[:5], "başlık/sanatçı tam tutmuyor")


def _sorgu_at(istemci: ApiIstemci, artist: str, title: str) -> list[Aday]:
    sorgu = f'artist:"{artist}" AND releasegroup:"{title}"'
    return adaylari_coz(
        istemci.get_json("release-group", {"query": sorgu, "fmt": "json", "limit": 5})
    )


def _normalize_sorgu(istemci: ApiIstemci, artist: str, title: str) -> list[Aday]:
    """Normalize edilmiş ad/başlıkla arama. Normalize bir şey değiştirmediyse boş."""
    n_artist, n_title = normalize_esleme(artist), normalize_esleme(title)
    if (n_artist, n_title) == (artist.lower(), title.lower()):
        return []  # istek boşuna
    return _sorgu_at(istemci, n_artist, n_title)


def album_ara(istemci: ApiIstemci, artist: str, title: str) -> list[Aday]:
    """Önce ham etiketle ara; sonuç yoksa normalize edilmiş başlıkla tekrar dene.

    "Meddle (2011 Remaster)" MusicBrainz'de yok, "meddle" var. Ham başlıkla
    başlamak kesinliği korur, normalize geri çekilişi kapsamı kurtarır.
    (Aday gelip de tutmadığı durumdaki ikinci deneme `eslestir` içinde.)
    """
    adaylar = _sorgu_at(istemci, artist, title)
    if adaylar:
        return adaylar
    return _normalize_sorgu(istemci, artist, title)


def _baslik_sorgusu(istemci: ApiIstemci, title: str) -> list[Aday]:
    """Sanatçı süzgeci OLMADAN arama.

    İki başarısızlığı birden kurtarıyor, ikisi de ölçüldü:
    - Etiketteki sanatçı adı MusicBrainz'inkinden farklı: «Yngwie Malmsteen»
      ↔ «Yngwie J. Malmsteen». `artist:"..."` süzgeci sıfır sonuç veriyordu.
    - Sanatçı adında Lucene'in özel karakteri var: «THE SQUARE / T-SQUARE».
      Eğik çizgi sorguyu bozuyordu.

    Sanatçı denetimi kaybolmuyor, SONRAYA alınıyor: `karar_ver` yine
    `ayni_kisi_mi` ya da kadro kapsaması arıyor. Yalnız arama alanı genişliyor.
    """
    return adaylari_coz(
        istemci.get_json("release-group",
                         {"query": f'releasegroup:"{title}"', "fmt": "json",
                          "limit": 10})
    )


def _sozcuk_sorgulari(
    istemci: ApiIstemci, artist: str, title: str, azami: int = 2,
) -> list[Aday]:
    """Sanatçıyı TIRNAKSIZ TEK SÖZCÜKLE ara; en ayırt edici sözcükten başla.

    `artist:"THE SQUARE / T-SQUARE"` sıfır sonuç veriyor — eğik çizgi Lucene
    sorgusunu bozuyor. `artist:"Yngwie Malmsteen"` de sıfır veriyor, çünkü
    MusicBrainz'de kayıt «Yngwie J. Malmsteen's Rising Force» adına.
    Yalnız başlıkla aramak da yetmiyor: «Adventures» ya da «Odyssey» gibi
    yaygın başlıklarda doğru sanatçı ilk ona girmiyor (ölçüldü).

    Tek sözcük ikisini birden çözüyor. Ölçüldü:
        square    → T‐SQUARE — ADVENTURES (1984)
        malmsteen → Yngwie J. Malmsteen's Rising Force — Odyssey (1988)
        blackmore → Rainbow — Stranger in Us All (1995)

    Sözcükler uzundan kısaya deneniyor; en uzun sözcük genellikle en ayırt
    edici olan. `azami` istek sayısını sınırlıyor — eşleşmeyen albüm başına
    en fazla iki ek ağ isteği.
    """
    sozcukler = sorted(
        {w for w in normalize_esleme(artist).split() if len(w) >= 4},
        key=len, reverse=True,
    )[:azami]
    toplanan: list[Aday] = []
    bilinen: set[str] = set()
    for sozcuk in sozcukler:
        sorgu = f'releasegroup:"{title}" AND artist:{sozcuk}'
        for aday in adaylari_coz(
            istemci.get_json("release-group",
                             {"query": sorgu, "fmt": "json", "limit": 5})
        ):
            if aday.mbid not in bilinen:
                bilinen.add(aday.mbid)
                toplanan.append(aday)
    return toplanan


# --------------------------------------------------------------------------- #
# Altıncı yol: önce SANATÇI, sonra onun kataloğu
# --------------------------------------------------------------------------- #

#: Katalog taraması en fazla bu kadar yayın grubu okur (sayfa başına 100).
KATALOG_AZAMI = 300


def _sanatci_kimlikleri(istemci: ApiIstemci, artist: str) -> list[str]:
    """Etiketteki ada TAKMA AD DAHİL uyan MusicBrainz sanatçıları.

    Önceki beş deneme sanatçıyı yayın grubunun `artist-credit` adıyla
    karşılaştırıyor. Japon kayıtlarında o ad özgün yazımla duruyor:
    «Masayoshi Takanaka» ↔ «高中正義», «Himiko Kikuchi» ↔ «菊池ひみこ».
    Latin ad yalnız TAKMA AD listesinde; `ayni_kisi_mi` onu hiç görmüyordu.

    Kabul dar: ad, sıralama adı ya da takma adlardan biri etiketle
    `ayni_kisi_mi` düzeyinde tutmalı. Arama skorunun yüksek olması yetmez —
    «Scott Henderson» araması «Michael Henderson»u 100 puanla döndürüyor.
    """
    parcalar = [artist] + [p.strip() for p in artist.split("/") if p.strip()]
    kimlikler: list[str] = []
    for ad in dict.fromkeys(parcalar):
        temiz = ad.replace('"', "")
        govde = istemci.get_json("artist", {
            "query": f'artist:"{temiz}" OR alias:"{temiz}"', "fmt": "json",
            "limit": 5})
        for aday in (govde or {}).get("artists", []):
            adlar = [aday.get("name"), aday.get("sort-name")] + [
                t.get("name") for t in aday.get("aliases", []) or []]
            if any(ayni_kisi_mi(ad, a) or _tanimliksiz(ad) == _tanimliksiz(a)
                   for a in adlar if a):
                if aday["id"] not in kimlikler:
                    kimlikler.append(aday["id"])
    return kimlikler[:2]


def _katalog(istemci: ApiIstemci, sanatci_id: str) -> list[Aday]:
    """Sanatçının yayın gruplarının tamamı (browse; arama değil)."""
    adaylar: list[Aday] = []
    ofset = 0
    while ofset < KATALOG_AZAMI:
        govde = istemci.get_json("release-group", {
            "artist": sanatci_id, "limit": 100, "offset": ofset, "fmt": "json"})
        gruplar = (govde or {}).get("release-groups", [])
        for ham in gruplar:
            adaylar.append(Aday(
                mbid=ham["id"], artist=f"<{sanatci_id[:8]}>",
                title=ham.get("title", ""),
                yil=yil_ayikla(ham.get("first-release-date")),
                skor=100, tur=ham.get("primary-type"),
            ))
        ofset += 100
        if len(gruplar) < 100 or ofset >= int((govde or {}).get("release-group-count", 0)):
            break
    return adaylar


#: Tanımlıklar sözcük örtüşmesine girmez. `normalize_esleme` BAŞTAKİ
#: tanımlığı atıyor; «虹伝説 THE RAINBOW GOBLINS» CJK düşünce «the» başa
#: geliyor ve gidiyor, bizim «Nijidensetsu -The Rainbow Goblins-»de ortada
#: kalıyor. Sayılırsa oran yapay biçimde düşüyor (ölçüldü: 2/4 yerine 2/3).
_TANIMLIK = frozenset({"the", "and", "les", "des", "der", "die", "das", "los", "las"})


def _baslik_sozcukleri(baslik: str) -> set[str]:
    return {w for w in normalize_esleme(baslik.translate(_TIRE)).split()
            if len(w) >= 3 and w not in _TANIMLIK}


def _tanimliksiz(ad: str | None) -> str:
    """«The Stampeders» ↔ «Stampeders» — etiketler baştaki tanımlığı atlıyor."""
    n = normalize_esleme(ad)
    return n[4:] if n.startswith("the ") else n


def katalog_karari(
    title: str, yil: int | None, katalog: list[Aday], parca_sayisi: int | None = None,
) -> Karar:
    """Doğrulanmış sanatçının kataloğunda başlığı bul.

    Sanatçı kimliği zaten doğrulandığı için başlık GEVŞEK tutulabilir ama
    iki koşulla:
    - Birebir (normalize) tutmuyorsa örtüşme İKİ YÖNLÜ en az %60 olmalı VE
      yıl ±1 tutmalı. «Nijidensetsu -The Rainbow Goblins-» (1981) ↔
      «虹伝説 THE RAINBOW GOBLINS» (1981): yıl tutuyor, 3 sözcüğün 2'si,
      MB'nin 2 sözcüğünün 2'si ortak. Yıl şartı olmasa «Seychelles» (1976)
      ↔ «Ukulele SEYCHELLES» (2011) bağlanırdı. Ters yön şartı olmasa
      «Passion & Warfare (25th Anniversary)» fazladan bir albüm adı taşıyan
      «Modern Primitive / Passion and Warfare»a bağlanırdı — kredileri de
      başka albümü anlatırdı. Emin olunamıyorsa insana kalır.
    - Birden çok aday kalırsa `karar_ver`'in yolu: tür, yıl, sonra yeniden
      basım kuralı (etiket yılı hepsinden sonraysa en eski yayın grubu).
    """
    sade = arama_basligi(title)
    n_baslik = normalize_esleme(sade.translate(_TIRE))
    bizim = _baslik_sozcukleri(sade)

    birebir = [a for a in katalog
               if normalize_esleme(a.title.translate(_TIRE)) == n_baslik]
    ortusen = []
    if not birebir and bizim and yil:
        for a in katalog:
            onlarin = _baslik_sozcukleri(a.title)
            ortak = bizim & onlarin
            if (onlarin and len(ortak) / len(bizim) >= 0.6
                    and len(ortak) / len(onlarin) >= 0.6
                    and a.yil and abs(a.yil - yil) <= 1):
                ortusen.append(a)

    adaylar = birebir or ortusen
    if not adaylar:
        return Karar("yok", None, [])
    neden = "katalog: birebir başlık" if birebir else "katalog: sözcük örtüşmesi + yıl"
    if len(adaylar) == 1:
        return Karar("kesin", adaylar[0], adaylar, neden)
    kalan = _tur_ile_ayir(adaylar, parca_sayisi)
    if len(kalan) == 1:
        return Karar("kesin", kalan[0], adaylar, neden + ", tür ile ayrıldı")
    if yil:
        for tolerans in (0, 1):
            uyan = [a for a in kalan if a.yil and abs(a.yil - yil) <= tolerans]
            if len(uyan) == 1:
                return Karar("kesin", uyan[0], adaylar, neden + ", yıl ile ayrıldı")
        yillilar = [a for a in kalan if a.yil]
        if yillilar and all(yil - a.yil > 1 for a in yillilar):
            en_eski = min(yillilar, key=lambda a: a.yil)
            return Karar("kesin", en_eski, adaylar,
                         neden + f", yeniden basım: ilk çıkış {en_eski.yil}")
    return Karar("supheli", kalan[0], adaylar[:5], neden + ", birden fazla aday")


def katalog_yolu(
    istemci: ApiIstemci, artist: str, title: str, yil: int | None,
    parca_sayisi: int | None = None,
) -> Karar:
    en_iyi = Karar("yok", None, [])
    for sanatci_id in _sanatci_kimlikleri(istemci, artist):
        karar = katalog_karari(title, yil, _katalog(istemci, sanatci_id), parca_sayisi)
        if karar.durum == "kesin":
            return karar
        if karar.durum == "supheli" and en_iyi.durum == "yok":
            en_iyi = karar
    return en_iyi


def eslestir(
    conn: sqlite3.Connection,
    istemci: ApiIstemci,
    *,
    limit: int | None = None,
    yenile: bool = False,
) -> tuple[dict[str, int], list[dict]]:
    """mbid'i boş albümleri MusicBrainz'e bağla. (sayaçlar, rapor satırları)."""
    # Kullanıcı "MusicBrainz karşılığı yok" dediyse (`mbid_yok`) bir daha
    # aranmaz: altıncı yol gevşek başlık eşlemesiyle ona MBID yazabilirdi ve
    # insan kararını makine kararı ezmiş olurdu.
    sorgu = ("SELECT album_id, artist, title, year, track_count FROM albums "
             "WHERE mbid_yok = 0")
    if not yenile:
        sorgu += " AND mbid IS NULL"
    sorgu += " ORDER BY artist, year, title"
    if limit:
        sorgu += f" LIMIT {int(limit)}"
    albumler = conn.execute(sorgu).fetchall()

    sayac = {"kesin": 0, "supheli": 0, "yok": 0}
    rapor: list[dict] = []

    for sira, albom in enumerate(albumler, 1):
        try:
            adaylar = album_ara(istemci, albom["artist"], albom["title"])
            karar = karar_ver(
                albom["artist"], albom["title"], albom["year"], adaylar,
                albom["track_count"],
            )

            # Ham sorgu aday döndürdü ama hiçbiri tutmadıysa, normalize sorguyu
            # yine de dene. Aksi halde "Comment te dire adieu (Remasterisé en
            # 2016)" gibi başlıklar hep şüpheli kalır: ham sorgu alakasız ama
            # skoru yüksek adaylar getirdiği için ikinci deneme hiç yapılmaz.
            if karar.durum != "kesin":
                ek = _normalize_sorgu(istemci, albom["artist"], albom["title"])
                if ek:
                    bilinen = {a.mbid for a in adaylar}
                    birlesik = adaylar + [a for a in ek if a.mbid not in bilinen]
                    ikinci = karar_ver(
                        albom["artist"], albom["title"], albom["year"], birlesik,
                        albom["track_count"],
                    )
                    if ikinci.durum == "kesin" or not adaylar:
                        karar = ikinci

            # ÜÇÜNCÜ DENEME: baskı süsü atılmış, apostrofu korunmuş başlık.
            # Normalize sorgu apostrofu boşluğa çevirdiği için «We're An
            # American Band» aranamıyordu; bu deneme onu kurtarıyor.
            if karar.durum != "kesin":
                sade = arama_basligi(albom["title"], albom["artist"])
                if sade != albom["title"]:
                    ek = _sorgu_at(istemci, albom["artist"], sade)
                    if ek:
                        ucuncu = karar_ver(
                            albom["artist"], sade, albom["year"], ek,
                            albom["track_count"],
                        )
                        if ucuncu.durum == "kesin":
                            karar = ucuncu

            # DÖRDÜNCÜ DENEME: sanatçı süzgeci olmadan, yalnız başlıkla.
            if karar.durum != "kesin":
                sade = arama_basligi(albom["title"], albom["artist"])
                ek = _baslik_sorgusu(istemci, sade)
                if ek:
                    dorduncu = karar_ver(
                        albom["artist"], sade, albom["year"], ek,
                        albom["track_count"],
                    )
                    if dorduncu.durum == "kesin":
                        karar = dorduncu

            # BEŞİNCİ DENEME: sanatçının en ayırt edici tek sözcüğü.
            if karar.durum != "kesin":
                sade = arama_basligi(albom["title"], albom["artist"])
                ek = _sozcuk_sorgulari(istemci, albom["artist"], sade)
                if ek:
                    besinci = karar_ver(
                        albom["artist"], sade, albom["year"], ek,
                        albom["track_count"],
                    )
                    if besinci.durum == "kesin":
                        karar = besinci

            # ALTINCI DENEME: sanatçıyı takma adıyla bul, kataloğunu tara.
            if karar.durum != "kesin":
                altinci = katalog_yolu(istemci, albom["artist"], albom["title"],
                                       albom["year"], albom["track_count"])
                if altinci.durum == "kesin" or (
                        altinci.durum == "supheli" and karar.durum == "yok"):
                    karar = altinci
        except AgYok:
            print(f"  çevrimdışı, atlandı: {albom['artist']} — {albom['title']}", file=sys.stderr)
            continue
        sayac[karar.durum] += 1

        if karar.durum == "kesin" and karar.aday:
            with conn:
                conn.execute(
                    "UPDATE albums SET mbid = ? WHERE album_id = ?",
                    (karar.aday.mbid, albom["album_id"]),
                )
            if karar.not_:
                print(
                    f"  not: {albom['artist']} — {albom['title']}: {karar.not_}",
                    file=sys.stderr,
                )
        else:
            rapor.append(
                {
                    "album_id": albom["album_id"],
                    "sanatci": albom["artist"],
                    "album": albom["title"],
                    "yil": albom["year"] or "",
                    "durum": karar.durum,
                    "neden": karar.not_,
                    "mbid": "",  # elle doldurulacak sütun
                    "adaylar": " | ".join(a.ozet() for a in karar.adaylar),
                }
            )

        if sira % 25 == 0 or sira == len(albumler):
            print(
                f"  {sira}/{len(albumler)} — kesin {sayac['kesin']}, "
                f"şüpheli {sayac['supheli']}, yok {sayac['yok']} "
                f"({istemci.sayac.ozet()})",
                file=sys.stderr,
            )

    return sayac, rapor


def rapor_yaz(satirlar: list[dict], hedef: Path) -> None:
    hedef.parent.mkdir(parents=True, exist_ok=True)
    alanlar = ["album_id", "sanatci", "album", "yil", "durum", "neden", "mbid", "adaylar"]
    with hedef.open("w", newline="", encoding="utf-8") as f:
        yazici = csv.DictWriter(f, fieldnames=alanlar)
        yazici.writeheader()
        yazici.writerows(satirlar)


# --------------------------------------------------------------------------- #
# MBID biçimi
# --------------------------------------------------------------------------- #

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
#: UPC-A 12, EAN-13 13 hane; EAN-8 ve GTIN-14 de görülüyor.
_BARKOD = re.compile(r"^\d{8,14}$")


def mbid_coz(istemci: ApiIstemci | None, deger: str) -> str | None:
    """Elle girilen değeri yayın grubu MBID'sine çevir; olmuyorsa None.

    Ölçülen hata (2026-09-21): iki albümün `mbid` alanında BARKOD duruyordu
    («074646770320», «4542696000309») — elle düzeltme CSV'sine barkod
    yapıştırılmış. Kredi zenginleştirmesi o satırda 400 alıp tüm turu
    düşürüyordu. Barkod aslında kesin bir kimlik: MusicBrainz'de yayına,
    oradan tek bir yayın grubuna çözülüyor. Birden çok gruba dağılıyorsa
    (farklı albümler aynı barkodu paylaşamaz ama kayıt hatası olur) None.
    """
    deger = (deger or "").strip().lower()
    if _UUID.match(deger):
        return deger
    if not _BARKOD.match(deger) or istemci is None:
        return None
    govde = istemci.get_json("release", {"query": f"barcode:{deger}",
                                         "fmt": "json", "limit": 10})
    gruplar = {
        (r.get("release-group") or {}).get("id")
        for r in (govde or {}).get("releases", [])
        if r.get("score", 0) >= 100 and (r.get("release-group") or {}).get("id")
    }
    return gruplar.pop() if len(gruplar) == 1 else None


def bicim_onar(conn: sqlite3.Connection, istemci: ApiIstemci | None) -> list[str]:
    """UUID olmayan `mbid`leri çöz ya da boşalt. Değişiklik satırlarını döner.

    Çözülemeyen değer SİLİNİR (NULL): yanlış biçimli bir MBID her
    zenginleştirme turunu düşürüyor, boş olan ise yalnız o albümü eşleştirme
    ekranına geri gönderiyor.
    """
    notlar = []
    for album_id, artist, title, mbid in conn.execute(
        "SELECT album_id, artist, title, mbid FROM albums "
        "WHERE mbid IS NOT NULL AND mbid != ''").fetchall():
        if _UUID.match(mbid):
            continue
        yeni = mbid_coz(istemci, mbid)
        with conn:
            conn.execute("UPDATE albums SET mbid = ? WHERE album_id = ?", (yeni, album_id))
        notlar.append(f"{artist} — {title}: «{mbid}» → {yeni or 'silindi (çözülemedi)'}")
    return notlar


def duzeltmeleri_uygula(
    conn: sqlite3.Connection, dosya: Path, istemci: ApiIstemci | None = None,
) -> int:
    """Elle doldurulmuş rapordaki mbid sütununu veritabanına yaz.

    Değer `mbid_coz`dan geçer: UUID olduğu gibi, barkod yayın grubuna
    çözülerek yazılır; ikisi de değilse satır atlanır ve söylenir.
    """
    uygulanan = 0
    with dosya.open(newline="", encoding="utf-8-sig") as f:
        for satir in csv.DictReader(f):
            ham = (satir.get("mbid") or "").strip()
            album_id = (satir.get("album_id") or "").strip()
            if not ham or not album_id:
                continue
            mbid = mbid_coz(istemci, ham)
            if mbid is None:
                print(f"  ATLANDI {satir.get('sanatci')} — {satir.get('album')}: "
                      f"«{ham}» MBID ya da çözülebilir barkod değil", file=sys.stderr)
                continue
            with conn:
                imlec = conn.execute(
                    "UPDATE albums SET mbid = ? WHERE album_id = ?", (mbid, album_id)
                )
            uygulanan += imlec.rowcount
    return uygulanan


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(
        description="Albümleri MusicBrainz release-group'a bağla."
    )
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--limit", type=int, help="en fazla kaç albüm işlensin")
    ayristirici.add_argument("--rapor", type=Path, default=VARSAYILAN_RAPOR)
    ayristirici.add_argument(
        "--yenile", action="store_true", help="mbid'i dolu albümleri de yeniden ara"
    )
    ayristirici.add_argument(
        "--cevrimdisi", action="store_true", help="sadece önbellekten çalış"
    )
    ayristirici.add_argument(
        "--uygula", type=Path, help="elle doldurulmuş rapor CSV'sini uygula ve çık"
    )
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        istemci = musicbrainz(cevrimdisi=args.cevrimdisi)
        if args.uygula:
            adet = duzeltmeleri_uygula(conn, args.uygula, istemci)
            print(f"{adet} albümün mbid'i elle karardan yazıldı.")
            return 0

        for not_ in bicim_onar(conn, istemci):
            print(f"  biçim onarıldı: {not_}", file=sys.stderr)
        sayac, rapor = eslestir(conn, istemci, limit=args.limit, yenile=args.yenile)
    finally:
        conn.close()

    print(f"Kesin eşleşen : {sayac['kesin']}")
    print(f"Şüpheli       : {sayac['supheli']}")
    print(f"Aday bulunamadı: {sayac['yok']}")
    print(istemci.sayac.ozet())
    if rapor:
        rapor_yaz(rapor, args.rapor)
        print(f"Elle bakılacaklar: {args.rapor} (mbid sütununu doldurup --uygula ile yaz)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
