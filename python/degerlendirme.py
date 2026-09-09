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
    buzulme: float = 0.0,
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
        listeler[liste_id].add(anahtar)

    toplam = len(listeler)
    if toplam < 5:
        return {}

    gorulme: Counter = Counter()
    for uyeler in listeler.values():
        gorulme.update(uyeler)

    birlikte: Counter = Counter()
    for uyeler in listeler.values():
        icerdeki = uyeler & tohumlar
        if not icerdeki:
            continue
        for a in icerdeki:
            for b in uyeler:
                if a != b:
                    birlikte[(a, b)] += 1

    tablo: dict[str, dict[str, float]] = defaultdict(dict)
    for (a, b), adet in birlikte.items():
        if adet < ASGARI_BIRLIKTE:
            continue
        p_ab = adet / toplam
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
    for dosya in PARCA_GOMU.glob("*.npy"):
        try:
            ad = parca_ad.get(int(dosya.stem))
        except ValueError:
            continue
        if ad:
            havuz[normalize_esleme(ad)].append(np.load(dosya))

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

    def __init__(self, kutup: dict[str, np.ndarray], havuz: dict[str, np.ndarray]):
        self.havuz_anahtar = sorted(havuz)
        self.havuz_sahip: list[str] = []
        havuz_satir = []
        for a in self.havuz_anahtar:
            for v in havuz[a]:
                havuz_satir.append(v)
                self.havuz_sahip.append(a)
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

    def sirala(
        self, gizlenen: str, sahip: set[str], sorgu: set[str] | None = None,
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

        skor: dict[str, float] = {}
        for deger, anahtar in zip(satir, self.havuz_sahip):
            if anahtar in sahip and anahtar != gizlenen:
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
    melez_agirlik: tuple[float, float] = (1.0, 1.0), ag: bool = False,
    ag_genis: bool = False,
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

    harita = eksen_haritasi(conn) if kapsam == "eksen" else {}
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
        calisma_id = satir[0] if satir else ""
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
    tablo = pmi_tablosu(conn, sahip_tam, olcut=olcut, buzulme=buzulme)

    print("CLAP gömüleri okunuyor…", file=sys.stderr)
    kutup_gomu, havuz_gomu = gomu_haritalari(conn)
    ses = SesErisimi(kutup_gomu, havuz_gomu)
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

        s_pmi = sira_bul(pmi_sirala(tablo, tohumlar, kalan_sahip), gizli)
        sonuc["liste_birlikteligi"]["siralar"].append(s_pmi)
        sonuc["liste_birlikteligi"]["erisilebilir"] += gizli in pmi_havuz
        sonuc["liste_birlikteligi"]["ayrinti"].append((kut[gizli], s_pmi))

        pmi_liste = pmi_sirala(tablo, tohumlar, kalan_sahip)
        ses_liste = ses.sirala(gizli, kalan_sahip, sorgu)
        sonuc["liste_birlikteligi"].setdefault("belirsizlik", []).append(
            _belirsizlik(pmi_liste))
        sonuc["ses_benzerligi"].setdefault("belirsizlik", []).append(
            _belirsizlik(ses_liste))

        s_ses = sira_bul(ses_liste, gizli)
        sonuc["ses_benzerligi"]["siralar"].append(s_ses)
        sonuc["ses_benzerligi"]["erisilebilir"] += gizli in ses_havuz
        sonuc["ses_benzerligi"]["ayrinti"].append((kut[gizli], s_ses))

        melez_liste = melez_sirala(
            [pmi_liste, ses_liste], agirliklar=list(melez_agirlik))
        sonuc["melez"].setdefault("belirsizlik", []).append(
            _belirsizlik(melez_liste))
        s_melez = sira_bul(melez_liste, gizli)
        sonuc["melez"]["siralar"].append(s_melez)
        sonuc["melez"]["erisilebilir"] += gizli in (pmi_havuz | ses_havuz)
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

    for veri in sonuc.values():
        if "gorulen" in veri:
            veri["havuz"] = len(veri["gorulen"])
        veri["ozet"] = ozet(veri["siralar"], veri["erisilebilir"],
                            havuz_boyu=veri["havuz"])
        veri["ozet"]["olculemedi"] = veri.get("olculemedi", 0)
        bel = [x for x in veri.get("belirsizlik", []) if x == x]
        veri["ozet"]["gorunurluk"] = float(np.median(bel)) if bel else float("nan")
    return sonuc


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
    ayristirici.add_argument("--buzulme", type=float, default=0.0,
                             help="kanıt gücü çarpanı n/(n+k); k=0 kapalı")
    ayristirici.add_argument("--olcut", choices=("pmi", "npmi"), default="pmi",
                             help="birliktelik ölçütü")
    ayristirici.add_argument("--en-kotu", type=int, default=0,
                             help="hiç bulunamayan ilk N sanatçıyı listele")
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        sonuc = calistir(conn, limit=args.limit, ayrinti=args.ayrinti,
                         kapsam=args.kapsam, olcut=args.olcut,
                         melez_agirlik=tuple(
                             float(x) for x in args.melez_agirlik.split(",")),
                         buzulme=args.buzulme,
                         ag=args.ag or args.ag_genis, ag_genis=args.ag_genis)
        print(rapor(sonuc))
        if args.en_kotu:
            for ad, veri in sonuc.items():
                kayip = [s for s, k in veri["ayrinti"] if k is None]
                print(f"{ad}: bulunamayan {len(kayip)} — "
                      f"{', '.join(kayip[:args.en_kotu])}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
