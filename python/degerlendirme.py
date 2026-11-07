"""Değerlendirme: motor, senin sanatçını sıfırdan bulabilir mi?

Bugüne kadar "öneri iyi mi?" sorusu kulakla cevaplandı. Bu modül her stratejiye
bir SAYI verir, böylece bundan sonraki her değişikliğin işe yarayıp yaramadığı
tahmin değil ölçüm olur.

ÖLÇÜT KULLANICININ SEÇİMİ (2026-09-01)
Başarı = HİÇ DUYMADIĞIN SANATÇI. "Zaten biliyorum" bir başarısızlık. Bu seçim
sınamanın biçimini belirledi; başka bir ölçüt seçilseydi düzenek de başka
olurdu.

NEDEN ALBÜM DEĞİL, SANATÇI GİZLENİYOR
Klasik leave-one-out bir albümü gizler ve geri gelip gelmediğine bakar. Burada
o ölçüt YANLIŞ olurdu: sanatçının diğer albümleri kütüphanede kalır, motor onu
kredi bağından bulur, sen de "zaten biliyorum" dersin. Ölçtüğümüz şey tam
olarak kaçındığımız şey olur.

Bu yüzden sanatçının TÜM albümleri gizleniyor. Kalan kütüphane, o sanatçıyı
hiç tanımayan birinin kütüphanesi. Soru: bu hâldeki motor, gerçekte seveceğin
—kanıt: sahipsin— bir sanatçıyı hiç görmediği hâlde listenin başına koyabiliyor
mu?

Bu ikamenin bir zayıflığı var ve yazıya geçmesi gerekiyor: sahip olduğun
sanatçı, "hoşuna gidecek ama tanımadığın sanatçı"nın kusursuz vekili değil.
Sahip olduklarının bulunabilir olması gerek şart, yeter şart değil. Ölçtüğümüz
şey erişim gücü; beğeni değil. Beğeniyi ancak geri bildirim söyler (n=15).

ÜÇ ÖLÇÜM, ÜÇÜ DE TASARIMI DEĞİŞTİRDİ
1. Saklanmış PMI tablosu kendi kendini değerlendiremez: `liste_birlikteligi`
   hesaplanırken kütüphane sanatçıları aday havuzundan çıkarılıyor. Ölçüldü —
   1.615 aday anahtarının 0'ı kütüphanede. Bu yüzden PMI burada YENİDEN
   hesaplanıyor, kütüphane kısıtı olmadan.
2. `adaylar.ses_benzerligi` açık havuzda arama YAPMIYOR; `adaylar` tablosunu
   yeniden sıralıyor (621 satır). Gizlenen sanatçı o tabloda olmadığı için
   asla bulunamaz. Değerlendirilen şey `ses_kume`'nin açık havuz erişimi:
   Jiro Inagaki'yi bulan yol da buydu.
3. Tavan: 147 kütüphane sanatçısının 132'si çalma listelerinde geçiyor,
   101'inin CLAP gömüsü var. Erişilemeyen sanatçı sıralama hatası değil
   kapsama boşluğudur; ayrı raporlanıyor.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from math import log
from pathlib import Path

import numpy as np

from python.db import VARSAYILAN_DB, baglan
# RRF üretimde yaşıyor (K19: değerlendirme üretimi ÇAĞIRIR, kopyalamaz).
from python.discover.adaylar import RRF_K, melez_sirala  # noqa: F401
from python.etiket_clap import GOMU_KLASOR, PARCA_GOMU
from python.onbellek import AgYok
from python.metin import normalize_esleme

#: Rapor edilen kesme noktaları. 1 = "listenin başında mı", 50 = "hiç
#: değilse sayfada mı". Aradakiler eğrinin şeklini gösteriyor.
KESMELER = (1, 5, 10, 50)

#: PMI için asgari birlikte görülme. `calma_listesi.birliktelik` ile aynı:
#: tek listede bir kez yan yana gelmek tesadüf olabilir, iki liste iki ayrı
#: insanın aynı bağı kurması demek.
ASGARI_BIRLIKTE = 2


# --------------------------------------------------------------------------- #
# Kütüphane
# --------------------------------------------------------------------------- #

def kutuphane(conn: sqlite3.Connection) -> dict[str, str]:
    """{normalize anahtar: gösterim adı} — gizlenecek sanatçılar."""
    esleme: dict[str, str] = {}
    for (ad,) in conn.execute("SELECT DISTINCT artist FROM albums WHERE artist != ''"):
        anahtar = normalize_esleme(ad)
        if anahtar:
            esleme.setdefault(anahtar, ad)
    return esleme


# --------------------------------------------------------------------------- #
# Sızıntı — gizlenenin ADIYLA bulunmuş listeler
# --------------------------------------------------------------------------- #

def sizinti_listeleri(conn: sqlite3.Connection) -> dict[str, set[int]]:
    """{sanatçı anahtarı: yalnız O sanatçının aramasıyla bulunmuş listeler}.

    SIZINTI (2026-10-20, iki ayrı literatür ajanı bağımsız buldu). Listeler
    kütüphanedeki her sanatçının ADIYLA Deezer'da aranarak toplandı
    (`calma_listesi.hasat`). Bir sanatçı gizlendiğinde onun adıyla bulunmuş
    listeler veride kalırsa, motor gizleneni tam da onu aramış olmamız
    sayesinde bulur — üretimde hiç duymadığın bir sanatçının adı aranmaz.
    Tavan, sıralar ve popülerlik şişer; en çok liste yolu kazanır.

    Kural: liste p, a'nın katmanında ancak a DIŞINDA bir sanatçının araması
    da p'yi bulduysa kalır. Bulucular önbellekteki arama yanıtlarından kurulur
    (ağ yok); yanıt önbellekte yoksa `tohum_sanatci` (ilk bulan) kullanılır.
    """
    from python.discover.calma_listesi import deezer_listesi, liste_ara

    tohumlar = {r[0] for r in conn.execute(
        "SELECT DISTINCT tohum_sanatci FROM calma_listesi WHERE tohum_sanatci != ''")}
    tohumlar |= {r[0] for r in conn.execute("SELECT DISTINCT artist FROM albums") if r[0]}
    istemci = deezer_listesi(cevrimdisi=True)
    bulucu: dict[int, set[str]] = defaultdict(set)
    for ad in tohumlar:
        for liste in liste_ara(istemci, ad):
            if liste.get("id"):
                bulucu[int(liste["id"])].add(normalize_esleme(ad))
    for liste_id, ad in conn.execute(
            "SELECT liste_id, tohum_sanatci FROM calma_listesi WHERE tohum_sanatci != ''"):
        bulucu[int(liste_id)].add(normalize_esleme(ad))
    # Bulucu, gizlenenin adını İÇERİYORSA da gizlenenin aramasıdır: «Allan
    # Holdsworth & Gordon Beck» araması Holdsworth listelerini getirir.
    sonuc: dict[str, set[int]] = defaultdict(set)
    for a in kutuphane(conn):
        for liste_id, bulanlar in bulucu.items():
            if all(_ad_icerir(b, a) for b in bulanlar):
                sonuc[a].add(liste_id)
    return dict(sonuc)


def _ad_icerir(arama: str, ad: str) -> bool:
    """Normalize `arama`, normalize `ad`ı tam sözcükler olarak içeriyor mu?"""
    return f" {ad} " in f" {arama} "


# --------------------------------------------------------------------------- #
# Kapsam — sorgu tüm kütüphane mi, gizlenenin ekseni mi?
# --------------------------------------------------------------------------- #

def eksen_haritasi(
    conn: sqlite3.Connection, calisma_id: str | None = None,
) -> dict[str, set[str]]:
    """{sanatçı anahtarı: aynı eksene keskin atanmış sanatçı anahtarları}.

    Uygulama tüm kütüphaneye karşı öneri yapmıyor, EKSEN EKSEN yapıyor
    ("hangi tarafını beslemek istiyorsun?"). Değerlendirme de öyle yapmalı:
    Allan Holdsworth'ü 147 sanatçılık karışık bir sorguya karşı aramak, ürünün
    yapmadığı bir işi ölçmek olur. Sorgu, gizlenenin ait olduğu eksenin geri
    kalanı.

    Keskin atama (`idxmax`) kullanılıyor: bulanık üyeliklerin tamamı alınırsa
    her albüm her eksene bir miktar girer ve eksen ayrımı anlamını yitirir.
    """
    if calisma_id is None:
        satir = conn.execute(
            "SELECT calisma_id FROM clusters ORDER BY calisma_id DESC LIMIT 1"
        ).fetchone()
        if not satir:
            return {}
        calisma_id = satir[0]

    en_iyi: dict[str, tuple[int, float]] = {}
    for album_id, kume_id, uyelik in conn.execute(
        "SELECT album_id, kume_id, uyelik FROM memberships WHERE calisma_id=?",
        (calisma_id,),
    ):
        onceki = en_iyi.get(album_id)
        if onceki is None or uyelik > onceki[1]:
            en_iyi[album_id] = (kume_id, uyelik)

    album_sanatci = {
        r[0]: normalize_esleme(r[1])
        for r in conn.execute("SELECT album_id, artist FROM albums") if r[1]
    }
    eksen_uyeleri: dict[int, set[str]] = defaultdict(set)
    sanatci_eksen: dict[str, set[int]] = defaultdict(set)
    for album_id, (kume_id, _) in en_iyi.items():
        anahtar = album_sanatci.get(album_id)
        if anahtar:
            eksen_uyeleri[kume_id].add(anahtar)
            sanatci_eksen[anahtar].add(kume_id)

    harita: dict[str, set[str]] = {}
    for anahtar, eksenler in sanatci_eksen.items():
        komsu: set[str] = set()
        for e in eksenler:
            komsu |= eksen_uyeleri[e]
        harita[anahtar] = komsu - {anahtar}
    return harita


# --------------------------------------------------------------------------- #
# Erişim 1 — çalma listesi birlikteliği (PMI)
# --------------------------------------------------------------------------- #

def pmi_tablosu(
    conn: sqlite3.Connection, tohumlar: set[str], *, olcut: str = "pmi",
    buzulme: float = 0.0, agirlik: str = "esit",
    haric_listeler: set[int] | frozenset[int] = frozenset(),
) -> dict[str, dict[str, float]]:
    """{tohum: {aday: pmi}} — kütüphane kısıtı OLMADAN.

    Saklanmış `liste_birlikteligi` kullanılamaz (bkz. modül başlığı): orada
    kütüphane sanatçıları aday olamıyor, oysa değerlendirmenin tamamı gizlenen
    kütüphane sanatçısının aday olarak geri gelmesine bakıyor.

    PMI(a,b) kütüphaneden bağımsız bir birliktelik istatistiği; hangi a'nın
    tohum, hangi b'nin aday sayılacağını kütüphane belirler, sayının kendisini
    değil. Bu yüzden bir kez hesaplanıp her gizlemede yeniden kullanılıyor.
    """
    listeler: dict[int, set[str]] = defaultdict(set)
    for liste_id, anahtar in conn.execute(
        "SELECT liste_id, sanatci_anahtar FROM liste_parca "
        "WHERE sanatci_anahtar != ''"
    ):
        if liste_id not in haric_listeler:
            listeler[liste_id].add(anahtar)

    if len(listeler) < 5:
        return {}

    # Liste ağırlığı ÜRETİMİN işleviyle (K19: değerlendirme üretimi çağırır,
    # kopyalamaz). Eşik ve büzülme ham liste sayısıyla — üretimle aynı.
    from python.discover.calma_listesi import liste_agirligi
    w = {lid: liste_agirligi(len(u), agirlik) for lid, u in listeler.items()}
    toplam = sum(w.values())

    gorulme: Counter = Counter()
    for lid, uyeler in listeler.items():
        for x in uyeler:
            gorulme[x] += w[lid]

    birlikte: Counter = Counter()
    ham: Counter = Counter()
    for lid, uyeler in listeler.items():
        icerdeki = uyeler & tohumlar
        if not icerdeki:
            continue
        for a in icerdeki:
            for b in uyeler:
                if a != b:
                    birlikte[(a, b)] += w[lid]
                    ham[(a, b)] += 1

    tablo: dict[str, dict[str, float]] = defaultdict(dict)
    for (a, b), agirlikli in birlikte.items():
        adet = ham[(a, b)]
        if adet < ASGARI_BIRLIKTE:
            continue
        p_ab = agirlikli / toplam
        p_a, p_b = gorulme[a] / toplam, gorulme[b] / toplam
        if p_a <= 0 or p_b <= 0:
            continue
        deger = log(p_ab / (p_a * p_b))
        if olcut == "npmi":
            # PMI'nın bilinen nadir-öğe yanlılığı: iki listede geçip ikisinde
            # de tohumla yan yana olan bir sanatçı, yüz listede geçen ve elli
            # kez yan yana gelenden yüksek skor alır. -log(p_ab)'ye bölmek
            # skoru [-1, 1]'e sıkıştırır ve bu yanlılığı söndürür.
            payda = -log(p_ab)
            deger = deger / payda if payda > 0 else 0.0
        if buzulme > 0:
            # KANIT GÜCÜ. npmi'nin tavanı +1 ve iki liste onu doldurmaya
            # yetiyor: «2 listede birlikte» ile «16 listede birlikte» aynı
            # skoru alabiliyor. n/(n+k) çarpanı az kanıtı sıfıra doğru
            # büzüyor, çok kanıtta 1'e yaklaşıp etkisiz kalıyor.
            deger *= adet / (adet + buzulme)
        tablo[a][b] = deger
    return tablo


def pmi_sirala(
    tablo: dict[str, dict[str, float]], tohumlar: set[str], sahip: set[str],
) -> list[str]:
    """Tohumlara PMI ile bağlı, `sahip` dışındaki adaylar — skora göre sıralı.

    Skor `MAX(pmi)`, `adaylar.liste_birlikteligi` ile aynı: bir sanatçıyla
    güçlü bağ, beş sanatçıyla zayıf bağdan iyidir.
    """
    skor: dict[str, float] = {}
    for a in tohumlar:
        for b, deger in tablo.get(a, {}).items():
            if b in sahip:
                continue
            if deger > skor.get(b, float("-inf")):
                skor[b] = deger
    return [b for b, _ in sorted(skor.items(), key=lambda x: -x[1])]


# --------------------------------------------------------------------------- #
# Erişim 2 — CLAP ses benzerliği (açık havuz)
# --------------------------------------------------------------------------- #

def gomu_haritalari(
    conn: sqlite3.Connection,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """({kütüphane anahtarı: vektörler}, {havuz anahtarı: vektörler}).

    Kütüphane tarafı `data/cache/clap` (albüm gömüleri), havuz tarafı
    `data/cache/clap_parca` (çalma listesi parçaları). Havuz SAHİPLİĞE GÖRE
    ELENMİYOR — `ses_kume.havuz_gomuleri` eliyor ama burada gizlenen sanatçının
    havuzda kalması sınamanın ta kendisi.
    """
    kutup: dict[str, list[np.ndarray]] = defaultdict(list)
    album_ad = {
        r[0]: r[1] for r in conn.execute("SELECT album_id, artist FROM albums")
    }
    for dosya in GOMU_KLASOR.glob("*.npy"):
        ad = album_ad.get(dosya.stem)
        if ad:
            kutup[normalize_esleme(ad)].append(np.load(dosya))

    parca_ad = {}
    for parca_id, sanatci in conn.execute(
        "SELECT parca_id, sanatci FROM liste_parca WHERE parca_id IS NOT NULL"
    ):
        parca_ad[int(parca_id)] = sanatci
    havuz: dict[str, list[np.ndarray]] = defaultdict(list)
    havuz_parca: dict[str, list[int]] = defaultdict(list)
    for dosya in sorted(PARCA_GOMU.glob("*.npy")):
        try:
            ad = parca_ad.get(int(dosya.stem))
        except ValueError:
            continue
        if ad:
            havuz[normalize_esleme(ad)].append(np.load(dosya))
            havuz_parca[normalize_esleme(ad)].append(int(dosya.stem))
    # Sızıntı düzeltmesi parçanın HANGİ listelerden geldiğini bilmeli.
    gomu_haritalari.parcalar = dict(havuz_parca)

    yigin = lambda d: {a: np.stack(v) for a, v in d.items() if v}  # noqa: E731
    return yigin(kutup), yigin(havuz)


class SesErisimi:
    """Hubness düzeltmeli CLAP erişimi, gizleme başına yeniden hesaplanan taban.

    Benzerlik matrisi BİR KEZ hesaplanıyor (havuz × kütüphane). Her gizlemede
    yalnızca sütunlar daraltılıp taban yeniden alınıyor — 147 gizleme için 147
    matris çarpımı yerine bir tane.

    Hubness düzeltmesi `etiket_clap.benzer_adaylar` ile aynı gerekçeyle burada:
    düzeltmesiz sıralamada "her şeye benzeyen" kayıtlar (ölçüldü: Foo Fighters
    beş adayın dördüne en yakın çıkıyordu) listeyi kaplıyor. Taban, KALAN
    kütüphaneye göre alınıyor — gizlenen sanatçı tabana karışırsa kendi
    bulunmasını kolaylaştırır, bu da sızıntı olurdu.
    """

    def __init__(self, kutup: dict[str, np.ndarray], havuz: dict[str, np.ndarray],
                 parcalar: dict[str, list[int]] | None = None):
        self.havuz_anahtar = sorted(havuz)
        self.havuz_sahip: list[str] = []
        self.havuz_parca: list[int | None] = []
        havuz_satir = []
        for a in self.havuz_anahtar:
            kimlik = (parcalar or {}).get(a, [])
            for k, v in enumerate(havuz[a]):
                havuz_satir.append(v)
                self.havuz_sahip.append(a)
                self.havuz_parca.append(kimlik[k] if k < len(kimlik) else None)
        self.P = np.stack(havuz_satir) if havuz_satir else np.zeros((0, 512), "float32")

        self.kutup_sahip: list[str] = []
        kutup_satir = []
        for a in sorted(kutup):
            for v in kutup[a]:
                kutup_satir.append(v)
                self.kutup_sahip.append(a)
        self.L = np.stack(kutup_satir) if kutup_satir else np.zeros((0, 512), "float32")

        # Havuz × kütüphane ve kütüphane × kütüphane: ikisi de bir kez.
        self.S = self.P @ self.L.T if self.P.size and self.L.size else np.zeros((0, 0))
        self.LL = self.L @ self.L.T if self.L.size else np.zeros((0, 0))
        self._sahip_dizi = np.array(self.kutup_sahip)

    #: "en_yakin_eksen": parça yalnız EN YAKIN kütüphane albümü sorgu
    #: ekseninde ise sayılır. "cok_sesli": komşu çoğunluğu + sanatçı başına
    #: birden çok parça (`etiket_clap.komsu_cogunlugu` / `sanatci_sirala` —
    #: üretimin işlevleri ÇAĞRILIR, K19). Varsayılan üretiminki.
    from python.etiket_clap import SES_KURALI as kural
    from python.etiket_clap import SES_OLCEGI as olcek

    def sirala(
        self, gizlenen: str, sahip: set[str], sorgu: set[str] | None = None,
        haric_satir: np.ndarray | None = None,
    ) -> list[str]:
        """`sorgu` sanatçılarına en yakın havuz sanatçıları, sıralı.

        `sorgu` None ise tüm kalan kütüphane. Eksen kapsamında sorgu yalnızca
        gizlenenin ekseni; TABAN yine tüm kalan kütüphaneye göre alınıyor.
        Bu ayrım `etiket_clap.benzer_adaylar` ile aynı ve kasıtlı: hubness
        genel bir özellik, eksen içinde ölçülürse "bu eksene her şey benziyor"
        etkisi düzeltilmemiş kalır.
        """
        if self.S.size == 0:
            return []
        kalan = self._sahip_dizi != gizlenen
        if not kalan.any():
            return []
        if sorgu is None:
            sutun = kalan
        else:
            sutun = kalan & np.isin(self._sahip_dizi, list(sorgu))
            if not sutun.any():
                return []

        taban_havuz = self.S[:, kalan].mean(axis=1, keepdims=True)
        taban_uye = self.LL[np.ix_(sutun, kalan)].mean(axis=1)
        duzeltilmis = self.S[:, sutun] - taban_havuz - taban_uye[None, :]

        # Satır (parça) skoru = sorguya en yakın olduğu nokta.
        satir = duzeltilmis.max(axis=1)
        # Sızan listelerden gelen parça bu katmanda havuzda yok.
        dusen = haric_satir if haric_satir is not None else np.zeros(len(satir), bool)

        if self.kural == "cok_sesli" and sorgu is not None:
            from python.etiket_clap import komsu_cogunlugu, sanatci_sirala, ses_olcegi
            tum = ses_olcegi(self.S[:, kalan], taban_havuz,
                             self.LL[np.ix_(kalan, kalan)].mean(axis=1)[None, :],
                             self.olcek)
            eksende = np.isin(self._sahip_dizi[kalan], list(sorgu))
            # Düşen parça bu katmanda havuzda YOK: NaN değil, hiç verilmez —
            # yoksa sanatçının parça sayısında kalır ve tek parça kuralı
            # (üretimde geçerli olan) hiç uygulanamaz.
            kal = ~dusen
            sayi, ort = komsu_cogunlugu(tum[kal], eksende)
            sk = sanatci_sirala(ort, sayi, [a for a, k in zip(self.havuz_sahip, kal) if k])
            sk = {a: d for a, d in sk.items() if not (a in sahip and a != gizlenen)}
            return [a for a, _ in sorted(sk.items(), key=lambda x: -x[1])]

        if self.kural == "en_yakin_eksen" and sorgu is not None:
            # En yakın albümü sorgu dışında kalan parça bu eksenin adayı değil.
            tum = (self.S[:, kalan] - taban_havuz
                   - self.LL[np.ix_(kalan, kalan)].mean(axis=1)[None, :])
            eksende = np.isin(self._sahip_dizi[kalan], list(sorgu))
            satir = np.where(eksende[tum.argmax(axis=1)], satir, -np.inf)

        skor: dict[str, float] = {}
        for deger, anahtar, d in zip(satir, self.havuz_sahip, dusen):
            if d or (anahtar in sahip and anahtar != gizlenen):
                continue
            if deger == -np.inf:
                continue
            if deger > skor.get(anahtar, float("-inf")):
                skor[anahtar] = float(deger)
        return [a for a, _ in sorted(skor.items(), key=lambda x: -x[1])]


# --------------------------------------------------------------------------- #
# Erişim 4 — ağ isteyen stratejiler, ÖNBELLEKTEN
# --------------------------------------------------------------------------- #

#: MusicBrainz/Discogs/ListenBrainz kullanan stratejiler. Diğer ikisi gibi
#: yeniden yazılmıyorlar; ÜRETİM İŞLEVİ doğrudan çağrılıyor (K19).
AG_STRATEJILERI = ("kredi_sicramasi", "sahne_komsulugu", "bilincli_uzaklik")


def gizli_kopya(conn: sqlite3.Connection, gizli: str) -> sqlite3.Connection:
    """Kütüphanenin bellekteki kopyası; gizlenen sanatçının albümleri silinmiş.

    Diğer iki erişim yolu sorguyu parametre olarak alabiliyordu. Bu üç strateji
    kütüphaneyi doğrudan `conn`'dan okuyor (`eksen_sanatcilari`,
    `kutuphane_anahtarlari`, `eksen_muzisyenleri`). Onları değiştirmek yerine
    VERİTABANINI değiştiriyoruz — böylece ölçülen şey üretim kodunun kendisi
    oluyor, kopyası değil.

    `albums` üzerindeki ON DELETE CASCADE `credits`, `memberships`,
    `audio_features`, `stem_profili` ve diğerlerini de temizliyor; yani kopya
    gerçekten "o sanatçıyı hiç almamış" bir kütüphane.
    """
    kopya = sqlite3.connect(":memory:")
    conn.backup(kopya)
    kopya.row_factory = sqlite3.Row
    kopya.execute("PRAGMA foreign_keys = ON")
    silinecek = [
        r[0] for r in kopya.execute("SELECT album_id, artist FROM albums")
        if normalize_esleme(r[1] or "") == gizli
    ]
    if silinecek:
        with kopya:
            kopya.executemany(
                "DELETE FROM albums WHERE album_id = ?",
                [(a,) for a in silinecek],
            )
    return kopya


def ag_siralamasi(
    kopya: sqlite3.Connection, calisma_id: str, eksen: int, strateji: str, *,
    frekans: dict[str, int] | None = None, adet: int = 400,
    genis: bool = False,
) -> list[str] | None:
    """Bir ağ stratejisinin sanatçı sıralaması. Önbellek yetmezse None.

    `cevrimdisi=True`: ölçüm sırasında hiçbir ağ isteği yapılmaz. 147 gizleme ×
    3 strateji ile MusicBrainz'e saniyede bir istek kuralıyla gidilseydi ölçüm
    saatler sürerdi ve dış servise yük olurdu. Önbellekte olmayan bir istek
    `AgYok` veriyor; o gizleme O STRATEJİ İÇİN ölçülemedi sayılıyor ve ayrı
    raporlanıyor — başarısızlıkla karıştırılmıyor.
    """
    from python.discover import adaylar as A

    # `genis`: üretimdeki dar ayarların mı yoksa yöntemin kendisinin mi
    # yetmediğini ayırmak için. Emekliye ayırma kararı, ancak yöntem geniş
    # ayarla da başarısızsa yönteme yazılabilir.
    try:
        if strateji == "kredi_sicramasi":
            dc = A.discogs(cevrimdisi=True)
            if dc is None:
                return None
            ek = {"kisi_adedi": 24, "kisi_basina": 120} if genis else {}
            sonuc = A.kredi_sicramasi(kopya, dc, calisma_id, eksen, **ek)
        elif strateji == "sahne_komsulugu":
            ek = ({"sanatci_adedi": 20, "komsu_adedi": 60, "album_adedi": 10}
                  if genis else {})
            sonuc = A.sahne_komsulugu(
                kopya, A.musicbrainz(cevrimdisi=True),
                A.listenbrainz(cevrimdisi=True), calisma_id, eksen, **ek)
        elif strateji == "bilincli_uzaklik":
            ek = {"sanatci_adedi": 20, "komsu_adedi": 50} if genis else {}
            sonuc = A.bilincli_uzaklik(
                kopya, A.musicbrainz(cevrimdisi=True),
                A.listenbrainz(cevrimdisi=True), calisma_id, eksen,
                frekans=frekans or {}, **ek)
        else:
            raise ValueError(strateji)
    except AgYok:
        return None
    except Exception:
        # Önbellek eksikliği bazen AgYok'a değil ayrıştırma hatasına düşüyor
        # (yarım kalmış kayıt). Ölçülemedi saymak, çökmekten doğru.
        return None

    gorulen, sira = set(), []
    for aday in sonuc[:adet]:
        anahtar = normalize_esleme(aday.artist)
        if anahtar not in gorulen:
            gorulen.add(anahtar)
            sira.append(anahtar)
    return sira


# --------------------------------------------------------------------------- #
# Sınama
# --------------------------------------------------------------------------- #

def sira_bul(siralama: list[str], hedef: str) -> int | None:
    """1 tabanlı sıra, yoksa None."""
    try:
        return siralama.index(hedef) + 1
    except ValueError:
        return None


def ozet(
    siralar: list[int | None], erisilebilir: int, havuz_boyu: int = 0,
) -> dict[str, float]:
    """recall@k, MRR, tavan ve YÜZDELİK.

    İki paydayı da raporluyoruz çünkü ikisi ayrı soru:
    `recall` bütün kütüphaneye göre "motor beni bulur mu",
    `recall_erisilebilir` havuzda olanlara göre "SIRALAMA doğru mu".
    Birincisi kapsama + sıralama, ikincisi yalnız sıralama.

    `medyan_yuzdelik` (sıra / havuz boyu) ŞART ve bunun sebebi ölçüldü
    (2026-09-02). Havuz 2.163'ten 4.183 gömüye çıkarıldığında ses erişiminin
    recall@50'si 0,08'den 0,03'e DÜŞTÜ ve bu "erişim kötüleşti" diye
    okunabilirdi. Okunamaz: havuz iki katına çıkınca rakip sayısı da iki
    katına çıkıyor, sabit k'lı ölçüt bunu ceza olarak yazıyor. Aynı ölçümde
    yüzdelik 0,349'dan 0,311'e İYİLEŞTİ.

    Kural: farklı havuz boyları arasında yalnız yüzdelik kıyaslanır; recall@k
    ancak havuz sabitken kıyaslanabilir. Rastgele erişimin yüzdeliği 0,50'dir.
    """
    n = len(siralar)
    bulunan = [s for s in siralar if s is not None]
    sonuc: dict[str, float] = {
        "gizlenen": n,
        "erisilebilir": erisilebilir,
        "bulunan": len(bulunan),
    }
    for k in KESMELER:
        isabet = sum(1 for s in bulunan if s <= k)
        sonuc[f"recall@{k}"] = isabet / n if n else 0.0
        sonuc[f"recall@{k}_eris"] = isabet / erisilebilir if erisilebilir else 0.0
    sonuc["mrr"] = sum(1 / s for s in bulunan) / n if n else 0.0
    sonuc["medyan_sira"] = (
        float(np.median(bulunan)) if bulunan else float("nan")
    )
    sonuc["havuz_boyu"] = havuz_boyu
    sonuc["medyan_yuzdelik"] = (
        float(np.median(bulunan)) / havuz_boyu
        if bulunan and havuz_boyu else float("nan")
    )
    return sonuc


def calistir(
    conn: sqlite3.Connection, *, limit: int | None = None, ayrinti: bool = False,
    kapsam: str = "eksen", olcut: str = "pmi", buzulme: float = 0.0,
    liste_agirlik: str = "esit",
    calisma: str | None = None,
    melez_agirlik: tuple[float, float] = (1.0, 1.0), ag: bool = False,
    ag_genis: bool = False, sizinti: bool = True, motor: bool = False,
    dis_komsular: dict[str, dict[str, list[dict]]] | None = None,
) -> dict[str, dict]:
    """Her kütüphane sanatçısını sırayla gizle, her erişimin sırasını topla.

    `kapsam="eksen"` ürünün yaptığı işi ölçer: sorgu, gizlenenin ait olduğu
    ekseninin geri kalanı. `kapsam="tum"` tüm kütüphaneyi sorgu yapar —
    kıyas için duruyor, ikisinin farkı eksen ayrımının değerini gösteriyor.
    """
    kut = kutuphane(conn)
    anahtarlar = sorted(kut)
    if limit:
        anahtarlar = anahtarlar[:limit]
    sahip_tam = set(kut)
    print(f"{len(anahtarlar)} sanatçı gizlenecek "
          f"(kütüphanede {len(kut)} tekil sanatçı)", file=sys.stderr)

    # `calisma` verilirse O kümelemeye göre ölçülür. Farklı küme sayılarıyla
    # yapılmış çalışmalar veritabanında duruyor; aynı havuz ve aynı sınama
    # ile kıyaslamak, "c kaç olmalı" sorusunu içsel geçerlilik indeksiyle
    # değil ÖNERİ KALİTESİYLE cevaplamayı sağlıyor (K19).
    harita = eksen_haritasi(conn, calisma) if kapsam == "eksen" else {}
    if kapsam == "eksen":
        kapsanan = sum(1 for a in anahtarlar if harita.get(a))
        print(f"eksen kapsamı: {kapsanan}/{len(anahtarlar)} sanatçının "
              f"ekseninde başka sanatçı var", file=sys.stderr)

    # Ağ stratejileri eksen NUMARASI istiyor (eksen_haritasi sanatçı kümesi
    # veriyor). Keskin atama; gizlemeden ÖNCE hesaplanıyor.
    eksen_no: dict[str, int] = {}
    ag_frekans: dict[str, int] = {}
    calisma_id = ""
    if ag:
        satir = conn.execute(
            "SELECT calisma_id FROM clusters ORDER BY calisma_id DESC LIMIT 1"
        ).fetchone()
        calisma_id = calisma or (satir[0] if satir else "")
        en_iyi: dict[str, tuple[int, float]] = {}
        for album_id, kume_id, uyelik in conn.execute(
            "SELECT album_id, kume_id, uyelik FROM memberships WHERE calisma_id=?",
            (calisma_id,),
        ):
            if album_id not in en_iyi or uyelik > en_iyi[album_id][1]:
                en_iyi[album_id] = (kume_id, uyelik)
        for album_id, (kume_id, _) in en_iyi.items():
            ad = conn.execute("SELECT artist FROM albums WHERE album_id=?",
                              (album_id,)).fetchone()
            if ad and ad[0]:
                eksen_no.setdefault(normalize_esleme(ad[0]), kume_id)
        # `bilincli_uzaklik`'ın popülerlik paydası TÜM kütüphaneden geliyor ve
        # tek sanatçı çıkarılınca kayda değer değişmiyor. 147 kez yeniden
        # hesaplamak yerine bir kez alınıyor; yaklaşıklık burada yazılı.
        from python.discover.adaylar import eksen_frekansi, listenbrainz, musicbrainz
        try:
            ag_frekans = eksen_frekansi(
                conn, musicbrainz(cevrimdisi=True),
                listenbrainz(cevrimdisi=True), calisma_id)
        except Exception:
            ag_frekans = {}

    # BELİRSİZLİK ÖLÇÜMÜ. Gizleme sınaması "sahip olduğun sanatçıyı bulabildi
    # mi" diye soruyor; sahip olduğun sanatçılar popülere kayıyor, dolayısıyla
    # sınamayı iyileştirmek POPÜLERLİĞE de itebiliyor. Ölçüldü ve oldu: kanıt
    # büzülmesi recall@10'u altı katına çıkarırken önerilerin medyan çalma
    # listesi görünürlüğünü 8-9'a taşıdı (kütüphanenin medyanı 6). Kullanıcının
    # ölçütü "hiç duymadığım sanatçı" olduğu için bu bir bedel; tek sayıya
    # bakmak yanıltır, ikisi yan yana raporlanıyor.
    gorunurluk = {
        r[0]: r[1] for r in conn.execute(
            "SELECT sanatci_anahtar, COUNT(DISTINCT liste_id) FROM liste_parca "
            "GROUP BY 1")
    }

    print("PMI tablosu hesaplanıyor…", file=sys.stderr)
    tablo = pmi_tablosu(conn, sahip_tam, olcut=olcut, buzulme=buzulme,
                        agirlik=liste_agirlik)

    print("CLAP gömüleri okunuyor…", file=sys.stderr)
    kutup_gomu, havuz_gomu = gomu_haritalari(conn)
    ses = SesErisimi(kutup_gomu, havuz_gomu, getattr(gomu_haritalari, "parcalar", None))

    # Sızıntı düzeltmesi (bkz. `sizinti_listeleri`). `sizinti=False` eski
    # protokol: eski sayıları yeniden üretmek ve farkı göstermek için.
    haric_harita = sizinti_listeleri(conn) if sizinti else {}
    parca_liste: dict[int, set[int]] = defaultdict(set)
    sanatci_liste: dict[str, set[int]] = defaultdict(set)
    if haric_harita:
        for pid, lid, anahtar in conn.execute(
                "SELECT parca_id, liste_id, sanatci_anahtar FROM liste_parca"):
            sanatci_liste[anahtar].add(int(lid))
            if pid is not None:
                parca_liste[int(pid)].add(int(lid))
        print(f"sızıntı düzeltmesi: {sum(len(v) for v in haric_harita.values())} liste "
              f"yalnız gizlenenin adıyla bulunmuş, o katmanda çıkarılıyor", file=sys.stderr)
    motor_kayit: list[dict] = []
    from python.etiket_clap import PARCA_ASGARI_LISTE
    print(f"  kütüphane {ses.L.shape[0]} gömü · havuz {ses.P.shape[0]} gömü "
          f"({len(ses.havuz_anahtar)} sanatçı)", file=sys.stderr)

    # Tavan: gizlenen sanatçı ilgili havuzda var mı?
    pmi_havuz = {b for a in tablo for b in tablo[a]}
    ses_havuz = set(ses.havuz_anahtar)

    sonuc: dict[str, dict] = {
        "liste_birlikteligi": {"siralar": [], "erisilebilir": 0, "ayrinti": [],
                               "havuz": len(pmi_havuz)},
        "ses_benzerligi": {"siralar": [], "erisilebilir": 0, "ayrinti": [],
                           "havuz": len(ses_havuz)},
        # Melezin havuzu ikisinin BİRLEŞİMİ; tavanı da öyle. Kesişim alınsaydı
        # yalnız bir sinyalde görünen aday kaybedilirdi.
        "melez": {"siralar": [], "erisilebilir": 0, "ayrinti": [],
                  "havuz": len(pmi_havuz | ses_havuz)},
    }
    # Dış komşuluk yolları (Deezer benzerleri, ListenBrainz, MusicBrainz
    # kadrosu; `komsuluk.py`): tohumların komşu listeleri, gizlenen tohum değil.
    from python.discover.komsuluk import tohumlardan_sira
    dis_komsular = dis_komsular or {}
    for yol in dis_komsular:
        sonuc[yol] = {"siralar": [], "erisilebilir": 0, "ayrinti": [], "havuz": 0,
                      "_boylar": []}
    if ag:
        for st in AG_STRATEJILERI:
            # Bu üçünün havuzu SABİT DEĞİL: her gizlemede kendi ürettikleri
            # kısa listeyi sıralıyorlar. Havuz, ölçüm boyunca gördükleri
            # tekil sanatçıların birleşimi olarak toplanıyor.
            sonuc[st] = {"siralar": [], "erisilebilir": 0, "ayrinti": [],
                         "havuz": 0, "gorulen": set(), "olculemedi": 0}

    for sira, gizli in enumerate(anahtarlar, 1):
        kalan_sahip = sahip_tam - {gizli}
        # Eksen kapsamında sorgu, gizlenenin ekseninin geri kalanı. Eksende
        # başka sanatçı yoksa (tek üyeli eksen) tüm kütüphaneye düşülüyor —
        # sorgu boş bırakılırsa o sanatçı hiç ölçülemez, bu da tavanı
        # sessizce düşürürdü.
        tohumlar = (harita.get(gizli) or kalan_sahip) & kalan_sahip
        sorgu = tohumlar if kapsam == "eksen" else None

        def _belirsizlik(liste: list[str]) -> float:
            """İlk 10 adayın medyan çalma listesi görünürlüğü. Küçük = belirsiz."""
            ilk = [gorunurluk.get(x, 0) for x in liste[:10]]
            return float(np.median(ilk)) if ilk else float("nan")

        haric = haric_harita.get(gizli, set())
        if haric:
            tablo_k = pmi_tablosu(conn, sahip_tam, olcut=olcut, buzulme=buzulme,
                                  agirlik=liste_agirlik, haric_listeler=haric)
            pmi_havuz_k = {b for a in tablo_k for b in tablo_k[a]}
            # Havuz uygunluğu da katmanda: sanatçı ancak ≥ PARCA_ASGARI_LISTE
            # listede geçiyorsa gömülüyor; sızan listeler çıkınca altına
            # düşen sanatçının bütün parçaları bu katmanda havuzda yok.
            yetersiz = {a for a in set(ses.havuz_sahip)
                        if sanatci_liste.get(a, set()) & haric
                        and len(sanatci_liste[a] - haric) < PARCA_ASGARI_LISTE}
            dusen = np.array([a in yetersiz or (bool(parca_liste.get(pid))
                                                and parca_liste[pid] <= haric)
                              for a, pid in zip(ses.havuz_sahip, ses.havuz_parca)], dtype=bool)
            ses_var = any(a == gizli and not d for a, d in zip(ses.havuz_sahip, dusen))
        else:
            tablo_k, pmi_havuz_k, dusen = tablo, pmi_havuz, None
            ses_var = gizli in ses_havuz

        pmi_liste = pmi_sirala(tablo_k, tohumlar, kalan_sahip)
        s_pmi = sira_bul(pmi_liste, gizli)
        sonuc["liste_birlikteligi"]["siralar"].append(s_pmi)
        sonuc["liste_birlikteligi"]["erisilebilir"] += gizli in pmi_havuz_k
        sonuc["liste_birlikteligi"]["ayrinti"].append((kut[gizli], s_pmi))

        ses_liste = ses.sirala(gizli, kalan_sahip, sorgu, haric_satir=dusen)
        sonuc["liste_birlikteligi"].setdefault("belirsizlik", []).append(
            _belirsizlik(pmi_liste))
        sonuc["ses_benzerligi"].setdefault("belirsizlik", []).append(
            _belirsizlik(ses_liste))

        s_ses = sira_bul(ses_liste, gizli)
        sonuc["ses_benzerligi"]["siralar"].append(s_ses)
        sonuc["ses_benzerligi"]["erisilebilir"] += ses_var
        sonuc["ses_benzerligi"]["ayrinti"].append((kut[gizli], s_ses))

        melez_liste = melez_sirala(
            [pmi_liste, ses_liste], agirliklar=list(melez_agirlik))
        sonuc["melez"].setdefault("belirsizlik", []).append(
            _belirsizlik(melez_liste))
        s_melez = sira_bul(melez_liste, gizli)
        sonuc["melez"]["siralar"].append(s_melez)
        sonuc["melez"]["erisilebilir"] += (gizli in pmi_havuz_k) or ses_var
        dis_liste = {}
        for yol, komsu in dis_komsular.items():
            dis_liste[yol] = tohumlardan_sira({t: komsu.get(t, []) for t in tohumlar},
                                              haric=kalan_sahip)
            s_dis = sira_bul(dis_liste[yol], gizli)
            veri = sonuc[yol]
            veri["siralar"].append(s_dis)
            veri["erisilebilir"] += s_dis is not None
            veri["ayrinti"].append((kut[gizli], s_dis))
            veri["_boylar"].append(len(dis_liste[yol]))
            veri.setdefault("belirsizlik", []).append(_belirsizlik(dis_liste[yol]))
        if motor:
            motor_kayit.append({"gizli": gizli, "tohumlar": tohumlar,
                                "sahip": kalan_sahip, "haric": haric,
                                "liste": pmi_liste, "ses": ses_liste, "dis": dis_liste})
        sonuc["melez"]["ayrinti"].append((kut[gizli], s_melez))

        if ag:
            kopya = gizli_kopya(conn, gizli)
            try:
                for st in AG_STRATEJILERI:
                    liste = ag_siralamasi(kopya, calisma_id, eksen_no.get(gizli, 0),
                                          st, frekans=ag_frekans, genis=ag_genis)
                    veri = sonuc[st]
                    if liste is None:
                        veri["olculemedi"] += 1
                        veri["siralar"].append(None)
                        veri["ayrinti"].append((kut[gizli], None))
                        continue
                    veri["gorulen"].update(liste)
                    veri["erisilebilir"] += gizli in liste
                    s_ag = sira_bul(liste, gizli)
                    veri["siralar"].append(s_ag)
                    veri["ayrinti"].append((kut[gizli], s_ag))
            finally:
                kopya.close()

        if ayrinti:
            print(f"  {sira:>3}/{len(anahtarlar)} {kut[gizli][:30]:<32}"
                  f" PMI {str(s_pmi):>6} · ses {str(s_ses):>6}"
                  f" · melez {str(s_melez):>6}", file=sys.stderr)
        elif sira % 25 == 0:
            print(f"  {sira}/{len(anahtarlar)}", file=sys.stderr)

    if motor and motor_kayit:
        motor_olc(conn, sonuc, motor_kayit, kut, gorunurluk)

    for ad, veri in sonuc.items():
        if ad.startswith("_"):
            continue
        if "_boylar" in veri:
            veri["havuz"] = int(np.median(veri.pop("_boylar"))) if veri["siralar"] else 0
        if "gorulen" in veri:
            veri["havuz"] = len(veri["gorulen"])
        veri["ozet"] = ozet(veri["siralar"], veri["erisilebilir"],
                            havuz_boyu=veri["havuz"])
        veri["ozet"]["olculemedi"] = veri.get("olculemedi", 0)
        bel = [x for x in veri.get("belirsizlik", []) if x == x]
        veri["ozet"]["gorunurluk"] = float(np.median(bel)) if bel else float("nan")
    return sonuc


# --------------------------------------------------------------------------- #
# Motor — RP3β, EASE ve öğrenilmiş füzyon, İÇ İÇE ayarlanarak
# --------------------------------------------------------------------------- #

#: Izgaralar. α liste boyutu cezası, β aday popülerlik cezası, bağlam ağırlığı
#: dil/ruh hâli listelerinin payı (1 = kapalı), λ EASE düzenlileştirmesi.
#: α 2'ye kadar: Cooper 2014'ün en iyisi 1,9; Dacrema'nın aralığı 0–2 (tam
#: metinle doğrulandı, `docs/arastirma/7-*`). Dacrema kodu varsayılanı α=1, β=0,6.
RP3_IZGARASI = [(a, b, w) for a in (0.0, 0.5, 1.0, 1.5, 2.0)
                for b in (0.0, 0.25, 0.5, 0.75, 1.0) for w in (1.0, 0.5, 0.2)]
EASE_IZGARASI = [(lam, w) for lam in (1.0, 10.0, 100.0, 1000.0) for w in (1.0, 0.5)]
DIS_KAT = 10


def _rr_listesi(siralar: list[int | None]) -> list[float]:
    return [1.0 / s if s else 0.0 for s in siralar]


def motor_olc(conn: sqlite3.Connection, sonuc: dict, kayitlar: list[dict],
              kut: dict[str, str], gorunurluk: dict[str, int] | None = None) -> None:
    """RP3β ve EASE ızgarası + koşullu logit füzyonu, iç içe CV ile.

    Dış katta (10 kat, sorgu = gizlenen sanatçı) RP3β/EASE ızgara noktası,
    logit λ'sı ve füzyon ağırlıkları YALNIZ eğitim sorgularında seçilir,
    dışarıdaki sorgular sıralanır (Varma & Simon 2006; Dacrema 2019).
    İÇ İÇE OLMAYAN kısım (rapora yazılır): öncülün yönü (liste 1 : ses 2) ve
    liste yolunun ayarları (npmi, büzülme 1) önceki çalışmalarda TÜM
    sorgularda seçilmişti. Üretim ayarı (`_motor_ayar`) TÜM sorgularda seçilir.

    Sıra, tavan ve yüzdelik KESİLMEMİŞ skor desteğinden ve sıranın geldiği
    katın ızgarasıyla (`motor.tam_sira`); öznitelikler ilk 1000'den.
    """
    from python import motor as M

    print("Motor: grafik ve ızgara…", file=sys.stderr)
    G = M.grafik_kur(conn, baglam_agirligi=1.0)
    n_q = len(kayitlar)
    rp3_s: list[list[list[str]]] = []      # [sorgu][ızgara] → ilk 1000 (öznitelik)
    ease_s: list[list[list[str]]] = []
    rp3_t: list[list[tuple]] = []          # [sorgu][ızgara] → (tam sıra, destek)
    ease_t: list[list[tuple]] = []
    ozellik: list[tuple[dict, dict]] = []
    for q, k in enumerate(kayitlar):
        satir = G.satir_maskesi(k["haric"])
        tohum = {a: 1.0 for a in k["tohumlar"]}
        sahip_idx = np.array([G.sira[a] for a in k["sahip"] if a in G.sira], dtype=int)
        satirlar, tamlar = [], []
        ortak = None
        for alfa, beta, bw in RP3_IZGARASI:
            G.w = np.where(G.baglam, bw, 1.0).astype("float32")
            skor, _, ortak_k = M.rp3(G, tohum, alfa=alfa, beta=beta, satir=satir)
            ortak = ortak_k if ortak is None else ortak
            satirlar.append(M.sirala(skor, G, k["sahip"]))
            tamlar.append(M.tam_sira(skor, G, sahip_idx, k["gizli"]))
        rp3_s.append(satirlar)
        rp3_t.append(tamlar)
        satirlar, tamlar = [], []
        for lam, bw in EASE_IZGARASI:
            G.w = np.where(G.baglam, bw, 1.0).astype("float32")
            skor = M.ease(G, tohum, lam=lam, satir=satir)
            satirlar.append(M.sirala(skor, G, k["sahip"]))
            tamlar.append(M.tam_sira(skor, G, sahip_idx, k["gizli"]))
        ease_s.append(satirlar)
        ease_t.append(tamlar)
        ozellik.append(M.ortak_ozeti(G, ortak))
        if (q + 1) % 25 == 0:
            print(f"  motor {q + 1}/{n_q}", file=sys.stderr)

    hedef = [k["gizli"] for k in kayitlar]

    def mrr(tamlar, indeksler, g):
        return float(np.mean([1.0 / tamlar[q][g][0] if tamlar[q][g][0] else 0.0
                              for q in indeksler])) if indeksler else 0.0

    def en_iyi(tamlar, indeksler, n_izgara):
        return max(range(n_izgara), key=lambda g: (mrr(tamlar, indeksler, g), -g))

    def kayit(q, g_rp3, g_ease):
        toplam, pay = ozellik[q]
        havuz, F = M.oznitelikler(
            {"rp3": rp3_s[q][g_rp3], "ease": ease_s[q][g_ease],
             "liste": kayitlar[q]["liste"], "ses": kayitlar[q]["ses"],
             **kayitlar[q].get("dis", {})},
            ortak=toplam, tohum_payi=pay)
        return {"havuz": havuz, "F": F, "hedef": hedef[q]}

    rng = np.random.default_rng(0)
    katman = rng.permutation(n_q) % DIS_KAT
    s_rp3: list[int | None] = [None] * n_q
    s_ease: list[int | None] = [None] * n_q
    s_motor: list[int | None] = [None] * n_q
    destek = {"rp3": [0] * n_q, "ease": [0] * n_q, "motor": [0] * n_q}
    tavan = {"rp3": [False] * n_q, "ease": [False] * n_q, "motor": [False] * n_q}
    gorunur = {"rp3": [], "ease": [], "motor": []}
    gorunurluk = gorunurluk or {}

    def ilk10(liste):
        return float(np.median([gorunurluk.get(x, 0) for x in liste[:10]])) if liste else np.nan

    katlar = []
    for kat in range(DIS_KAT):
        egit = [q for q in range(n_q) if katman[q] != kat]
        sina = [q for q in range(n_q) if katman[q] == kat]
        g_r = en_iyi(rp3_t, egit, len(RP3_IZGARASI))
        g_e = en_iyi(ease_t, egit, len(EASE_IZGARASI))
        ornek = [o for o in (M._ornek(kayit(q, g_r, g_e)) for q in egit) if o is not None]
        lam = M.lambda_sec(ornek, tohum=kat)
        theta = M.logit_egit(ornek, lam=lam)
        katlar.append({"rp3": RP3_IZGARASI[g_r], "ease": EASE_IZGARASI[g_e],
                       "lam": lam, "theta": theta.round(3).tolist()})
        for q in sina:
            s_rp3[q], destek["rp3"][q] = rp3_t[q][g_r]
            s_ease[q], destek["ease"][q] = ease_t[q][g_e]
            r = kayit(q, g_r, g_e)
            s_motor[q] = M._hedef_sirasi(r, theta)
            destek["motor"][q] = len(r["havuz"])
            tavan["rp3"][q] = s_rp3[q] is not None
            tavan["ease"][q] = s_ease[q] is not None
            tavan["motor"][q] = hedef[q] in r["havuz"]
            sira = np.argsort(-M.puanla(r["F"], theta), kind="stable")[:10] if r["havuz"] else []
            gorunur["rp3"].append(ilk10(rp3_s[q][g_r]))
            gorunur["ease"].append(ilk10(ease_s[q][g_e]))
            gorunur["motor"].append(ilk10([r["havuz"][i] for i in sira]))

    def yol(ad, siralar):
        # Tavan ve havuz, sıranın üretildiği katın ızgarasından (aynı katman).
        return {"siralar": siralar, "erisilebilir": sum(tavan[ad]),
                "ayrinti": [(kut[h], s) for h, s in zip(hedef, siralar)],
                "havuz": int(np.median(destek[ad])) if n_q else 0}

    g_r_tum = en_iyi(rp3_t, range(n_q), len(RP3_IZGARASI))
    g_e_tum = en_iyi(ease_t, range(n_q), len(EASE_IZGARASI))
    tum_kayit = [kayit(q, g_r_tum, g_e_tum) for q in range(n_q)]
    sonuc["rp3"] = yol("rp3", s_rp3)
    sonuc["ease"] = yol("ease", s_ease)
    sonuc["motor"] = yol("motor", s_motor)
    for ad, deger in gorunur.items():
        sonuc[ad]["belirsizlik"] = deger

    ornek = [o for o in map(M._ornek, tum_kayit) if o is not None]
    lam = M.lambda_sec(ornek)
    theta = M.logit_egit(ornek, lam=lam)
    alfa, beta, bw = RP3_IZGARASI[g_r_tum]
    lam_e, bw_e = EASE_IZGARASI[g_e_tum]
    dis_adlari = [ad for ad in sonuc if ad in M.YOL_ADLARI[4:]]
    rr = {ad: _rr_listesi(sonuc[ad]["siralar"])
          for ad in ("motor", "rp3", "ease", "melez", "liste_birlikteligi", "ses_benzerligi",
                     *dis_adlari)}
    ciftler_ = [("motor", "melez"), ("motor", "rp3"), ("rp3", "liste_birlikteligi"),
                ("ease", "liste_birlikteligi"), ("motor", "ses_benzerligi")]
    ciftler_ += [(ad, "liste_birlikteligi") for ad in dis_adlari]
    kiyas = {f"{a} − {b}": M.eslesmis_kiyas(rr[a], rr[b]) for a, b in ciftler_}
    sonuc["_motor_ayar"] = {
        "alfa": alfa, "beta": beta, "lam_ease": lam_e,
        # RP3β ve EASE ayrı bağlam ağırlığı seçebilir; üretim ikisini de
        # kendi değeriyle koşar (`motor.eksen_sirasi`).
        "baglam_agirligi": bw, "baglam_agirligi_ease": bw_e,
        "theta": theta.round(4).tolist(), "lam_logit": lam,
        "katlar": katlar, "kiyas": kiyas, "sorgu": n_q,
    }


def olcum_ozeti(sonuc: dict, *, cift: dict | None = None, kaynak: str = "") -> dict:
    """Ölçümler sayfasının ve raporun okuduğu, JSON'a yazılabilir özet.

    Bütün erişim yollarının LOAO özeti, eşli kıyaslar, motorun ayarı ve
    (varsa) insan çifti sınaması. Seçim kuralı (önceden yazılı): motor
    ölçüldüyse ÜRETİMDEKİ yapı odur — λ → ∞ iken melezle aynı olduğundan
    melezden kötü seçilemez; sayılar yine de yan yana gösterilir.
    """
    from datetime import date as _tarih

    alanlar = ("gizlenen", "erisilebilir", "bulunan", "recall@1", "recall@5", "recall@10",
               "recall@50", "mrr", "medyan_sira", "medyan_yuzdelik", "havuz_boyu", "gorunurluk")
    loao = {ad: {k: v["ozet"].get(k) for k in alanlar}
            for ad, v in sonuc.items() if not ad.startswith("_") and "ozet" in v}
    for ad, v in sonuc.items():
        if ad in loao:
            rr = _rr_listesi(v["siralar"])
            loao[ad]["ndcg"] = float(np.mean([1 / np.log2(1 + s) if s else 0.0
                                              for s in v["siralar"]])) if rr else 0.0
    ayar = sonuc.get("_motor_ayar") or {}
    ozet = {"tarih": _tarih.today().isoformat(), "kaynak": kaynak,
            "protokol": "sizintisiz", "loao": loao,
            "kiyas": ayar.get("kiyas", {}),
            "motor": {k: ayar.get(k) for k in ("alfa", "beta", "lam_ease", "baglam_agirligi",
                                               "baglam_agirligi_ease", "theta", "lam_logit",
                                               "sorgu")} if ayar else None,
            "secilen": "motor" if ayar else "melez"}
    if ayar:
        from python.motor import OZNITELIKLER
        ozet["motor"]["oznitelikler"] = list(OZNITELIKLER)
    if cift:
        ozet["ciftler"] = {"ozet": {y: {k: v for k, v in o.items() if k != "rr"}
                                    for y, o in cift["ozet"].items()},
                           "kiyas": cift["kiyas"], "sayim": cift["sayim"]}
    return _json_uyumlu(ozet)


def _json_uyumlu(x):
    """NaN → None, numpy → Python (JSON'a yazılabilsin)."""
    if isinstance(x, dict):
        return {k: _json_uyumlu(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json_uyumlu(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if x != x else float(x)
    if isinstance(x, np.integer):
        return int(x)
    return x


def motor_raporu(sonuc: dict) -> str:
    ayar = sonuc.get("_motor_ayar")
    if not ayar:
        return ""
    from python.motor import OZNITELIKLER
    satirlar = ["Motor — iç içe CV: RP3β/EASE ızgarası, λ ve θ dış katın eğitim sorgularında",
                "seçildi. İç içe OLMAYAN: öncülün yönü (liste 1 : ses 2) ve liste yolunun",
                "ayarları (npmi, büzülme 1) önceki çalışmalarda tüm sorgularda seçilmişti.",
                "=" * 74,
                f"üretim ayarı: RP3β α={ayar['alfa']} β={ayar['beta']} "
                f"bağlam={ayar['baglam_agirligi']} · EASE λ={ayar['lam_ease']} · "
                f"logit λ={ayar['lam_logit']}",
                "füzyon ağırlıkları: " + ", ".join(
                    f"{a}={t:+.2f}" for a, t in zip(OZNITELIKLER, ayar["theta"])),
                "", f"{'eşli kıyas (MRR farkı)':<34}{'fark':>8}{'%95 aralık':>20}{'p':>8}"]
    for ad, k in ayar["kiyas"].items():
        aralik = f"[{k['alt']:+.3f}, {k['ust']:+.3f}]"
        satirlar.append(f"{ad:<34}{k['fark']:>+8.3f}{aralik:>20}{k['p']:>8.3f}")
    secimler = Counter(str(k["rp3"]) for k in ayar["katlar"])
    satirlar += ["", "kat başına RP3β seçimi (α, β, bağlam): " + ", ".join(
        f"{a} ×{n}" for a, n in secimler.most_common()),
        "p: işaret çevirmeli permütasyon (20.000), aralık: eşli bootstrap.", ""]
    return "\n".join(satirlar)


# --------------------------------------------------------------------------- #
# İnsan çiftleri — forumlardaki «X'i seven Y'yi dener» (2026-10-20)
# --------------------------------------------------------------------------- #

def ciftleri_oku(yol: Path) -> list[dict]:
    """`docs/arastirma/insan-ciftleri.csv`: tohumlar ('A | B'), oneri, onay,
    op, negatif, dogrulama, bolum, kaynak. Yalnız doğrulanmış satırlar sayılır."""
    import csv

    with open(yol, newline="", encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))
    sonuc = []
    for r in satirlar:
        if r.get("dogrulama") not in ("dogrulandi", "onay_daha_az", "op_farkli"):
            continue
        tohum = [t.strip() for t in (r.get("tohumlar") or "").split("|") if t.strip()]
        if tohum and r.get("oneri"):
            sonuc.append({**r, "tohumlar": tohum,
                          "negatif": r.get("negatif") in ("1", "True", "true")})
    return sonuc


def cift_sinamasi(conn: sqlite3.Connection, ciftler: list[dict], *,
                  dis_komsular: dict[str, dict[str, list[dict]]] | None = None,
                  kutuphane_haric: bool = True, birlesim: bool = True) -> dict:
    """Dışarıdan gelen insan önerileriyle ikinci ölçüt — gizleme sınamasının
    vekil sorununu (sahip olunan = popüler) taşımıyor: öneriler çoğunlukla
    kütüphanede OLMAYAN, niş sanatçılar.

    Sorgu çiftin tohumları (kütüphaneden bağımsız: YÖNTEMİN benzerlik bilgisini
    ölçer). Tohumlar aday olamaz. `kutuphane_haric`: sahip olunan öneri atlanır
    («zaten biliyorum») ve sahip olunanlar aday olamaz; bulut kıyasında
    (kütüphane = tohumlar) kapalı.

    Yollar: çalma listesi grafiği (npmi, RP3β, EASE) + `dis_komsular`
    ({yol: {tohum anahtarı: komşu listesi}} — Deezer benzerleri, ListenBrainz,
    MusicBrainz kadrosu; `komsuluk.py`). Birleşimler: «rrf_tum» (eşit ağırlıklı
    sıra kaynaşması) ve «birlesim» (koşullu logit, her TOHUM GRUBU dışarıda
    bırakılarak öğrenilir — iç içe; λ iç katlarda NDCG ile). Kullanıcının
    öğrenilmiş motoru varsa «motor» da.

    Sızıntı: öneri sanatçısının ADIYLA bulunmuş listeler o çiftte çıkarılır
    (`sizinti_listeleri`; LOAO ile aynı kural).
    """
    from python import motor as M
    from python.discover.komsuluk import tohumlardan_sira

    ayar = M.ayar_oku(conn)
    G = M.grafik_kur(conn, baglam_agirligi=ayar["baglam_agirligi"])
    w_ease = np.where(G.baglam, ayar.get("baglam_agirligi_ease", ayar["baglam_agirligi"]),
                      1.0).astype("float32")
    sahip = set(kutuphane(conn)) if kutuphane_haric else set()
    sizinti = sizinti_listeleri(conn)
    dis_komsular = dis_komsular or {}
    taban = ["liste_birlikteligi", "rp3", "ease", *dis_komsular]
    yollar = taban + (["rrf_tum"] if len(taban) > 1 else []) \
        + (["birlesim"] if birlesim and len(taban) > 1 else []) \
        + (["motor"] if ayar["ogrenildi"] else [])
    onbellek: dict[tuple, dict[str, list[str]]] = {}

    def siralar_kur(tohum_t: tuple, haric_listeler: frozenset) -> dict[str, list[str]]:
        anahtar = (tohum_t, haric_listeler)
        if anahtar in onbellek:
            return onbellek[anahtar]
        tohum = {t: 1.0 for t in tohum_t if t in G.sira}
        haric = sahip | set(tohum_t)
        satir = G.satir_maskesi(haric_listeler)
        s = {}
        if tohum:
            s_rp3, _, ortak = M.rp3(G, tohum, alfa=ayar["alfa"], beta=ayar["beta"], satir=satir)
            tablo = pmi_tablosu(conn, set(tohum), olcut="npmi", buzulme=1.0,
                                haric_listeler=haric_listeler)
            s["liste_birlikteligi"] = pmi_sirala(tablo, set(tohum), haric)
            s["rp3"] = M.sirala(s_rp3, G, haric, derinlik=len(G.anahtar))
            s["ease"] = M.sirala(M.ease(G, tohum, lam=ayar["lam_ease"], w=w_ease, satir=satir),
                                 G, haric, derinlik=len(G.anahtar))
            if ayar["ogrenildi"]:
                toplam, pay = M.ortak_ozeti(G, ortak)
                havuz, F = M.oznitelikler({"rp3": s["rp3"], "ease": s["ease"],
                                           "liste": s["liste_birlikteligi"]},
                                          ortak=toplam, tohum_payi=pay)
                s["motor"] = [havuz[i] for i in np.argsort(-M.puanla(F, np.asarray(
                    ayar["theta"])), kind="stable")]
        else:
            s.update({"liste_birlikteligi": [], "rp3": [], "ease": []})
        for yol, komsu in dis_komsular.items():
            s[yol] = tohumlardan_sira({t: komsu.get(t, []) for t in tohum_t}, haric=haric)
        if len(taban) > 1:
            s["rrf_tum"] = melez_sirala([s[y] for y in taban])
        onbellek[anahtar] = s
        return s

    gruplar: dict[tuple, list[dict]] = defaultdict(list)
    for c in ciftler:
        gruplar[tuple(sorted(normalize_esleme(t) for t in c["tohumlar"]))].append(c)
    kayit: list[dict] = []          # çift başına: grup, hedef, olumsuz mu, yol → sıra
    sayim = Counter()
    for tohum_t, grup in gruplar.items():
        for c in grup:
            hedef = normalize_esleme(c["oneri"])
            if hedef in sahip:
                sayim["zaten_sahip"] += 1
                continue
            if hedef not in G.sira:
                sayim["oneri_grafikte_yok"] += 1
            sayim["olculen"] += 1
            s = siralar_kur(tohum_t, frozenset(sizinti.get(hedef, ())))
            kayit.append({"grup": tohum_t, "hedef": hedef, "negatif": c["negatif"],
                          "s": s, "sira": {y: sira_bul(s.get(y, []), hedef) for y in s}})

    if "birlesim" in yollar:
        _birlesim_ogren(kayit, taban, sayim)

    ozet = {y: _cift_ozeti(kayit, y) for y in yollar}
    kiyas = {f"{a} − liste_birlikteligi": M.eslesmis_kiyas(
        ozet[a]["rr"], ozet["liste_birlikteligi"]["rr"]) for a in yollar
        if a != "liste_birlikteligi"}
    return {"ozet": ozet, "kiyas": kiyas, "sayim": dict(sayim),
            "ogrenildi": ayar["ogrenildi"], "yollar": yollar,
            "ciftler": [{"grup": " | ".join(k["grup"]), "hedef": k["hedef"],
                         "negatif": k["negatif"], "sira": k["sira"]} for k in kayit]}


def _birlesim_ogren(kayit: list[dict], taban: list[str], sayim: Counter) -> None:
    """Koşullu logit, tohum grubu dışarıda bırakılarak (iç içe): her grubun
    çiftleri, ağırlıkları O GRUP GÖRÜLMEDEN öğrenilmiş birleşimle sıralanır.
    Öznitelik: her yolun K/(K+sıra) puanı (ilk 1000). Öncül: eşit ağırlık."""
    from python import motor as M

    mu = np.ones(len(taban))

    def havuz_F(s: dict) -> tuple[list[str], np.ndarray]:
        rr = {y: {a: M.RR_K / (M.RR_K + r) for r, a in enumerate(s[y][:M.YOL_DERINLIGI], 1)}
              for y in taban}
        havuz = list(dict.fromkeys(a for y in taban for a in s[y][:M.YOL_DERINLIGI]))
        F = np.array([[rr[y].get(a, 0.0) for y in taban] for a in havuz]) \
            if havuz else np.zeros((0, len(taban)))
        return havuz, F

    gruplar = sorted({k["grup"] for k in kayit})
    ornek_grup = []
    for k in kayit:
        k["_havuz"], k["_F"] = havuz_F(k["s"])
        if not k["negatif"] and k["hedef"] in k["_havuz"]:
            ornek_grup.append(((k["_F"], k["_havuz"].index(k["hedef"])), k["grup"]))
    agirliklar = []
    for g in gruplar:
        egit = [(o, gg) for o, gg in ornek_grup if gg != g]
        if len(egit) < 10:
            theta = mu
        else:
            ic = sorted({gg for _, gg in egit})
            katman = np.array([ic.index(gg) % 5 for _, gg in egit])
            ornek = [o for o, _ in egit]
            theta = M.logit_egit(ornek, lam=M.lambda_sec(ornek, mu=mu, katman=katman), mu=mu)
        agirliklar.append(theta)
        for k in kayit:
            if k["grup"] != g:
                continue
            if not k["_havuz"]:
                k["sira"]["birlesim"] = None
                continue
            sira = [k["_havuz"][i] for i in np.argsort(-(k["_F"] @ theta), kind="stable")]
            k["sira"]["birlesim"] = sira_bul(sira, k["hedef"])
    sayim["birlesim_agirlik"] = dict(zip(taban, np.mean(agirliklar, axis=0).round(2).tolist())) \
        if agirliklar else {}


def _cift_ozeti(kayit: list[dict], yol: str) -> dict:
    poz = [k["sira"].get(yol) for k in kayit if not k["negatif"]]
    neg = [k["sira"].get(yol) for k in kayit if k["negatif"]]
    rr = [1.0 / r if r else 0.0 for r in poz]
    return {
        "n": len(poz), "tavan": sum(1 for r in poz if r),
        "@10": sum(1 for r in poz if r and r <= 10) / len(poz) if poz else 0.0,
        "@50": sum(1 for r in poz if r and r <= 50) / len(poz) if poz else 0.0,
        "mrr": float(np.mean(rr)) if rr else 0.0,
        # NDCG (tek ilgili öğe): 1/log₂(1+sıra) — üst sıralar kadar orta sıraları
        # da sayar; λ seçimiyle aynı ölçüt.
        "ndcg": float(np.mean([1 / np.log2(1 + r) if r else 0.0 for r in poz])) if poz else 0.0,
        "medyan_sira": float(np.median([r for r in poz if r])) if any(poz) else float("nan"),
        "negatif_n": len(neg),
        # Olumsuz çiftlerin ilk 50'ye girme oranı — küçük iyi; havuz
        # boyundan bağımsız (erişilemeyen olumsuz ilk 50'de değildir).
        "negatif_@50": sum(1 for r in neg if r and r <= 50) / len(neg) if neg else 0.0,
        "rr": rr,
    }


def cift_raporu(s: dict) -> str:
    satirlar = ["", "İnsan çiftleri — forumda «X'i seven Y'yi dener» (doğrulanmış satırlar)",
                "=" * 82,
                f"{'yol':<22}{'n':>5}{'tavan':>7}{'@10':>7}{'@50':>7}{'MRR':>8}"
                f"{'NDCG':>8}{'medyan':>8}{'olumsuz @50':>13}"]
    for y, o in s["ozet"].items():
        medyan = f"{o['medyan_sira']:>8.0f}" if o["medyan_sira"] == o["medyan_sira"] else f"{'—':>8}"
        satirlar.append(f"{y:<22}{o['n']:>5}{o['tavan']:>7}{o['@10']:>7.2f}{o['@50']:>7.2f}"
                        f"{o['mrr']:>8.3f}{o['ndcg']:>8.3f}{medyan}{o['negatif_@50']:>13.2f}")
    satirlar += ["", f"{'eşli kıyas (MRR farkı)':<40}{'fark':>8}{'%95 aralık':>20}{'p':>8}"]
    for ad, k in s["kiyas"].items():
        aralik = f"[{k['alt']:+.3f}, {k['ust']:+.3f}]"
        satirlar.append(f"{ad:<40}{k['fark']:>+8.3f}{aralik:>20}{k['p']:>8.3f}")
    sayim = {k: v for k, v in s["sayim"].items() if k != "birlesim_agirlik"}
    satirlar += ["", "sayım: " + ", ".join(f"{k}={v}" for k, v in sorted(sayim.items()))]
    if s["sayim"].get("birlesim_agirlik"):
        satirlar.append("birleşim ağırlıkları (katların ortalaması): " + ", ".join(
            f"{y}={w:+.2f}" for y, w in s["sayim"]["birlesim_agirlik"].items()))
    satirlar += ["tavan: önerinin o yolun listesinde HİÇ bulunması. olumsuz @50: forumda",
                 "reddedilenlerin ilk 50'ye girme oranı (küçük iyi). NDCG: 1/log₂(1+sıra).",
                 "birlesim: her tohum grubu dışarıda bırakılarak öğrenilmiş (iç içe).", ""]
    return "\n".join(satirlar)


def rapor(sonuc: dict[str, dict]) -> str:
    satirlar = [
        "",
        "Leave-one-artist-out — sanatçının TÜM albümleri gizlenip motora soruldu",
        "=" * 74,
        f"{'erişim':<22}{'tavan':>7}{'havuz':>7}"
        + "".join(f"{'@' + str(k):>7}" for k in KESMELER)
        + f"{'MRR':>8}{'medyan':>8}{'yüzdelik':>10}{'görünür':>9}",
        "-" * 84,
    ]
    for ad, veri in sonuc.items():
        if ad.startswith("_"):
            continue
        o = veri["ozet"]
        medyan = o["medyan_sira"]
        yuzde = o["medyan_yuzdelik"]
        satirlar.append(
            f"{ad:<22}{o['erisilebilir']:>3}/{o['gizlenen']:<3}"
            f"{o['havuz_boyu']:>7}"
            + "".join(f"{o['recall@' + str(k)]:>7.2f}" for k in KESMELER)
            + f"{o['mrr']:>8.3f}"
            + (f"{medyan:>8.0f}" if medyan == medyan else f"{'—':>8}")
            + (f"{yuzde:>10.3f}" if yuzde == yuzde else f"{'—':>10}")
            + (f"{o['gorunurluk']:>9.0f}"
               if o.get("gorunurluk", float("nan")) == o.get("gorunurluk", float("nan"))
               else f"{'—':>9}")
            + (f"  *{o['olculemedi']}" if o.get("olculemedi") else "")
        )
    satirlar += [
        "-" * 84,
        "tavan    = gizlenen sanatçının ilgili havuzda BULUNABİLİR olduğu durum",
        "havuz    = sıralanan aday sanatçı sayısı",
        "@k       = ilk k'da yakalanan oran (payda: tüm gizlenenler)",
        "MRR      = ortalama karşılıklı sıra; 1.0 hepsi birinci demek",
        "* satırı: önbellekte veri olmadığı için ölçülemeyen gizleme sayısı",
        "görünür  = ilk 10 adayın medyan çalma listesi sayısı = POPÜLERLİK.",
        "           Kütüphanenin medyanı 6. Büyükse öneriler seninkinden",
        "           popüler demek — «hiç duymadığım sanatçı» hedefine ters.",
        "yüzdelik = medyan sıra / havuz. FARKLI HAVUZ BOYLARI ARASINDA YALNIZ",
        "           BU KIYASLANIR; rastgele erişim 0,500 verir.",
        "",
    ]
    return "\n".join(satirlar)


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--limit", type=int, help="ilk N sanatçı (deneme)")
    ayristirici.add_argument("--ayrinti", action="store_true",
                             help="sanatçı sanatçı sıra yaz")
    ayristirici.add_argument("--kapsam", choices=("eksen", "tum"),
                             default="eksen",
                             help="sorgu: gizlenenin ekseni mi, tüm kütüphane mi")
    ayristirici.add_argument("--ag-genis", action="store_true",
                             help="ağ stratejilerini GENİŞ ayarla ölç")
    ayristirici.add_argument("--ag", action="store_true",
                             help="ağ isteyen 3 stratejiyi de ölç (önbellekten)")
    ayristirici.add_argument("--melez-agirlik", default="1,1",
                             help="liste,ses ağırlığı (örn. 2,1)")
    ayristirici.add_argument("--calisma",
                             help="hangi kümeleme çalışmasına göre ölçülsün")
    ayristirici.add_argument("--buzulme", type=float, default=0.0,
                             help="kanıt gücü çarpanı n/(n+k); k=0 kapalı")
    ayristirici.add_argument("--liste-agirlik", choices=("esit", "log", "ters"),
                             default="esit",
                             help="liste başına ağırlık (büyük karışık listeleri kısar)")
    ayristirici.add_argument("--olcut", choices=("pmi", "npmi"), default="pmi",
                             help="birliktelik ölçütü")
    from python.etiket_clap import SES_KURALI
    ayristirici.add_argument("--ses-kural", choices=("cok_sesli", "en_yakin_eksen", "eksen"),
                             default=SES_KURALI,
                             help="ses erişiminde eksen kuralı (kıyas için)")
    ayristirici.add_argument("--motor", action="store_true",
                             help="RP3β, EASE ve öğrenilmiş füzyonu da ölç (iç içe CV)")
    ayristirici.add_argument("--eski-protokol", action="store_true",
                             help="sızıntı düzeltmesi KAPALI (eski sayıları üretmek için)")
    ayristirici.add_argument("--ciftler", type=Path,
                             help="insan çiftleri CSV'si (docs/arastirma/insan-ciftleri.csv); "
                                  "yalnız bu sınamayı koşar")
    ayristirici.add_argument("--ses-olcek", choices=("merkez", "mp"), default=None,
                             help="ses benzerliği ölçeği: merkezleme (varsayılan) ya da "
                                  "Mutual Proximity (kıyas için)")
    ayristirici.add_argument("--en-kotu", type=int, default=0,
                             help="hiç bulunamayan ilk N sanatçıyı listele")
    args = ayristirici.parse_args(argv)

    SesErisimi.kural = args.ses_kural
    if args.ses_olcek:
        SesErisimi.olcek = args.ses_olcek
    conn = baglan(args.db)
    # Bilinmeyen çalışma kimliği SESSİZCE boş eksen haritası veriyordu ve
    # sonuçlar rastgeleye yakın çıkıyordu (2026-09-28: yer tutucu kimlikle
    # koşuldu, «eksen kapsamı 0/147»). Ölçmeden önce dur.
    if args.calisma and not conn.execute(
            "SELECT 1 FROM memberships WHERE calisma_id = ? LIMIT 1", (args.calisma,)).fetchone():
        mevcut = [r[0] for r in conn.execute(
            "SELECT DISTINCT calisma_id FROM clusters ORDER BY calisma_id DESC LIMIT 5")]
        conn.close()
        print(f"HATA: '{args.calisma}' diye bir kümeleme çalışması yok. Son çalışmalar:",
              *mevcut, sep="\n  ")
        return 2
    if args.ciftler:
        try:
            print(cift_raporu(cift_sinamasi(conn, ciftleri_oku(args.ciftler))))
        finally:
            conn.close()
        return 0
    try:
        sonuc = calistir(conn, limit=args.limit, ayrinti=args.ayrinti,
                         kapsam=args.kapsam, olcut=args.olcut,
                         melez_agirlik=tuple(
                             float(x) for x in args.melez_agirlik.split(",")),
                         buzulme=args.buzulme, calisma=args.calisma,
                         liste_agirlik=args.liste_agirlik,
                         ag=args.ag or args.ag_genis, ag_genis=args.ag_genis,
                         sizinti=not args.eski_protokol, motor=args.motor)
        print(rapor(sonuc))
        if args.motor:
            print(motor_raporu(sonuc))
        if args.en_kotu:
            for ad, veri in sonuc.items():
                if ad.startswith("_"):
                    continue
                kayip = [s for s, k in veri["ayrinti"] if k is None]
                print(f"{ad}: bulunamayan {len(kayip)} — "
                      f"{', '.join(kayip[:args.en_kotu])}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
