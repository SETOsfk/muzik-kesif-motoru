"""Çok boyutlu etiketleme — 12 kaba küme yerine okunabilir tarifler.

## Netflix modeli, doğru anlaşılmış hâliyle

Netflix'in ~76.000 kategorisi kümelemeyle BULUNMADI. İnsan etiketçiler filmleri
onlarca boyutta etiketledi ve kategoriler o etiketlerin KOMBİNASYONU —
"Görsel açıdan çarpıcı nostaljik yabancı dramlar" gibi. Yani üretilmiş
tarifler, keşfedilmiş kümeler değil.

Bu bizim lehimize: zaten etiketçiyiz. Albüm başına ölçtüğümüz eksenler var,
üstüne kredilerden ve tür etiketlerinden gelen bilgi var.

## Üç eksen — MTG-Jamendo yapısı

MTG-Jamendo (55.525 parça, 195 etiket) etiketleri üç kategoriye ayırıyor:
tür (87), enstrüman (40), ruh/tema (56). Bu ayrım bizim veri kaynaklarımıza
birebir oturuyor ve aynı yapı benimsendi:

    tür        MusicBrainz etiketleri + dönem + ülke     (ne tarz)
    enstrüman  ayrılmış stem ölçümleri                   (nasıl çalınmış)
    doku       ton, dinamik, tempo                       (nasıl seslenmiş)

## Eşikler veriden gelir, elle yazılmaz

Bir etiket ancak albüm o eksenin KUYRUĞUNDAYSA veriliyor (varsayılan: üst/alt
%20). Sebep: "zil ağırlıklı" demek ancak kütüphanenin geri kalanına göre
anlamlı. Sabit bir eşik (örn. "zil payı > 0.5") başka bir kütüphanede saçma
olurdu, üstelik bu kütüphanenin medyanı 0.37 iken 0.5 "yüksek" değil "çok
yüksek" demek olurdu.

Ortadaki albümler o eksende etiket ALMAZ. Her albüme her eksenden bir etiket
yapıştırmak, etiketi bilgisizleştirir.
"""

from __future__ import annotations

import sqlite3
from collections import Counter

import pandas as pd

#: DENETİMDEN GEÇEN ÖLÇÜTLER, stem başına (`python -m python.enrich.olcut_denetimi`,
#: 2026-09-02, n≈270). Etiket ancak burada olan bir (sütun, stem) çiftine
#: asılabilir; testi bunu koruyor.
#:
#: Elenenler ve sebepleri: davulda `parlaklik` (artık payı 0,092) ve
#: `nota_vurus` (0,296) — ikisi de diğer davul ölçütlerinin doğrusal
#: bileşiminden ibaret. Perdeli stem'lerin üçünde `zcr` elendi (0,115–0,240),
#: çünkü `parlaklik` ile aynı şeyi söylüyor.
DENETLENEN: dict[str, frozenset[str]] = {
    "drums": frozenset({
        "dinamik_db", "enerji_payi", "harmonik_pay", "izgara_entropi",
        "sustain_orani", "tekme_payi", "tempo", "trampet_payi", "zcr",
        "zil_payi",
    }),
    "bass": frozenset({
        "dinamik_db", "enerji_payi", "harmonik_pay", "nota_vurus",
        "parlaklik", "perde_araligi", "perde_medyan", "sustain_orani",
        "tempo", "vibrato_hizi",
    }),
    "other": frozenset({
        "dinamik_db", "enerji_payi", "harmonik_pay", "nota_vurus",
        "parlaklik", "perde_araligi", "perde_medyan", "sustain_orani",
        "tempo", "vibrato_hizi",
    }),
    "vocals": frozenset({
        "dinamik_db", "enerji_payi", "harmonik_pay", "nota_vurus",
        "parlaklik", "perde_araligi", "perde_medyan", "sustain_orani",
        "tempo", "vibrato_hizi",
    }),
}

#: (sütun, stem, eksen, yön, etiket, açıklama)
#: yön "ust" = üst kuyrukta olanlar etiketi alır, "alt" = alt kuyrukta.
#:
#: DÖRT STEM DE TEMSİL EDİLİR (kullanıcı isteği, 2026-09-02). Önceki küme 20
#: etiketin 9'unu davula ayırmıştı, bası tek etiketle geçmişti ve gitar/klavye
#: tarafını hiç adlandırmamıştı: «distorsiyonlu», «parlak», «kesik» hangi
#: enstrümandan geldiğini söylemiyordu. Etiket adı, ölçümün HANGİ STEM'DEN
#: geldiğini söylemek zorunda — aksi hâlde kullanıcı davulu okuyup gerisini
#: tahmin ediyor.
#:
#: `enerji_payi` BİLEŞİMSEL: dört stem'in payı toplamda mikse eşit, yani bir
#: albüm hem «bas ağırlıklı» hem «gitar duvarı» olamaz. Bu bir kusur değil,
#: tam da ayırt eden şey.
OLCUM_ETIKETLERI: tuple[tuple[str, str, str, str, str, str], ...] = (
    # ---------------------------------------------------------------- parça --
    ("tempo", "drums", "doku", "ust", "hızlı",
     "Şarkının temposu kütüphanenin üst beşte birinde."),
    ("tempo", "drums", "doku", "alt", "ağır",
     "Şarkının temposu kütüphanenin alt beşte birinde."),
    ("dinamik_db", "drums", "doku", "ust", "geniş dinamik",
     "Yüksek ve kısık anlar arasında büyük fark. Davul stem'inden ölçülüyor; "
     "miksin dinamiğini en iyi o taşıyor."),
    ("dinamik_db", "drums", "doku", "alt", "sıkıştırılmış",
     "Dinamik aralık dar — ağır kompresyon."),

    # ---------------------------------------------------------------- davul --
    ("zil_payi", "drums", "enstruman", "ust", "ride ağırlıklı davul",
     "Davul sesinin büyük kısmı zillerden — ride/hi-hat sürekli çalışıyor."),
    ("zil_payi", "drums", "enstruman", "alt", "tok davul",
     "Ziller cimri kullanılmış; ağırlık tom ve trampette."),
    ("tekme_payi", "drums", "enstruman", "ust", "ayak yüklü davul",
     "Bas davul mikste öne çıkıyor."),
    ("trampet_payi", "drums", "enstruman", "ust", "trampet önde davul",
     "Ağırlık trampette — backbeat sert vurgulanıyor."),
    ("izgara_entropi", "drums", "enstruman", "alt", "programlanmış ritim",
     "Vuruşlar 16'lık ızgaraya kilitli — makine ya da ızgaraya çok yakın icra."),
    ("izgara_entropi", "drums", "enstruman", "ust", "serbest ritim",
     "Vuruşlar ızgaradan belirgin sapıyor — insan salınımı ya da serbest ölçü."),
    ("sustain_orani", "drums", "enstruman", "alt", "kuru davul",
     "Vuruşlar hemen kesiliyor — sönümlenmiş deriler ya da kapılı reverb."),
    ("sustain_orani", "drums", "enstruman", "ust", "çınlayan davul",
     "Davul uzun çınlıyor — açık oda ya da bol reverb."),
    ("enerji_payi", "drums", "enstruman", "ust", "davul önde miks",
     "Mikste en çok yer kaplayan katman davul."),
    ("harmonik_pay", "drums", "enstruman", "alt", "gürültülü davul",
     "Davul katmanı gürültü ağırlıklı — saturasyon ya da ezilmiş oda mikrofonu."),

    # ------------------------------------------------------------------ bas --
    ("perde_araligi", "bass", "enstruman", "ust", "melodik bas",
     "Bas kök notada durmuyor, geniş bir alanda geziniyor."),
    ("perde_araligi", "bass", "enstruman", "alt", "kök notada bas",
     "Bas akorun kökünde duruyor; hareket etmiyor."),
    ("perde_medyan", "bass", "enstruman", "alt", "derin bas",
     "Bas alışılmıştan düşük register'da — akort düşürülmüş olabilir."),
    ("nota_vurus", "bass", "enstruman", "ust", "yoğun bas",
     "Vuruş başına çok nota; bas boşluk bırakmıyor."),
    ("enerji_payi", "bass", "enstruman", "ust", "bas ağırlıklı miks",
     "Mikste en çok yer kaplayan katman bas."),
    ("harmonik_pay", "bass", "enstruman", "alt", "distorsiyonlu bas",
     "Bas katmanı gürültülü — overdrive ya da fuzz."),
    ("parlaklik", "bass", "enstruman", "ust", "tırmalayan bas",
     "Basın ağırlık merkezi tizde — parmak/pena atağı öne çıkmış."),

    # ------------------------------------------------------- gitar / klavye --
    ("harmonik_pay", "other", "doku", "alt", "distorsiyonlu gitar",
     "Gitar/klavye katmanı gürültülü — distorsiyon ya da saturasyon."),
    ("harmonik_pay", "other", "doku", "ust", "temiz ton",
     "Melodik katman tonal ve temiz."),
    ("parlaklik", "other", "doku", "ust", "parlak tını",
     "Gitar/klavye katmanının ağırlık merkezi tizde."),
    ("parlaklik", "other", "doku", "alt", "tok tını",
     "Gitar/klavye katmanının ağırlık merkezi kalın tarafta."),
    ("sustain_orani", "other", "doku", "ust", "uzayan",
     "Notalar çınlıyor; atmosferik."),
    ("sustain_orani", "other", "doku", "alt", "kesik",
     "Notalar kısa; staccato."),
    ("perde_araligi", "other", "enstruman", "ust", "geniş gezinen gitar",
     "Gitar/klavye geniş bir aralıkta dolaşıyor — solo ya da arpej ağırlıklı."),
    ("nota_vurus", "other", "enstruman", "ust", "nota yoğun gitar",
     "Vuruş başına çok nota; riff ya da pasaj yoğun."),
    ("enerji_payi", "other", "enstruman", "ust", "gitar duvarı",
     "Mikste en çok yer kaplayan katman gitar/klavye."),
    ("vibrato_hizi", "other", "enstruman", "ust", "vibratolu gitar",
     "Perde sürekli salınıyor — vibrato, bend ya da tremolo kolu."),

    # ---------------------------------------------------------------- vokal --
    ("perde_araligi", "vocals", "enstruman", "ust", "geniş vokal",
     "Vokal geniş bir aralıkta geziniyor."),
    ("perde_araligi", "vocals", "enstruman", "alt", "düz söyleyiş",
     "Vokal dar bir aralıkta, konuşmaya yakın."),
    ("perde_medyan", "vocals", "enstruman", "ust", "tiz vokal", "Yüksek register."),
    ("perde_medyan", "vocals", "enstruman", "alt", "kalın vokal", "Düşük register."),
    ("vibrato_hizi", "vocals", "enstruman", "ust", "vibratolu vokal",
     "Perde sürekli salınıyor — belirgin vibrato."),
    ("nota_vurus", "vocals", "enstruman", "ust", "hızlı söyleyiş",
     "Vuruş başına çok hece — rap ya da yoğun fraz."),
    ("enerji_payi", "vocals", "enstruman", "ust", "vokal önde miks",
     "Mikste en çok yer kaplayan katman vokal."),
    ("enerji_payi", "vocals", "enstruman", "alt", "vokal geride miks",
     "Vokal miksin içine gömülmüş — enstrümanlar önde."),
    ("harmonik_pay", "vocals", "enstruman", "alt", "haşin vokal",
     "Vokal katmanı gürültü ağırlıklı — scream, growl ya da sert saturasyon."),
)

#: Kuyruk payı. %20 = her eksende albümlerin en fazla beşte biri etiket alır.
KUYRUK = 0.20

#: Tür etiketi için bir etiketin kaç albümde geçmesi gerektiği. Tek albümde
#: geçen etiket bir kategori kurmaz, gürültüdür.
ASGARI_TUR = 3


#: Türkçe ünlü uyumu: -lı / -li / -lu / -lü son ünlüye göre seçilir.
#: Düz birleştirme "davullı", "söyleyişlı", "ritimlı" gibi bozuk sonuçlar
#: veriyordu — tarif okunabilir olacaksa dilbilgisi de doğru olmalı.
_UYUM = {"a": "lı", "ı": "lı", "e": "li", "i": "li",
         "o": "lu", "u": "lu", "ö": "lü", "ü": "lü"}


def _lu(sozcuk: str) -> str:
    """Sözcüğe ünlü uyumuna göre -lı/-li/-lu/-lü ekle."""
    for harf in reversed(sozcuk.lower()):
        if harf in _UYUM:
            ek = _UYUM[harf]
            # Sonu ünlüyle biten sözcükte kaynaştırma yok: "davul" + "lu".
            return f"{sozcuk}{ek}"
    return sozcuk


#: Onyılın Türkçe okunuşunun SON ÜNLÜSÜ eki belirler; hepsine "'ler" eklemek
#: yanlış. 1990 "doksanlar", 1980 "seksenler", 1960 "altmışlar", 2020
#: "yirmiler". Test bu hatayı yakaladı.
_ONYIL_EKI = {
    1900: "ler", 1910: "lar", 1920: "ler", 1930: "lar", 1940: "lar",
    1950: "ler", 1960: "lar", 1970: "ler", 1980: "ler", 1990: "lar",
    2000: "ler", 2010: "lar", 2020: "ler", 2030: "lar",
}


def _donem(yil) -> str | None:
    if yil is None or pd.isna(yil) or yil < 1900:
        return None
    onyil = int(yil) // 10 * 10
    return f"{onyil}'{_ONYIL_EKI.get(onyil, 'ler')}"


def olcum_etiketleri(conn: sqlite3.Connection) -> pd.DataFrame:
    """Stem ölçümlerinden kuyruk temelli etiketler."""
    veri = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE tur = 'album'", conn
    )
    if veri.empty:
        return pd.DataFrame(columns=["album_id", "eksen", "etiket"])

    satirlar = []
    for sutun, stem, eksen, yon, etiket, _ in OLCUM_ETIKETLERI:
        if sutun not in veri.columns:
            continue
        x = veri[(veri["stem"] == stem) & veri[sutun].notna()]
        if len(x) < 20:
            continue
        # Eşik KÜTÜPHANEDEN: "zil ağırlıklı" ancak geri kalanına göre anlamlı.
        esik = x[sutun].quantile(1 - KUYRUK if yon == "ust" else KUYRUK)
        secilen = x[x[sutun] >= esik] if yon == "ust" else x[x[sutun] <= esik]
        for album_id in secilen["album_id"]:
            satirlar.append({"album_id": album_id, "eksen": eksen,
                             "etiket": etiket, "kaynak": "olcum"})
    return pd.DataFrame(satirlar)


def tur_etiketleri(conn: sqlite3.Connection) -> pd.DataFrame:
    """MusicBrainz tür etiketleri + dönem + ülke."""
    satirlar = []
    sayac = Counter(
        r[0] for r in conn.execute("SELECT tag FROM tags WHERE tag IS NOT NULL")
    )
    for album_id, tag in conn.execute(
        "SELECT album_id, tag FROM tags WHERE tag IS NOT NULL"
    ):
        if sayac[tag] >= ASGARI_TUR:
            satirlar.append({"album_id": album_id, "eksen": "tur",
                             "etiket": tag, "kaynak": "musicbrainz"})

    for album_id, yil, ulke in conn.execute(
        "SELECT album_id, year, country FROM albums"
    ):
        donem = _donem(yil)
        if donem:
            satirlar.append({"album_id": album_id, "eksen": "tur",
                             "etiket": donem, "kaynak": "yil"})
        if ulke:
            satirlar.append({"album_id": album_id, "eksen": "tur",
                             "etiket": f"ülke:{ulke}", "kaynak": "ulke"})
    return pd.DataFrame(satirlar)


def etiketle(conn: sqlite3.Connection) -> pd.DataFrame:
    parcalar = [d for d in (olcum_etiketleri(conn), tur_etiketleri(conn))
                if not d.empty]
    if not parcalar:
        return pd.DataFrame(columns=["album_id", "eksen", "etiket", "kaynak"])
    return pd.concat(parcalar, ignore_index=True).drop_duplicates(
        subset=["album_id", "etiket"]
    )


def yaz(conn: sqlite3.Connection, etiketler: pd.DataFrame) -> int:
    with conn:
        conn.execute("DELETE FROM album_etiket")
        conn.executemany(
            "INSERT OR IGNORE INTO album_etiket (album_id, eksen, etiket, kaynak) "
            "VALUES (?,?,?,?)",
            etiketler[["album_id", "eksen", "etiket", "kaynak"]].itertuples(
                index=False, name=None),
        )
    return len(etiketler)


def tarifler(
    conn: sqlite3.Connection, *, asgari_albom: int = 2, adet: int = 60
) -> pd.DataFrame:
    """Etiket KOMBİNASYONLARI — Netflix'in "altgenre"lerinin karşılığı.

    Tek tek etiketler zaten var; buradaki iş onları birleştirip okunabilir
    tarifler üretmek. Üç eksenden birer etiket alınıyor (tür + enstrüman +
    doku) ve o üçlüyü birden taşıyan albümler sayılıyor.

    `asgari_albom`: tek albümlük bir tarif bir kategori değil, o albümün
    tarifidir. En az iki albüm gerekiyor ki "bu bir tür" denebilsin.
    """
    veri = pd.read_sql_query("SELECT * FROM album_etiket", conn)
    if veri.empty:
        return pd.DataFrame()

    eksenler = {
        e: veri[veri["eksen"] == e].groupby("album_id")["etiket"].apply(list)
        for e in ("tur", "enstruman", "doku")
    }
    albumler = set(veri["album_id"])
    sayac: Counter = Counter()
    for album_id in albumler:
        turler = eksenler["tur"].get(album_id, [])[:6]
        enstrumanlar = eksenler["enstruman"].get(album_id, [])[:4]
        dokular = eksenler["doku"].get(album_id, [])[:4]
        for t in turler:
            for e in enstrumanlar:
                for d in dokular:
                    sayac[(t, e, d)] += 1

    satirlar = [
        {"tur": t, "enstruman": e, "doku": d, "albüm": n,
         "tarif": f"{d}, {_lu(e)} {t}"}
        for (t, e, d), n in sayac.items() if n >= asgari_albom
    ]
    if not satirlar:
        return pd.DataFrame()
    return (pd.DataFrame(satirlar).sort_values("albüm", ascending=False)
            .head(adet).reset_index(drop=True))


def albom_etiketleri(conn: sqlite3.Connection, album_id: str) -> dict[str, list[str]]:
    sonuc: dict[str, list[str]] = {"tur": [], "enstruman": [], "doku": []}
    for eksen, etiket in conn.execute(
        "SELECT eksen, etiket FROM album_etiket WHERE album_id = ? ORDER BY eksen",
        (album_id,),
    ):
        sonuc.setdefault(eksen, []).append(etiket)
    return sonuc


ACIKLAMALAR = {etiket: aciklama for _, _, _, _, etiket, aciklama in OLCUM_ETIKETLERI}


def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path

    from python.db import VARSAYILAN_DB, baglan

    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        etiketler = etiketle(conn)
        print(f"{yaz(conn, etiketler)} etiket · "
              f"{etiketler['album_id'].nunique()} albüm · "
              f"{etiketler['etiket'].nunique()} ayrı etiket")
        t = tarifler(conn)
        print(f"\n{len(t)} tarif:")
        for _, r in t.head(20).iterrows():
            print(f"  {r['albüm']:>3} albüm  ·  {r['tarif']}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------- #
# Bağlam etiketleri — çalma listesi başlıklarından
# --------------------------------------------------------------------------- #

#: MTG-Jamendo'nun 56 ruh/tema etiketinden, çalma listesi başlıklarında
#: gerçekten karşılığı olanlar + çok dilli varyantları. Serbest kelime
#: toplamak YANLIŞ olurdu: başlıklarda sanatçı adları ("GOJIRA DEEZER",
#: "Ritchie Blackmore"), kişisel notlar ("new staff", "Jesse john's") ve
#: coğrafya ("Top Croatia") var. Kontrollü sözlük bunları dışarıda bırakıyor.
#:
#: Türkçe karşılık veriliyor çünkü etiket kullanıcıya gösteriliyor.
BAGLAM_SOZLUGU: dict[str, tuple[str, ...]] = {
    "sakin": ("calm", "relax", "relaxing", "chill", "mellow", "soft", "quiet",
              "douceur", "tranquil", "sakin"),
    "enerjik": ("energetic", "upbeat", "powerful", "energy", "pump", "hype",
                "workout", "gym", "sport", "running", "training"),
    "melankolik": ("melancholic", "sad", "melancholy", "triste", "blue",
                   "hüzün", "hüzünlü"),
    "romantik": ("romantic", "love", "romantique", "amour", "aşk", "slow"),
    "karanlık": ("dark", "doom", "horror", "grim", "evil", "brutal"),
    "epik": ("epic", "cinematic", "soundtrack", "trailer", "orchestral",
             "film", "bo ", "score"),
    "parti": ("party", "dance", "club", "fiesta", "festa", "parti"),
    "meditatif": ("meditative", "ambient", "ambiental", "soundscape",
                  "meditation", "drone", "atmospheric"),
    "neşeli": ("happy", "fun", "funny", "positive", "feel good", "good vibes",
              "uplifting", "hopeful"),
    "sabah": ("morning", "matin", "wake", "breakfast", "sunday", "dimanche"),
    "akşam": ("evening", "night", "late night", "midnight", "soir", "gece"),
    "odaklanma": ("focus", "study", "work", "concentration", "coding",
                  "reading", "çalışma"),
    "sürüş": ("driving", "drive", "road trip", "roadtrip", "yolculuk"),
    "yaz": ("summer", "beach", "tropical", "yaz"),
    "nostaljik": ("retro", "nostalgia", "nostalgic", "oldies", "classics",
                  "throwback", "nostalji"),
    "enstrümantal": ("instrumental", "no vocals", "enstrümantal"),
}

#: Bir bağlam etiketinin sanatçıya yapışması için kaç ayrı listede geçmesi
#: gerektiği.
#:
#: 2'ye ayarlamak DENENDİ ve kapsamayı öldürdü: kütüphanenin 147 sanatçısından
#: yalnız 18'i etiket alıyordu (eşik 1'de 79). Sebep, liste başlıklarının
#: yalnız %17'sinin sözlükten bir terim içermesi — iki ayrı böyle listede
#: geçmek nadir.
#:
#: Çözüm bu projede tekrarlayan çözüm: otomatik elemek yerine KANITI GÖSTERMEK.
#: Etiket kaç listeden geldiğini taşıyor; bir listeden gelen bir kişinin
#: kararı, beş listeden gelen bir örüntü ve arayüz ikisini ayırt ettiriyor.
ASGARI_BAGLAM_LISTE = 1


def baglam_etiketleri(conn: sqlite3.Connection) -> pd.DataFrame:
    """Çalma listesi başlıklarından sanatçı düzeyinde bağlam etiketleri.

    "Dinleyici tipi" sinyali burada: «Evening Chill», «GYMeshuggah»,
    «Calm jazz for work» — kalabalığın müziği HANGİ BAĞLAMA koyduğu.
    Kredi grafiği de tür etiketi de bunu söyleyemiyor.

    Sanatçı düzeyinde, albüm düzeyinde değil: bir liste sanatçının bir
    parçasını içeriyor, o parçanın hangi albümden olduğu listede yok.
    """
    satirlar = []
    baslik_sanatci = conn.execute(
        """SELECT c.baslik, p.sanatci_anahtar
             FROM calma_listesi c JOIN liste_parca p USING (liste_id)
            WHERE c.baslik IS NOT NULL"""
    ).fetchall()

    sayac: dict[tuple[str, str], set[str]] = {}
    for baslik, anahtar in baslik_sanatci:
        dusuk = f" {baslik.lower()} "
        for etiket, kelimeler in BAGLAM_SOZLUGU.items():
            if any(k in dusuk for k in kelimeler):
                sayac.setdefault((anahtar, etiket), set()).add(baslik)

    for (anahtar, etiket), basliklar in sayac.items():
        if len(basliklar) >= ASGARI_BAGLAM_LISTE:
            satirlar.append({"sanatci_anahtar": anahtar, "etiket": etiket,
                             "liste": len(basliklar)})
    return pd.DataFrame(satirlar)


def sanatci_baglami(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """sanatçı anahtarı -> bağlam etiketleri (en çok listede geçenler önce)."""
    veri = baglam_etiketleri(conn)
    if veri.empty:
        return {}
    return {
        anahtar: list(grup.sort_values("liste", ascending=False)["etiket"])[:4]
        for anahtar, grup in veri.groupby("sanatci_anahtar")
    }


def aday_olcum_etiketleri(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Aday albümlerin kendi stem ölçümlerinden etiketler.

    Eşikler KÜTÜPHANEDEN hesaplanıyor, aday havuzundan değil. Sebep: etiketin
    anlamı "senin kütüphanene göre zil ağırlıklı" olmalı. Aday havuzuna göre
    ölçeklenirse etiket, o gün hangi adayların üretildiğine bağlı hale gelir
    ve iki çalışma arasında kıyaslanamaz — `ses_uzakligi`'ndaki ölçek kararının
    aynısı.
    """
    kutuphane = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE tur = 'album'", conn)
    adaylar = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE tur = 'aday'", conn)
    if kutuphane.empty or adaylar.empty:
        return {}

    sonuc: dict[str, list[str]] = {}
    for sutun, stem, _eksen, yon, etiket, _ in OLCUM_ETIKETLERI:
        if sutun not in kutuphane.columns:
            continue
        k = kutuphane[(kutuphane["stem"] == stem) & kutuphane[sutun].notna()]
        if len(k) < 20:
            continue
        esik = k[sutun].quantile(1 - KUYRUK if yon == "ust" else KUYRUK)
        a = adaylar[(adaylar["stem"] == stem) & adaylar[sutun].notna()]
        secilen = a[a[sutun] >= esik] if yon == "ust" else a[a[sutun] <= esik]
        for album_id in secilen["album_id"]:
            sonuc.setdefault(album_id, []).append(etiket)
    return sonuc
