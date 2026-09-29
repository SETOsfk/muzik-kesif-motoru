"""Yeni kullanıcı aktarım hattı: Spotify kütüphanesi → öneri.

Bu hat olmadan seto dışındaki hiçbir kullanıcı öneri alamıyordu. Yerel
kütüphane yolu (tarama → krediler → stem ölçümü → metadata matrisi) diskte
dosya ister; Spotify kullanıcısının elinde dosya yok, yalnız bir liste var.

## Aşamalar

1. **Spotify** — kayıtlı albümler, son çalınanların albümleri, en çok
   dinlenen sanatçılar. Salt okuma (`python/spotify.py`).
2. **Deezer eşlemesi** — her albüm için doğrulanmış bir 30 sn önizleme.
   En çok dinlenen ama albümü kayıtlı olmayan sanatçı için Deezer'ın o
   sanatçıdaki en popüler parçasının albümü alınır (`kaynak='spotify_en_cok'`).
3. **CLAP gömüsü** — önizlemenin 512 boyutlu ses gömüsü, `data/cache/clap/`
   altına album_id ile. Gömü ALBÜMÜN özelliği, kullanıcının değil: iki
   kullanıcının aynı albümü aynı dosyayı paylaşır ve sızacak kişisel bilgi
   yok (K20'nin önbellek sorusu soruldu, cevap bu).
4. **Çalma listesi hasadı** — kullanıcının sanatçıları için Deezer listeleri
   (paylaşımlı havuz büyür), ardından KULLANICIYA GÖRE npmi.
5. **Kümeleme** — yalnız CLAP gömüsünde FCM (aşağıya bakınız).
6. **Adaylar** — ana akışın üç stratejisi: melez, liste birlikteliği, ses
   benzerliği. Kredi grafiği stratejileri çalışmaz: Spotify albümünün kredisi
   yok ve MusicBrainz/Discogs zenginleştirmesi saatler sürer. Bu eksiklik
   arayüzde yazılı.

## Kümeleme neden yalnız ses, c nasıl seçiliyor

Metadata matrisi (kredi/etiket/sahne/ses) bu kullanıcılar için yok. CLAP
gömüsü tek ortak zemin. Ölçüldü (2026-09-21, seto'nun 288 gömülü albümü,
leave-one-artist-out, `python/degerlendirme.py`, npmi + büzülme 1, melez 1:2,
aynı havuz — 1.972 liste sanatçısı):

    kümeleme                  melez @50   MRR    yüzdelik   liste @50
    metadata FCM, c=12          0.10     0.011    0.096       0.29
    CLAP FCM, c=2 (XB seçimi)   0.03     0.011    0.157       0.15
    CLAP FCM, c=5               0.08     0.019    0.116       0.23
    CLAP FCM, c=8               0.08     0.009    0.106       0.24
    CLAP FCM, c=9  (seçilen)    0.09     0.010    0.099       0.25
    CLAP FCM, c=10              0.09     0.017    0.100       0.24
    CLAP FCM, c=12              0.10     0.017    0.097       0.24

İki sonuç var. (1) Yalnız ses, metadata kümelemesi kadar iyi — yeni
kullanıcı ikinci sınıf öneri almıyor. (2) CLAP uzayında Xie-Beni eğrisi düz
(0,6–0,85); XB minimumu c=2'yi seçiyor ve bu en KÖTÜ sonuç. İçsel indeks
burada yapı söylemiyor.

Seçim bu yüzden `fcm.en_ince_stabil_c`: bütün kümeleri bootstrap'ta stabil
olan ve XB'si en iyinin 1,5 katını aşmayan EN İNCE bölme. Seto'da c=9
(tablodaki en iyi bölgede); 52 albümlük deneme kütüphanesinde c=3 — XB kuralı
orada da c=2 verip cazı metalle, hip-hop'u folkla aynı eksene koyuyordu;
yapısı bilinen sentetik veride (3 küme) doğru olan c=3. Tavan `n // 10`
([2, 12]); en küçük küme 5 albümden az olamaz.

## Denenip ÇIKARILAN: komşu gömüsü (2026-09-21)

Ses havuzu (`clap_parca`) ilk hasattan, yani seto'nun sanatçılarının
komşularından kuruldu. 52 albümlük denemede kullanıcının en güçlü 300 liste
komşusunun 151'inin gömüsü yoktu; hattan sonra 447 parçası gömüldü (351
başarılı, ~6 dk). Ölçüm (leave-one-artist-out, aynı ayar):

    kütüphane      yol     tavan    @50    MRR    yüzdelik
    deneme (50)    melez   47→47   .12→.10  .028→.014  .081→.087
    seto (147)     ses    104→109  .03→.03  .006→.005  .347→.330
    seto (147)     melez  123→123  .10→.10  .011→.013  .096→.101

Tutarlı bir kazanç yok, aktarıma 6 dakika ekliyor → hattan çıkarıldı.
Gözle de bakıldı: ses önerileri neredeyse aynı kaldı, iki eksende birden
çıkan «her şeye benzeyen» kayıtlar yerinde duruyor. Yani sorun havuzun
kapsamı değil, küçük kütüphanede ses benzerliğinin hubness'ı. Gömülen
parçalar paylaşımlı havuzda duruyor (zararsız).

## Spotify'sız giriş: sanatçı listesi (2026-09-28)

Spotify Development Mode beş hesapla sınırlı; herkese açık bir sürümde asıl
kapı bu olamaz. Kullanıcı sevdiği sanatçıları (ya da «Sanatçı — Albüm»
satırlarını) yazar; albümsüz her sanatçı için Deezer'daki en popüler
parçalarından `LISTE_SANATCI_ALBUM` ayrı albüm alınır (`kaynak='liste'`).
Hattın geri kalanı aynı. `liste_ayristir` metni kayıt + sanatçıya böler;
`ASGARI_ALBUM`a yetmeyecek kadar kısa liste aktarım başlamadan reddedilir.

## Çalıştırma

    python -m python.aktarim --kullanici 2              # Spotify'dan
    python -m python.aktarim --kullanici 2 --json a.json  # elle liste
    python -m python.aktarim --kullanici 2 --asama kume   # kaldığı yerden

`--json` girdisi `[{sanatci, album?}]`; albümü olmayan satır sanatçı sayılır.

Web arayüzü bunu ayrı bir SÜREÇ olarak başlatıyor (`web/sunucu.py:aktar`):
torch ~2 GB bellek ister ve sunucu sürecine yüklenmemeli. İlerleme
`data/db/kullanici/{id}.aktarim.json` dosyasına yazılıyor.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

import python.db as _db
from python.db import baglan_kullanici, baglan_ortak, kullanici_db
from python.metin import album_kimligi, normalize_esleme, yil_ayikla

#: c taramasının tavanı albüm sayısına bağlı: küme başına en az ~10 albüm.
#: Seçimi tavan değil stabilite yapıyor (bkz. modül belgesi).
KUME_BASINA_ASGARI = 10
C_ALT, C_UST = 2, 12

#: Bundan az gömülü albümle kümeleme yapılmaz. PCA 8 bileşen istiyor ve iki
#: kümenin her biri bootstrap'ta anlamlı bir örneklem görmeli.
ASGARI_ALBUM = 20

#: Ana akışın stratejileri (`web/sunucu.py:ANA_STRATEJILER`). Kredi/kalabalık
#: grafiği stratejileri Spotify albümünde çalışmaz — kredisi yok.
STRATEJILER = ("liste_birlikteligi", "ses_benzerligi", "melez")

#: Listeyle gelen albümsüz sanatçı başına alınan albüm. Bir albüm sanatçıyı
#: tek bir döneme bağlıyor; üç ve fazlası kümeleri sanatçı sınırına
#: kilitliyor ve aktarımı uzatıyor (albüm başına ~2,5 sn).
LISTE_SANATCI_ALBUM = 2

#: Liste satırı tavanı: aktarım süresi satırla doğrusal büyüyor.
LISTE_AZAMI_SATIR = 150

#: Art arda bu kadar sanatçı araması hatayla biterse Deezer'a ulaşılamıyor
#: sayılır. Ölçüldü (2026-09-28, ağ kapalı): her arama 4 deneme × artan
#: bekleme ≈ 30 sn sürüyor; 12 sanatçılık liste dakikalarca sessizce bekliyordu.
AG_HATA_ESIGI = 3

ASAMALAR = ("spotify", "eslesme", "gomu", "hasat", "kume", "aday")
ASAMA_ADI = {
    "spotify": "Spotify kütüphanesi okunuyor",
    "eslesme": "Deezer'da önizlemeler aranıyor",
    "gomu": "Ses gömüleri çıkarılıyor",
    "hasat": "Çalma listeleri toplanıyor",
    "kume": "Zevk eksenleri kümeleniyor",
    "aday": "Öneriler üretiliyor",
    "bitti": "Hazır",
}


# --------------------------------------------------------------------------- #
# İlerleme dosyası
# --------------------------------------------------------------------------- #

def durum_yolu(kullanici_id: int) -> Path:
    # `_db.KULLANICI_KOK` ÇAĞRI ANINDA okunuyor: içe aktarırken bağlansaydı
    # testlerin yönlendirmesi işlemez, durum dosyası gerçek dizine düşerdi
    # (aynı hata sınıfı `db.baglan_kullanici` belgesinde).
    return _db.KULLANICI_KOK / f"{kullanici_id}.aktarim.json"


def durum_oku(kullanici_id: int) -> dict[str, Any] | None:
    try:
        return json.loads(durum_yolu(kullanici_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def calisiyor_mu(kullanici_id: int) -> bool:
    """Durum 'calisiyor' diyor VE o süreç hâlâ yaşıyor mu?

    Yalnız dosyaya bakmak yetmez: süreç öldürülürse dosya sonsuza dek
    'calisiyor' der ve kullanıcı yeniden başlatamaz.
    """
    durum = durum_oku(kullanici_id)
    if not durum or durum.get("durum") != "calisiyor":
        return False
    pid = durum.get("pid")
    if not isinstance(pid, int):
        return False
    # Süreci web sunucusu başlattıysa ölen çocuk BİÇMLENENE kadar zombi kalır
    # ve `kill(pid, 0)` onu yaşıyor sayar. Ölçüldü (2026-09-28): hesap silmede
    # durdurulan aktarım `<defunct>` kaldı. Bellek yetmezliğinde ölen bir
    # aktarım da kullanıcıyı sonsuza dek "çalışıyor"da ve eşzamanlılık
    # yuvasını dolu tutardı. Bizim çocuğumuz değilse (CLI, sunucu yeniden
    # başlamış) ChildProcessError — o zaman yalnız kill(0) karar verir.
    try:
        if os.waitpid(pid, os.WNOHANG)[0] == pid:
            return False
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Ilerleme:
    """Aşama + sayaç; her güncellemede dosyaya atomik yazar."""

    def __init__(self, kullanici_id: int | None, *, sessiz: bool = False):
        self.kullanici_id = kullanici_id
        self.sessiz = sessiz
        self.veri: dict[str, Any] = {
            "durum": "calisiyor", "pid": os.getpid(),
            "basladi": _simdi(), "asama": None, "adim": 0, "toplam": 0,
            "ozet": {},
        }

    def _yaz(self) -> None:
        if self.kullanici_id is None:
            return
        yol = durum_yolu(self.kullanici_id)
        yol.parent.mkdir(parents=True, exist_ok=True)
        gecici = yol.with_suffix(".tmp")
        gecici.write_text(json.dumps(self.veri, ensure_ascii=False), encoding="utf-8")
        gecici.replace(yol)

    def asama(self, ad: str, toplam: int = 0) -> None:
        self.veri.update(asama=ad, adim=0, toplam=toplam)
        if not self.sessiz:
            print(f"\n[{ad}] {ASAMA_ADI.get(ad, ad)}", file=sys.stderr)
        self._yaz()

    def adim(self, adim: int, toplam: int | None = None) -> None:
        self.veri["adim"] = adim
        if toplam is not None:
            self.veri["toplam"] = toplam
        # Her adımda disk yazmak gereksiz; arayüz birkaç saniyede bir bakıyor.
        if adim % 5 == 0 or adim == self.veri["toplam"]:
            self._yaz()
            if not self.sessiz and adim % 25 == 0:
                print(f"  {adim}/{self.veri['toplam']}", file=sys.stderr)

    def ozet(self, **alanlar) -> None:
        self.veri["ozet"].update(alanlar)
        self._yaz()

    def secim_bekle(self) -> None:
        """Önizleme hazır; hat kullanıcının zaman penceresini bekliyor."""
        self.veri.update(durum="secim", asama="secim", bitti=_simdi())
        self._yaz()

    def bitir(self, *, hata: str | None = None) -> None:
        self.veri.update(durum="hata" if hata else "bitti", bitti=_simdi(),
                         hata=hata, asama=self.veri["asama"] if hata else "bitti")
        self._yaz()


def baslangic_yaz(kullanici_id: int, pid: int, kaynak: str) -> None:
    """Süreci başlatan taraf durumu HEMEN yazar.

    Alt süreç numpy/pandas yükleyip kendi dosyasını yazana kadar ~1 sn geçiyor;
    o arada `/basla`ya dönen kullanıcı ilerleme yerine formu görüyor, ikinci
    tıklama da ikinci bir süreç açabiliyordu. Alt süreç aynı pid'le üzerine yazar.
    """
    ilerleme = Ilerleme(kullanici_id, sessiz=True)
    ilerleme.veri.update(pid=pid, kaynak=kaynak)
    ilerleme._yaz()


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# 1. Spotify
# --------------------------------------------------------------------------- #

def erisim_jetonu(kullanici_id: int) -> str:
    """Saklı yenileme jetonundan taze erişim jetonu.

    Spotify yeni bir yenileme jetonu dönerse saklanır; dönmezse eskisi
    geçerli kalır (bkz. `spotify.jeton_tazele`).
    """
    from python.hesap import spotify_bagla
    from python.sifre import coz
    from python.spotify import jeton_tazele

    ortak = baglan_ortak()
    try:
        kayit = ortak.execute(
            "SELECT spotify_id, spotify_yenile FROM kullanici WHERE kullanici_id = ?",
            (kullanici_id,)).fetchone()
        yenile = coz(kayit["spotify_yenile"]) if kayit else None
        if not yenile:
            # Bağlı değil ya da anahtar değişmiş (jeton çözülemiyor).
            raise AktarimHatasi("Spotify yetkisi yok ya da okunamıyor — "
                                "Spotify'a yeniden bağlan")
        jetonlar = jeton_tazele(yenile)
        if jetonlar.get("refresh_token"):
            spotify_bagla(ortak, kullanici_id, kayit["spotify_id"],
                          jetonlar["refresh_token"])
    finally:
        ortak.close()
    return jetonlar["access_token"]


def spotify_kayitlari(erisim: str) -> tuple[list[dict], list[str]]:
    """(albüm kayıtları, albümsüz en çok dinlenen sanatçılar).

    Üç kaynak, üçü de SAHİPLİK kadar güçlü bir tercih sinyali (K17): albümü
    kaydetmek, şu sıralar çalmak, aylarca en çok dinlemek.
    """
    from python.spotify import en_cok_sanatcilar, kayitli_albumler, son_calinanlar

    kayitlar = [
        {"sanatci": a["sanatci"], "album": a["album"],
         "yil": yil_ayikla(a.get("yil")), "kaynak": "spotify_kayitli",
         "eklenme": a.get("eklenme")}
        for a in kayitli_albumler(erisim)
    ]
    for p in son_calinanlar(erisim):
        if p.get("album"):
            kayitlar.append({"sanatci": p["sanatci"], "album": p["album"],
                             "yil": None, "kaynak": "spotify_son"})

    kapsanan = {normalize_esleme(k["sanatci"]) for k in kayitlar}
    sanatcilar = []
    for aralik in ("medium_term", "long_term"):
        for s in en_cok_sanatcilar(erisim, aralik=aralik):
            anahtar = normalize_esleme(s["sanatci"])
            if anahtar not in kapsanan:
                kapsanan.add(anahtar)
                sanatcilar.append(s["sanatci"])
    return kayitlar, sanatcilar


# --------------------------------------------------------------------------- #
# 1b. Zaman penceresi: «ne kadar geriye gidelim?» (2026-09-28)
# --------------------------------------------------------------------------- #
#
# Kullanıcı geri bildirimi: «bazı şarkıları en son 2 yıl önce dinledim.»
# Kaydedilmiş ama artık dinlenmeyen albüm bugünkü zevki temsil etmiyor.
# Aktarım iki adıma bölündü: önce Spotify okunur ve ÖNİZLEME yazılır
# (her sinyalin kaç gün önce olduğu), kullanıcı sürgüyle pencereyi seçer,
# sonra hat yalnız pencere içindekilerle çalışır.
#
# Tarih kaynakları: kayıtlı albüm → kaydetme tarihi; son çalınan → çalma
# anı; kendi çalma listesi → parçanın eklenme tarihi; en çok dinlenenler →
# Spotify'ın kendi aralıkları (kısa ≈ 4 hafta, orta ≈ 6 ay, uzun ≈ 1 yıl).
# «Uzun» için tarih yok; bir yıl diye yaklaşıklanıyor ve arayüzde yazılı.

#: Spotify'ın «en çok dinlenenler» aralıklarının gün karşılığı (yaklaşık).
EN_COK_GUN = {"short_term": 28, "medium_term": 182, "long_term": 365}
#: Okunacak en çok kendi liste sayısı ve liste başına en son parça sayısı.
LISTE_AZAMI = 40
LISTE_PARCA_AZAMI = 300
#: Listelerden gelen albüm tavanı (her biri gömü ister, ~2,5 sn).
LISTE_ALBUM_AZAMI = 250
#: Sürgünün durakları, ay. 0 = hepsi.
ZAMAN_DURAKLARI = (1, 3, 6, 12, 24, 36, 60, 0)


def onizleme_yolu(kullanici_id: int) -> Path:
    return _db.KULLANICI_KOK / f"{kullanici_id}.spotify.json"


def _gun_once(tarih: str | None, simdi: datetime) -> int | None:
    if not tarih:
        return None
    try:
        an = datetime.fromisoformat(tarih.replace("Z", "+00:00"))
    except ValueError:
        return None
    if an.tzinfo is None:
        an = an.replace(tzinfo=timezone.utc)
    return max(0, (simdi - an).days)


def spotify_onizleme(erisim: str, *, simdi: datetime | None = None) -> dict:
    """Spotify'dan her sinyali «kaç gün önce» bilgisiyle oku. Hat çalışmaz."""
    from python.spotify import (
        SpotifyHatasi, ben, calma_listelerim, en_cok_sanatcilar,
        kayitli_albumler, liste_parcalari, son_calinanlar,
    )

    simdi = simdi or datetime.now(timezone.utc)
    albumler = [
        {"sanatci": a["sanatci"], "album": a["album"], "yil": yil_ayikla(a.get("yil")),
         "gun": _gun_once(a.get("eklenme"), simdi), "kaynak": "spotify_kayitli"}
        for a in kayitli_albumler(erisim)
    ]
    for p in son_calinanlar(erisim):
        if p.get("album"):
            albumler.append({"sanatci": p["sanatci"], "album": p["album"], "yil": None,
                             "gun": _gun_once(p.get("calma_zamani"), simdi),
                             "kaynak": "spotify_son"})
    en_cok = [
        {"sanatci": s["sanatci"], "gun": gun}
        for aralik, gun in EN_COK_GUN.items()
        for s in en_cok_sanatcilar(erisim, aralik=aralik)
    ]
    listeler, okunamadi = [], False
    try:
        kimlik = ben(erisim)["spotify_id"]
        for l in calma_listelerim(erisim, kimlik, azami=LISTE_AZAMI):
            parcalar = [
                {"sanatci": p["sanatci"], "album": p["album"], "yil": yil_ayikla(p.get("yil")),
                 "gun": _gun_once(p.get("eklenme"), simdi)}
                for p in liste_parcalari(erisim, l["liste_id"], toplam=l["toplam"],
                                         azami=LISTE_PARCA_AZAMI)
            ]
            listeler.append({"ad": l["ad"], "toplam": l["toplam"], "parcalar": parcalar})
    except SpotifyHatasi:
        # Eski bağlantının yetkisinde liste kapsamı yok (403). Hat listesiz
        # sürer; arayüz yeniden bağlanmayı önerir.
        okunamadi = True
    return {"okundu": simdi.isoformat(timespec="seconds"), "albumler": albumler,
            "en_cok": en_cok, "listeler": listeler, "listeler_okunamadi": okunamadi}


def _pencerede(gun: int | None, sinir: int | None) -> bool:
    """`sinir` None = hepsi. Tarihi bilinmeyen sinyal yalnız «hepsi»nde girer."""
    return sinir is None or (gun is not None and gun <= sinir)


def ay_gun(ay: int) -> int | None:
    """Sürgü durağı (ay) → gün sınırı; 0 → None (hepsi)."""
    return None if not ay else round(ay * 30.44)


def zamana_gore(onizleme: dict, sinir: int | None) -> tuple[list[dict], list[str]]:
    """Önizlemeden pencere içindeki (albüm kayıtları, albümsüz sanatçılar).

    Listeden gelen parçalar sanatçı başına TEK albüme iner (o listede en çok
    parçası olan): 300 parçalık bir liste 200 albüm getirip her birine gömü
    istemesin.
    """
    kayitlar = [
        {k: a[k] for k in ("sanatci", "album", "yil", "kaynak")}
        for a in onizleme.get("albumler", []) if _pencerede(a.get("gun"), sinir)
    ]
    kapsanan = {normalize_esleme(k["sanatci"]) for k in kayitlar}

    sayac: dict[tuple[str, str], list] = {}
    for l in onizleme.get("listeler", []):
        for p in l.get("parcalar", []):
            if not _pencerede(p.get("gun"), sinir):
                continue
            anahtar = (normalize_esleme(p["sanatci"]), normalize_esleme(p["album"]))
            if anahtar in sayac:
                sayac[anahtar][0] += 1
            else:
                sayac[anahtar] = [1, p]
    en_iyi: dict[str, list] = {}
    for (sanatci, _), (adet, p) in sayac.items():
        if sanatci in kapsanan:
            continue
        if sanatci not in en_iyi or adet > en_iyi[sanatci][0]:
            en_iyi[sanatci] = [adet, p]
    for adet, p in sorted(en_iyi.values(), key=lambda x: -x[0])[:LISTE_ALBUM_AZAMI]:
        kayitlar.append({"sanatci": p["sanatci"], "album": p["album"],
                         "yil": p.get("yil"), "kaynak": "spotify_liste"})
        kapsanan.add(normalize_esleme(p["sanatci"]))

    sanatcilar = []
    for s in onizleme.get("en_cok", []):
        anahtar = normalize_esleme(s["sanatci"])
        if _pencerede(s.get("gun"), sinir) and anahtar not in kapsanan:
            kapsanan.add(anahtar)
            sanatcilar.append(s["sanatci"])
    return kayitlar, sanatcilar


def onizleme_ozeti(onizleme: dict) -> dict:
    """Sürgü sayfası için küçük özet: sanatçı başına en yakın gün, liste
    başına son eklenme günü, albüm günleri. Adlar ham (K22: dile bağlı
    metin yok)."""
    sanatci: dict[str, list] = {}

    def isle(ad: str, gun: int | None):
        anahtar = normalize_esleme(ad)
        if not anahtar:
            return
        g = 10 ** 6 if gun is None else gun
        if anahtar not in sanatci:
            sanatci[anahtar] = [ad, g, 0]
        sanatci[anahtar][1] = min(sanatci[anahtar][1], g)
        sanatci[anahtar][2] += 1

    for a in onizleme.get("albumler", []):
        isle(a["sanatci"], a.get("gun"))
    for s in onizleme.get("en_cok", []):
        isle(s["sanatci"], s.get("gun"))
    listeler = []
    for l in onizleme.get("listeler", []):
        gunler = [p["gun"] for p in l.get("parcalar", []) if p.get("gun") is not None]
        for p in l.get("parcalar", []):
            isle(p["sanatci"], p.get("gun"))
        listeler.append({"ad": l["ad"], "toplam": l.get("toplam", 0),
                         "gun": min(gunler) if gunler else None})
    sirali = sorted(sanatci.values(), key=lambda s: (s[1], -s[2]))
    return {
        "sanatcilar": [{"ad": ad, "gun": None if g >= 10 ** 6 else g, "sayi": n}
                       for ad, g, n in sirali],
        "listeler": sorted(listeler, key=lambda l: (l["gun"] is None, l["gun"] or 0)),
        "albumler": [a.get("gun") for a in onizleme.get("albumler", [])
                     if a["kaynak"] == "spotify_kayitli"],
        "listeler_okunamadi": onizleme.get("listeler_okunamadi", False),
    }


def pencere_disini_sil(conn: sqlite3.Connection, kayitlar: list[dict]) -> int:
    """Daha dar bir pencereyle yeniden aktarımda, pencere dışına düşen
    SPOTIFY kaynaklı albümleri kütüphaneden çıkar. Elle liste ya da yerel
    taramayla gelenlere dokunulmaz."""
    icerde = {(normalize_esleme(k["sanatci"]), normalize_esleme(k["album"])) for k in kayitlar}
    sil = [
        r[0] for r in conn.execute(
            "SELECT album_id, artist, title FROM albums WHERE kaynak LIKE 'spotify%'")
        if (normalize_esleme(r[1]), normalize_esleme(r[2])) not in icerde
    ]
    with conn:
        conn.executemany("DELETE FROM albums WHERE album_id = ?", [(a,) for a in sil])
    return len(sil)


# --------------------------------------------------------------------------- #
# 2. Deezer eşlemesi
# --------------------------------------------------------------------------- #

def deezer_parca_bul(istemci, sanatci: str, album: str) -> dict | None:
    """Albümden doğrulanmış bir Deezer parçası: {parca_id, parca, album, yil}.

    Doğrulama `onizleme.deezer_onizleme` ile aynı ve aynı gerekçeyle:
    zayıf eşleşmede arama sanatçının HIT şarkısına düşüyor ve o klip yanlış
    albümü anlatıyor. Doğrulanamayan albüm GÖMÜLMEZ.
    """
    from python.discover.onizleme import _album_uyuyor_mu, _uyuyor_mu

    govde = istemci.get_json("search", {"q": f"{sanatci} {album}", "limit": 8})
    for kayit in (govde or {}).get("data", []):
        if not kayit.get("id"):
            continue
        if not _uyuyor_mu(sanatci, (kayit.get("artist") or {}).get("name", "")):
            continue
        bulunan_album = (kayit.get("album") or {}).get("title", "")
        if not _album_uyuyor_mu(album, bulunan_album):
            continue
        return {"parca_id": int(kayit["id"]), "parca": kayit.get("title", "")}
    return None


def sanatci_albumleri(istemci, sanatci: str, *, adet: int = 1,
                      kaynak: str = "spotify_en_cok") -> list[dict]:
    """Sanatçının Deezer'daki en popüler parçalarından en çok `adet` AYRI albüm.

    Spotify "bu sanatçıyı çok dinliyorsun" diyor ama hangi albümü demiyor;
    listeyle gelen kullanıcı da çoğu zaman yalnız sanatçı adı yazıyor. En
    popüler parça sanatçının en tanınan sesi; tek bir parça atipik bir ana
    denk gelebilir ama bu kaynak zaten bir iki albümle temsil ediliyor.
    """
    govde = istemci.get_json("search/artist", {"q": sanatci, "limit": 3})
    from python.discover.onizleme import _uyuyor_mu

    for aday in (govde or {}).get("data", []):
        if not _uyuyor_mu(sanatci, aday.get("name", "")):
            continue
        ust = istemci.get_json(f"artist/{aday['id']}/top", {"limit": 5 * adet})
        bulunan: list[dict] = []
        gorulen: set[str] = set()
        for parca in (ust or {}).get("data", []):
            albom = parca.get("album") or {}
            anahtar = normalize_esleme(albom.get("title") or "")
            if not anahtar or not parca.get("id") or anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            bulunan.append({"sanatci": aday["name"], "album": albom["title"],
                            "yil": None, "kaynak": kaynak,
                            "parca_id": int(parca["id"]),
                            "parca": parca.get("title", "")})
            if len(bulunan) >= adet:
                break
        return bulunan
    return []


def sanatci_albumu(istemci, sanatci: str) -> dict | None:
    """En çok dinlenen sanatçının en popüler parçasının albümü (Spotify yolu)."""
    bulunan = sanatci_albumleri(istemci, sanatci, adet=1)
    return bulunan[0] if bulunan else None


# --------------------------------------------------------------------------- #
# Spotify'sız giriş: elle yazılmış liste
# --------------------------------------------------------------------------- #

#: «Sanatçı — Albüm» ayırıcıları. Kısa çizgi YALNIZ boşluklar arasında:
#: «Jay-Z», «AC/DC», «Sigur Rós» bölünmemeli.
_AYIRICILAR = (" — ", " – ", " - ", "\t")


def liste_ayristir(metin: str) -> tuple[list[dict], list[str]]:
    """Serbest metin → (albüm kayıtları, albümsüz sanatçılar).

    Satır başına bir giriş: «Sanatçı» ya da «Sanatçı — Albüm». Madde işareti
    ve sıra numarası atılır; tekrarlar sanatçı+albüm anahtarıyla elenir.
    Tavan `LISTE_AZAMI_SATIR`.
    """
    import re

    kayitlar: list[dict] = []
    sanatcilar: list[str] = []
    gorulen: set[tuple[str, str]] = set()
    for satir in metin.splitlines():
        satir = re.sub(r"^\s*(?:[-*•·]|\d+[.)])\s*", "", satir).strip()
        if not satir:
            continue
        sanatci, album = satir, ""
        for ayirici in _AYIRICILAR:
            if ayirici in satir:
                sanatci, album = (p.strip() for p in satir.split(ayirici, 1))
                break
        anahtar = (normalize_esleme(sanatci), normalize_esleme(album))
        if not anahtar[0] or anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        if album:
            kayitlar.append({"sanatci": sanatci, "album": album, "yil": None,
                             "kaynak": "liste"})
        else:
            sanatcilar.append(sanatci)
        if len(kayitlar) + len(sanatcilar) >= LISTE_AZAMI_SATIR:
            break
    return kayitlar, sanatcilar


def liste_yeterli_mi(kayitlar: list[dict], sanatcilar: list[str]) -> bool:
    """Kümelemeye yetecek kadar albüm çıkabilir mi (en iyi durumda)?"""
    return len(kayitlar) + LISTE_SANATCI_ALBUM * len(sanatcilar) >= ASGARI_ALBUM


# --------------------------------------------------------------------------- #
# Kütüphaneye yazma
# --------------------------------------------------------------------------- #

def kutuphaneye_yaz(conn: sqlite3.Connection, kayitlar: list[dict]) -> int:
    """Albümleri `albums`a ekle. Var olanlar (aynı sanatçı+albüm) atlanır.

    Tekilleştirme KİMLİKLE değil sanatçı+albüm anahtarıyla: Spotify yıl
    verir, son çalınanlar vermez; aynı albüm iki kaynaktan iki ayrı kimlikle
    girerdi. Yerel taramayla gelen albüm de aynı şekilde korunur.
    """
    mevcut = {
        (normalize_esleme(r[0]), normalize_esleme(r[1]))
        for r in conn.execute("SELECT artist, title FROM albums")
    }
    bugun = datetime.now(timezone.utc).date().isoformat()
    eklenen = 0
    with conn:
        for k in kayitlar:
            anahtar = (normalize_esleme(k["sanatci"]), normalize_esleme(k["album"]))
            if not all(anahtar) or anahtar in mevcut:
                continue
            mevcut.add(anahtar)
            conn.execute(
                "INSERT OR IGNORE INTO albums (album_id, artist, title, year, "
                "eklenme_tarihi, kaynak) VALUES (?,?,?,?,?,?)",
                (album_kimligi(k["sanatci"], k["album"], k.get("yil")),
                 k["sanatci"], k["album"], k.get("yil"),
                 (k.get("eklenme") or bugun)[:10], k["kaynak"]),
            )
            eklenen += 1
    return eklenen


# --------------------------------------------------------------------------- #
# 3. CLAP gömüsü
# --------------------------------------------------------------------------- #

def gomule(
    conn: sqlite3.Connection, ilerleme: Ilerleme, *,
    gomucu: Callable[[str], np.ndarray | None] | None = None,
    istemci=None,
) -> dict[str, int]:
    """Gömüsü olmayan her albüm için: Deezer parçası → taze URL → CLAP.

    Artımlı (K6): gömüsü diskte olan albüme dokunulmaz — başka bir kullanıcı
    aynı albümü önceden gömmüşse bedava gelir. `gomucu` testte sahte gömü
    vermek için; üretimde `etiket_clap.onizleme_gomusu`.
    """
    from python.discover.calma_listesi import deezer_listesi
    from python.etiket_clap import GOMU_KLASOR

    if gomucu is None:
        from python.etiket_clap import onizleme_gomusu as gomucu
    istemci = istemci or deezer_listesi()
    GOMU_KLASOR.mkdir(parents=True, exist_ok=True)

    albumler = conn.execute(
        "SELECT album_id, artist, title FROM albums ORDER BY album_id").fetchall()
    sayac = {"hazir": 0, "gomulen": 0, "eslesmedi": 0, "onizleme_yok": 0, "hata": 0}
    ilerleme.asama("gomu", len(albumler))
    for sira, (album_id, sanatci, baslik) in enumerate(albumler, 1):
        dosya = GOMU_KLASOR / f"{album_id}.npy"
        if dosya.exists():
            sayac["hazir"] += 1
        else:
            try:
                parca = deezer_parca_bul(istemci, sanatci, baslik)
                if parca is None:
                    sayac["eslesmedi"] += 1
                else:
                    # Arama yanıtı önbellekli olabilir; URL imzası dolmuştur.
                    bilgi = istemci.get_json(
                        f"track/{parca['parca_id']}", {}, yenile=True)
                    url = (bilgi or {}).get("preview")
                    gomu = gomucu(url) if url else None
                    if gomu is None:
                        sayac["onizleme_yok"] += 1
                    else:
                        np.save(dosya, gomu)
                        sayac["gomulen"] += 1
            except Exception as hata:  # noqa: BLE001 — tek albüm hattı durdurmaz
                sayac["hata"] += 1
                print(f"  gömü hatası {sanatci} — {baslik}: {hata}", file=sys.stderr)
        ilerleme.adim(sira)
    return sayac


def gomulu_albumler(conn: sqlite3.Connection) -> list[str]:
    from python.etiket_clap import GOMU_KLASOR
    return [
        r[0] for r in conn.execute("SELECT album_id FROM albums ORDER BY album_id")
        if (GOMU_KLASOR / f"{r[0]}.npy").exists()
    ]


# --------------------------------------------------------------------------- #
# 5. Kümeleme
# --------------------------------------------------------------------------- #

def c_tavani(n: int) -> int:
    """c taramasının üst sınırı — gerekçe modül belgesinde."""
    return max(C_ALT, min(C_UST, n // KUME_BASINA_ASGARI))


def matris_yolu(kullanici_id: int) -> Path:
    return _db.KULLANICI_KOK / f"{kullanici_id}.clap.parquet"


def kumele(kullanici_id: int, conn: sqlite3.Connection) -> dict:
    """CLAP matrisini yaz, üretimin kümeleme hattını ona çalıştır.

    `kumeleme.calistir` DEĞİŞMEDEN kullanılıyor; yalnız matris ve c farklı.
    Matris tek bloklu (`clap__i`), blok ağırlığı anlamsız ve 1.0 kalıyor.
    """
    import pandas as pd

    from python.etiket_clap import gomuleri_oku
    from python.kumeleme.ayar import VARSAYILAN
    from python.kumeleme.calistir import calistir

    kimlik, A = gomuleri_oku(gomulu_albumler(conn))
    if len(kimlik) < ASGARI_ALBUM:
        raise AktarimHatasi(
            f"kümeleme için en az {ASGARI_ALBUM} albümün sesi gerekiyor, "
            f"{len(kimlik)} tanesi bulunabildi")
    matris = pd.DataFrame(
        A, index=pd.Index(kimlik, name="album_id"),
        columns=[f"clap__{i}" for i in range(A.shape[1])],
    ).reset_index()
    yol = matris_yolu(kullanici_id)
    matris.to_parquet(yol)

    sonuc = calistir(
        VARSAYILAN.ile(matris=yol, db=kullanici_db(kullanici_id),
                       c_araligi=(C_ALT, c_tavani(len(kimlik))),
                       c_secimi="en_ince_stabil"),
        sessiz=True,
    )
    return {"calisma_id": sonuc["calisma_id"], "c": sonuc["c"], "albüm": len(kimlik),
            "stabil": int((sonuc["jaccard"] >= VARSAYILAN.stabilite_esigi).sum())}


# --------------------------------------------------------------------------- #
# 6. Adaylar
# --------------------------------------------------------------------------- #

def adaylari_uret(conn: sqlite3.Connection, calisma_id: str, *, adet: int = 10) -> int:
    from python.discover.adaylar import adaylari_yaz, eksen_uret

    eksenler = [r[0] for r in conn.execute(
        "SELECT kume_id FROM clusters WHERE calisma_id = ? AND stabil_mi = 1 "
        "ORDER BY kume_id", (calisma_id,))]
    toplam = 0
    for eksen in eksenler:
        adaylar = eksen_uret(conn, calisma_id, eksen, adet=adet,
                             stratejiler=STRATEJILER)
        toplam += adaylari_yaz(conn, calisma_id, adaylar)
    return toplam


# --------------------------------------------------------------------------- #
# Yürütme
# --------------------------------------------------------------------------- #

class AktarimHatasi(RuntimeError):
    """Kullanıcıya gösterilebilir, sebebi belli bir durma."""


def calistir(
    kullanici_id: int, *, kayitlar: list[dict] | None = None,
    sanatcilar: list[str] | None = None,
    baslangic: str = "spotify", sessiz: bool = False,
    spotify_penceresi: bool = False,
) -> dict:
    """Hattı `baslangic` aşamasından sona kadar çalıştır.

    `kayitlar` verilirse Spotify'a gidilmez (elle liste / test); o zaman
    `sanatcilar` listeyle gelen albümsüz sanatçılardır ve her biri
    `LISTE_SANATCI_ALBUM` albümle temsil edilir.
    """
    ilerleme = Ilerleme(kullanici_id, sessiz=sessiz)
    # Arayüz listeyle gelen kullanıcıya «Spotify okunuyor» aşamasını göstermesin.
    ilerleme.veri["kaynak"] = ("spotify" if kayitlar is None or spotify_penceresi
                               else "liste")
    ilerleme._yaz()
    atla = ASAMALAR.index(baslangic)
    conn = baglan_kullanici(kullanici_id)
    try:
        if atla <= ASAMALAR.index("eslesme"):
            if kayitlar is None:
                ilerleme.asama("spotify")
                kayitlar, sanatcilar = spotify_kayitlari(erisim_jetonu(kullanici_id))
                adet, kaynak = 1, "spotify_en_cok"
            elif spotify_penceresi:
                # Önizlemeden, kullanıcının seçtiği pencereyle.
                sanatcilar = sanatcilar or []
                adet, kaynak = 1, "spotify_en_cok"
            else:
                sanatcilar = sanatcilar or []
                adet, kaynak = LISTE_SANATCI_ALBUM, "liste"
            ilerleme.ozet(spotify_albüm=len(kayitlar),
                          albümsüz_sanatçı=len(sanatcilar))

            ilerleme.asama("eslesme", len(sanatcilar))
            from python.discover.calma_listesi import deezer_listesi
            istemci = deezer_listesi()
            art_arda_hata = 0
            for sira, sanatci in enumerate(sanatcilar, 1):
                try:
                    kayitlar.extend(sanatci_albumleri(istemci, sanatci, adet=adet,
                                                      kaynak=kaynak))
                    art_arda_hata = 0
                except Exception:  # noqa: BLE001 — tek sanatçı hattı durdurmaz
                    art_arda_hata += 1
                    if art_arda_hata >= AG_HATA_ESIGI:
                        raise AktarimHatasi(
                            "Deezer'a ulaşılamıyor — birkaç dakika sonra yeniden dene")
                ilerleme.adim(sira)
            if spotify_penceresi:
                ilerleme.ozet(pencere_disi=pencere_disini_sil(conn, kayitlar))
            ilerleme.ozet(eklenen_albüm=kutuphaneye_yaz(conn, kayitlar))

        if atla <= ASAMALAR.index("gomu"):
            ilerleme.ozet(gomu=gomule(conn, ilerleme))

        if atla <= ASAMALAR.index("hasat"):
            from python.discover.calma_listesi import (
                birliktelik, birliktelik_yaz, deezer_listesi, hasat,
            )
            ilerleme.asama("hasat")
            h = hasat(conn, deezer_listesi(), adim=ilerleme.adim)
            ilerleme.ozet(yeni_liste=h["liste"],
                          birliktelik=birliktelik_yaz(conn, birliktelik(conn)))

        if atla <= ASAMALAR.index("kume"):
            ilerleme.asama("kume")
            ilerleme.ozet(kume=kumele(kullanici_id, conn))

        ilerleme.asama("aday")
        calisma_id = conn.execute(
            "SELECT calisma_id FROM clusters ORDER BY calisma_id DESC LIMIT 1"
        ).fetchone()
        if calisma_id is None:
            raise AktarimHatasi("kümeleme çalışması yok")
        adet = adaylari_uret(conn, calisma_id[0])
        if not adet:
            raise AktarimHatasi(
                "hiç stabil eksen çıkmadı ya da adaylar üretilemedi — "
                "kütüphane büyüdükçe yeniden dene")
        ilerleme.ozet(aday=adet)
    except Exception as hata:
        ilerleme.bitir(hata=str(hata) if isinstance(hata, AktarimHatasi)
                       else f"{type(hata).__name__}: {hata}")
        raise
    finally:
        conn.close()
    ilerleme.bitir()
    return ilerleme.veri


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--kullanici", type=int, required=True)
    a.add_argument("--json", type=Path,
                   help="Spotify yerine liste: [{sanatci, album, yil?}]")
    a.add_argument("--asama", choices=ASAMALAR, default="spotify",
                   help="bu aşamadan başla (öncekiler yapılmış sayılır)")
    a.add_argument("--onizle", action="store_true",
                   help="yalnız Spotify'ı oku ve zaman penceresi seçimini bekle")
    a.add_argument("--ay", type=int,
                   help="önizlemeden, son N ayla aktar (0 = hepsi)")
    args = a.parse_args(argv)

    if args.onizle:
        ilerleme = Ilerleme(args.kullanici)
        ilerleme.veri["kaynak"] = "spotify"
        ilerleme.asama("spotify")
        try:
            veri = spotify_onizleme(erisim_jetonu(args.kullanici))
        except Exception as hata:  # noqa: BLE001
            ilerleme.bitir(hata=f"Spotify okunamadı: {type(hata).__name__}")
            raise
        yol = onizleme_yolu(args.kullanici)
        gecici = yol.with_suffix(".tmp")
        gecici.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
        gecici.replace(yol)
        ilerleme.secim_bekle()
        return 0

    if args.ay is not None:
        onizleme = json.loads(onizleme_yolu(args.kullanici).read_text(encoding="utf-8"))
        kayitlar, sanatcilar = zamana_gore(onizleme, ay_gun(args.ay))
        try:
            sonuc = calistir(args.kullanici, kayitlar=kayitlar, sanatcilar=sanatcilar,
                             spotify_penceresi=True)
        except AktarimHatasi as hata:
            print(f"\nDURDU: {hata}", file=sys.stderr)
            return 1
        print(json.dumps(sonuc["ozet"], ensure_ascii=False, indent=2))
        return 0

    kayitlar = sanatcilar = None
    if args.json:
        kayitlar, sanatcilar = [], []
        for k in json.loads(args.json.read_text(encoding="utf-8")):
            if not k.get("album"):
                sanatcilar.append(k["sanatci"])
                continue
            kayitlar.append({
                "sanatci": k["sanatci"], "album": k["album"],
                "yil": yil_ayikla(k.get("yil")),
                "kaynak": k.get("kaynak", "spotify_kayitli")})
    bas = time.monotonic()
    try:
        sonuc = calistir(args.kullanici, kayitlar=kayitlar, sanatcilar=sanatcilar,
                         baslangic=args.asama)
    except AktarimHatasi as hata:
        print(f"\nDURDU: {hata}", file=sys.stderr)
        return 1
    print(json.dumps(sonuc["ozet"], ensure_ascii=False, indent=2))
    print(f"{time.monotonic() - bas:.0f} sn", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
