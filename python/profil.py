"""Dinleyici profili — "kütüphanene göre sen böyle birisin".

Bu modül SAYIYI üretir, cümleyi de üretir; çizimi arayüz yapar. Ayrı durmasının
sebebi test edilebilirlik: profil cümleleri kullanıcıya "sen busun" diyor, yanlış
söylememesi gerekiyor.

## Referans sorunu

"Sen şöyle birisin" demek bir karşılaştırma gerektirir, yoksa kütüphaneyi
kendisiyle kıyaslamış olursun. Uydurma bir "ortalama dinleyici" normu YOK —
öyle bir veri elimizde olmadığı için üretmek de dürüst olmaz. Bunun yerine iki
gerçek çapa kullanılıyor:

1. **ÖLÇÜLMÜŞ ÖRNEKLER** (`CAPALAR`). Eminem'in programlanmış beat'i ızgara
   entropisi 0.755 verdi, Meshuggah'ın ride ağırlıklı stili zil payı 0.62.
   Bunlar bu kütüphanede gerçekten ölçülmüş uç noktalar; bir eksende nerede
   durduğunu bunlara göre söylemek uydurma değil.
2. **KENDİ İSİMLENDİRDİĞİN KÜMELER**. "Prog kümen kütüphane medyanından %40 daha
   zil ağırlıklı" cümlesi hem doğrulanabilir hem de senin verdiğin isme dayanıyor.

Kütüphane geneli için üçüncü bir şey söylenmiyor — çünkü söylenemez.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

#: Eksen tanımı: (sütun, stem, okunur ad, düşük ucun anlamı, yüksek ucun anlamı).
#: Yalnız `olcut_denetimi` denetiminden geçmiş, yorumlanabilir eksenler burada —
#: `enerji_payi` gibi miks kararına bağlı olanlar profil cümlesine girmiyor.
EKSENLER: tuple[tuple[str, str, str, str, str], ...] = (
    # --- parça düzeyi ---------------------------------------------------
    ("tempo", "drums", "tempo", "ağır", "hızlı"),
    ("dinamik_db", "drums", "dinamik aralık",
     "sıkıştırılmış / hep aynı seviye", "geniş / nefes alan"),

    # --- davul ----------------------------------------------------------
    ("izgara_entropi", "drums", "ritim insanlığı",
     "programlanmış / ızgaraya kilitli", "insan eli / esneyen"),
    ("zil_payi", "drums", "zil ağırlığı", "tok, zil cimri", "ride/hi-hat ağırlıklı"),
    ("tekme_payi", "drums", "tekme ağırlığı", "hafif ayak", "tom-tekme ağırlıklı"),

    # --- bas ------------------------------------------------------------
    ("perde_araligi", "bass", "bas gezinmesi",
     "kök notada duran", "melodik gezinen"),
    ("nota_vurus", "bass", "bas yoğunluğu", "seyrek, boşluk bırakan", "nota yoğun"),
    ("perde_medyan", "bass", "bas register'ı", "derin / akort düşük", "yüksek"),

    # --- gitar / klavye --------------------------------------------------
    ("perde_araligi", "other", "gitar gezinmesi",
     "sabit riff / akor", "geniş gezinen / solo"),
    ("harmonik_pay", "other", "ton dokusu",
     "distorsiyonlu / gürültülü", "temiz / tonal"),
    ("enerji_payi", "other", "gitar ağırlığı",
     "mikste geride", "gitar duvarı"),
    ("parlaklik", "other", "gitar tınısı", "tok / kalın", "parlak / tiz"),
    ("sustain_orani", "other", "nota uzunluğu",
     "kesik / staccato", "uzayan / atmosferik"),

    # --- vokal -----------------------------------------------------------
    ("perde_medyan", "vocals", "vokal register",
     "kalın / göğüs", "tiz / ince"),
    ("perde_araligi", "vocals", "vokal gezinmesi",
     "düz söyleyiş", "geniş melodik gezinme"),
    ("harmonik_pay", "vocals", "vokal dokusu",
     "gürültülü / haşin / ritmik", "temiz / tonal"),
    ("nota_vurus", "vocals", "söyleyiş hızı", "seyrek / uzun notalar", "yoğun hece"),
    ("enerji_payi", "vocals", "vokal ağırlığı",
     "enstrümantale yakın", "vokal önde"),
)

#: Bu kütüphanede GERÇEKTEN ölçülmüş çapa noktaları. Uydurma norm değil (K13);
#: her biri `stem_profili` içindeki bir albümün gerçek değeri. Uçtan ÜÇÜNCÜ
#: sıradaki albüm seçildi — tek bir aykırı değere yaslanmamak için.
#:
#: DÖRT STEM DE ÇAPALI (2026-09-15). Önceki kümede çapaların %75'i davuldu;
#: bas ve vokalde hiç yoktu. K13 gereği çapası olmayan eksende cümle
#: kurulmuyor, dolayısıyla profil ekranı yalnız davul hakkında konuşuyordu ve
#: uygulama "davulcu uygulaması" gibi hissettiriyordu (kullanıcı geri bildirimi).
CAPALAR: dict[tuple[str, str], tuple[tuple[float, str], ...]] = {
    # --- parça düzeyi ----------------------------------------------------
    ("tempo", "drums"): (
        (47.9, "Eminem — ağır"),
        (184.6, "Madvillain — hızlı"),
    ),
    ("dinamik_db", "drums"): (
        (8.3, "Van Halen — sıkıştırılmış"),
        (68.9, "King Crimson — geniş, nefes alan"),
    ),

    # --- davul ----------------------------------------------------------
    ("izgara_entropi", "drums"): (
        (0.755, "Eminem — programlanmış beat"),
        (0.99, "Meshuggah / Casiopea — insan eli"),
    ),
    ("zil_payi", "drums"): (
        (0.17, "TOOL — tok, tom ağırlıklı"),
        (0.62, "Meshuggah — ride ağırlıklı"),
    ),
    ("tekme_payi", "drums"): (
        (0.17, "Casiopea — hafif ayak"),
        (0.41, "TOOL — tekme ağırlıklı"),
    ),

    # --- bas ------------------------------------------------------------
    ("perde_araligi", "bass"): (
        (1.75, "Skepta — kök notada duran bas"),
        (22.7, "Santana — geniş gezinen bas"),
    ),
    ("nota_vurus", "bass"): (
        (0.29, "Magnum — seyrek, boşluk bırakan"),
        (3.13, "Gojira — nota yoğun bas"),
    ),
    ("perde_medyan", "bass"): (
        (5.2, "Michael Jackson — derin bas"),
        (21.0, "MF DOOM — yüksek register"),
    ),

    # --- gitar / klavye --------------------------------------------------
    ("perde_araligi", "other"): (
        (5.2, "TOOL — sabit riff"),
        (42.4, "Joe Satriani — geniş gezinen solo"),
    ),
    ("harmonik_pay", "other"): (
        (0.66, "Idris Muhammad — gürültülü doku"),
        (0.98, "Skepta — temiz / tonal"),
    ),
    ("enerji_payi", "other"): (
        (0.006, "Eminem — gitar mikste yok denecek kadar geride"),
        (0.222, "Pink Floyd — gitar duvarı"),
    ),
    ("parlaklik", "other"): (
        (478.0, "Gojira — tok, kalın tını"),
        (2746.0, "Supertramp — parlak tını"),
    ),
    ("sustain_orani", "other"): (
        (0.655, "Joji — kesik, kısa notalar"),
        (1.056, "Saxon — uzayan, çınlayan"),
    ),

    # --- vokal -----------------------------------------------------------
    ("perde_medyan", "vocals"): (
        (20.1, "Odezenne — kalın / göğüs"),
        (48.9, "Death — tiz / haykırmaya yakın"),
    ),
    ("perde_araligi", "vocals"): (
        (6.3, "A-Ha — dar aralık"),
        (40.1, "Pantera — geniş gezinme"),
    ),
    ("harmonik_pay", "vocals"): (
        (0.12, "Eminem — ritmik, gürültülü (rap)"),
        (0.98, "Joji — temiz, tonal söyleyiş"),
    ),
    ("nota_vurus", "vocals"): (
        (0.30, "Blade and Bath — seyrek, uzun notalar"),
        (2.66, "MF DOOM — yoğun hece"),
    ),
    ("enerji_payi", "vocals"): (
        (0.008, "Masayoshi Takanaka — enstrümantale yakın"),
        (0.145, "Françoise Hardy — vokal önde"),
    ),
}


#: PROFİL ODAKLARI. Aynı ekran herkese aynı şeyi göstermemeli: biri gitara
#: bakmak ister, biri vokale, biri hiçbirine — düz bir dinleyici profili
#: ister. Kullanıcının geri bildirimi tam olarak buydu: "ben dinleyici
#: profiline girince sadece davul görüyorum; belki adam gitar, vocal istiyor
#: ya da hiçbirini istemiyor."
#:
#: VARSAYILAN «genel» ve enstrüman jargonu İÇERMİYOR. Orada duran eksenler
#: enstrüman bilgisi gerektirmeden okunabilen şeyler: tempo, dinamik aralık,
#: doku temizliği, vokalin mikste önde olup olmaması. «Zil payı» bilmek
#: gerekmiyor.
ODAKLAR: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "genel": (
        "Genel",
        "Enstrüman ayrıntısına girmeden: ne kadar hızlı, ne kadar nefes alan, "
        "ne kadar temiz, vokal önde mi.",
        ("tempo", "dinamik_db", "harmonik_pay|other", "enerji_payi|vocals",
         "sustain_orani|other"),
    ),
    "davul": ("Davul", "Ritmin karakteri: insan eli mi makine mi, ne ağırlıkta.",
              ("izgara_entropi", "zil_payi", "tekme_payi", "tempo", "dinamik_db")),
    "bas": ("Bas", "Bas kök notada mı duruyor, geziniyor mu; ne kadar yoğun.",
            ("perde_araligi|bass", "nota_vurus|bass", "perde_medyan|bass")),
    "gitar": ("Gitar / klavye",
              "Melodik katman: sabit riff mi geniş solo mu, temiz mi distorsiyonlu.",
              ("perde_araligi|other", "harmonik_pay|other", "enerji_payi|other",
               "parlaklik|other")),
    "vokal": ("Vokal", "Register, gezinme, doku ve söyleyiş hızı.",
              ("perde_medyan|vocals", "perde_araligi|vocals", "harmonik_pay|vocals",
               "nota_vurus|vocals", "enerji_payi|vocals")),
    "hepsi": ("Hepsi", "Ölçülen bütün eksenler.", ()),
}

#: Odak başına saçılım haritası: (x sütunu, x stem, y sütunu, y stem, açıklama).
#: Eskiden sayfada SABİT bir "Davul haritası" vardı; odak değişince harita da
#: değişmeli, yoksa vokale bakan kullanıcı yine davul görür.
ODAK_HARITASI: dict[str, tuple[str, str, str, str, str]] = {
    "genel": ("tempo", "drums", "dinamik_db", "drums",
              "Yatay: tempo · Dikey: dinamik aralık. Sağ alt = hızlı ve "
              "sıkıştırılmış; sol üst = ağır ve nefes alan."),
    "davul": ("tekme_payi", "drums", "zil_payi", "drums",
              "Yatay: tekme ağırlığı · Dikey: zil ağırlığı. Sol üst = "
              "zil ağırlıklı, hafif ayak; sağ alt = tom-tekme ağırlıklı."),
    "bas": ("perde_araligi", "bass", "nota_vurus", "bass",
            "Yatay: gezinme · Dikey: nota yoğunluğu. Sağ üst = hem gezinen "
            "hem yoğun bas."),
    "gitar": ("perde_araligi", "other", "enerji_payi", "other",
              "Yatay: gezinme · Dikey: mikste kapladığı yer. Sağ üst = "
              "önde duran, geniş gezinen gitar."),
    "vokal": ("perde_araligi", "vocals", "harmonik_pay", "vocals",
              "Yatay: gezinme · Dikey: doku (aşağı = gürültülü/ritmik, "
              "yukarı = temiz). Sol alt = rap'e yakın; sağ üst = melodik."),
}


def odak_eksenleri(odak: str) -> tuple:
    """Odağa giren eksenler. Bilinmeyen odak `genel`e düşer.

    Anahtar biçimi `sutun` ya da `sutun|stem`; stem verilmezse o sütunun
    hangi stem'den geldiği EKSENLER'deki ilk eşleşmeden alınır.
    """
    if odak == "hepsi":
        return EKSENLER
    _, _, anahtarlar = ODAKLAR.get(odak, ODAKLAR["genel"])
    istenen = []
    for a in anahtarlar:
        sutun, _, stem = a.partition("|")
        istenen.append((sutun, stem or None))
    secilen = []
    for e in EKSENLER:
        for sutun, stem in istenen:
            if e[0] == sutun and (stem is None or e[1] == stem):
                secilen.append(e)
                break
    return tuple(secilen)


def stem_verisi(conn: sqlite3.Connection, tur: str = "album") -> pd.DataFrame:
    """Albüm × stem ölçümleri + sanatçı/albüm adı. Boş tabloda boş çerçeve."""
    try:
        return pd.read_sql_query(
            """
            SELECT s.*, a.artist, a.title, a.year
              FROM stem_profili s JOIN albums a USING (album_id)
             WHERE s.tur = ?
            """,
            conn, params=(tur,),
        )
    except Exception:
        return pd.DataFrame()


def enstruman_dengesi(veri: pd.DataFrame) -> pd.DataFrame:
    """Her stem'in mikste kapladığı yer — kütüphanenin enstrüman ağırlığı.

    `enerji_payi` stem enerjisinin tüm miks enerjisine oranı. Dört stem toplamı
    1 etmez (Demucs artığı ve örtüşme var); mutlak değeri değil stem'ler arası
    dengeyi okumak anlamlı.

    `kapsama` ayrı bir bilgi taşıyor: vokal stem'i kaç albümde ÖLÇÜLEBİLDİ.
    Düşük kapsama enstrümantal ağırlıklı bir kütüphane demek — bu başlı başına
    bir dinleyici özelliği.
    """
    if veri.empty:
        return pd.DataFrame()
    toplam_album = veri["album_id"].nunique()
    satirlar = []
    for stem in ("drums", "bass", "other", "vocals"):
        x = veri[veri["stem"] == stem]
        if x.empty:
            continue
        satirlar.append({
            "stem": stem,
            "enerji_payi": float(x["enerji_payi"].median()),
            "album": int(x["album_id"].nunique()),
            "kapsama": float(x["album_id"].nunique() / max(1, toplam_album)),
        })
    return pd.DataFrame(satirlar)


def eksen_ozeti(veri: pd.DataFrame, odak: str = "hepsi") -> pd.DataFrame:
    """Her eksende kütüphanenin dağılımı + iki ucundaki albümler.

    Uçları isimlendirmek şart: "zil ağırlığın medyanı 0.374" tek başına bir şey
    söylemiyor, "en zil ağırlıklı albümün şu" söylüyor. Kullanıcı kendi
    albümünü görüp ölçümün doğru olup olmadığını anında yargılayabiliyor.
    """
    if veri.empty:
        return pd.DataFrame()
    satirlar = []
    for sutun, stem, ad, dusuk, yuksek in odak_eksenleri(odak):
        # Sütun eksik olabilir: eski veritabanı, kısmi ölçüm ya da göç öncesi
        # çerçeve. Eksik sütunda çakılmak tüm profil ekranını çökertiyordu.
        if sutun not in veri.columns:
            continue
        x = veri[(veri["stem"] == stem) & veri[sutun].notna()]
        if len(x) < 10:
            continue
        sirali = x.sort_values(sutun)
        alt, ust = sirali.iloc[0], sirali.iloc[-1]
        satirlar.append({
            "eksen": ad,
            "sutun": sutun,
            "stem": stem,
            "n": len(x),
            "p5": float(x[sutun].quantile(0.05)),
            "medyan": float(x[sutun].median()),
            "p95": float(x[sutun].quantile(0.95)),
            "dusuk_anlam": dusuk,
            "yuksek_anlam": yuksek,
            "en_dusuk": f"{alt['artist']} — {alt['title']}",
            "en_dusuk_deger": float(alt[sutun]),
            "en_yuksek": f"{ust['artist']} — {ust['title']}",
            "en_yuksek_deger": float(ust[sutun]),
        })
    return pd.DataFrame(satirlar)


def kume_ses_imzasi(
    conn: sqlite3.Connection, veri: pd.DataFrame, U: pd.DataFrame, adlar: dict[int, str]
) -> pd.DataFrame:
    """Her kümenin ses imzası: eksen × küme medyanı, kütüphane medyanına göre.

    Kümeleri kullanıcı isimlendirdi ama isimler kredi ve tür verisinden geldi;
    o kümelerin NASIL SESLENDİĞİ hiç gösterilmiyordu. Burada iki taraf
    birleşiyor — "senin 'prog' dediğin küme ölçülebilir biçimde zil ağırlıklı".

    Albüm kümeye KESKİN atanıyor (en yüksek üyelik). Bulanık ağırlıkla medyan
    almak mümkün değil; ağırlıklı medyan tanımlı ama az üyeli albümler imzayı
    bulanıklaştırıyor ve okunabilirlik düşüyor.
    """
    if veri.empty or U is None or U.empty:
        return pd.DataFrame()
    keskin = U.idxmax(axis=1)
    satirlar = []
    for sutun, stem, ad, *_ in EKSENLER:
        if sutun not in veri.columns:
            continue
        x = veri[(veri["stem"] == stem) & veri[sutun].notna()]
        if len(x) < 10:
            continue
        genel = float(x[sutun].median())
        if genel == 0:
            continue
        x = x.assign(kume=x["album_id"].map(keskin))
        for kume, grup in x.groupby("kume"):
            if len(grup) < 3:  # üç albümden az bir imza taşımaz
                continue
            satirlar.append({
                "eksen": ad,
                "kume": adlar.get(int(kume), f"Küme {int(kume)}"),
                "medyan": float(grup[sutun].median()),
                "genel_medyan": genel,
                "sapma": float(grup[sutun].median() / genel - 1.0),
                "albüm": len(grup),
            })
    return pd.DataFrame(satirlar)


def _sayi(x: float) -> str:
    """Okunur sayı: büyüklüğüne göre basamak.

    «medyanın 117.454» bir insana hiçbir şey söylemiyor ve fazladan üç basamak
    kesinlik iddia ediyor — ölçüm tek bir 30 sn klipten geliyor, o kesinlik
    yok. Tempo 117, oran 0,88 olarak okunuyor.
    """
    if x != x:
        return "—"
    m = abs(x)
    if m >= 100:
        return f"{x:,.0f}".replace(",", ".")
    if m >= 10:
        return f"{x:.1f}".replace(".", ",")
    return f"{x:.2f}".replace(".", ",")


def _capa_cumlesi(sutun: str, stem: str, deger: float) -> str | None:
    """Değeri ölçülmüş çapa noktalarına göre konumlandır."""
    capalar = CAPALAR.get((sutun, stem))
    if not capalar:
        return None
    (alt_d, alt_ad), (ust_d, ust_ad) = capalar[0], capalar[-1]
    if deger <= alt_d:
        return f"{alt_ad} tarafında"
    if deger >= ust_d:
        return f"{ust_ad} tarafında"
    oran = (deger - alt_d) / max(1e-9, ust_d - alt_d)
    yakin = alt_ad if oran < 0.5 else ust_ad
    # EK YERİNE TARAF. Türkçe yönelme eki (-e/-a) ünlü uyumuna bağlı ve
    # yabancı adlarda YAZILIŞA değil OKUNUŞA göre alınıyor: «Death» yazılışta
    # son ünlüsü «a» ama «Deth» okunduğu için «Death'e» olur. Her grup adının
    # okunuşunu tahmin etmeye kalkmak kaçınılmaz olarak yanlış üretir;
    # «... tarafında» kurgusu adı ek almadan bırakıyor ve hep doğru.
    return f"ikisinin arasında, {yakin.split(' — ')[0]} tarafında"


def profil_cumleleri(ozet: pd.DataFrame, denge: pd.DataFrame) -> list[str]:
    """Kütüphaneyi anlatan cümleler — şablon, LLM yok (K2).

    Her cümlenin sayısal dayanağı var ve dayanak ekranda yanında duruyor.
    K7'nin "uydurma yok, doğrulanabilir" kuralı burada da geçerli.
    """
    cumleler: list[str] = []

    if not denge.empty:
        vokal = denge[denge["stem"] == "vocals"]
        if not vokal.empty:
            kapsama = float(vokal.iloc[0]["kapsama"])
            if kapsama < 0.80:
                cumleler.append(
                    f"Albümlerinin yalnızca %{kapsama*100:.0f}'inde ölçülebilir bir vokal "
                    f"katmanı var — kütüphanen enstrümantal ağırlıklı."
                )

    for _, satir in ozet.iterrows():
        capa = _capa_cumlesi(satir["sutun"], satir["stem"], satir["medyan"])
        if not capa:
            continue
        cumleler.append(
            f"**{satir['eksen'].capitalize()}**: medyanın {_sayi(satir['medyan'])}, "
            f"{capa}. "
            f"Uçların: {satir['en_dusuk']} ({_sayi(satir['en_dusuk_deger'])}) ↔ "
            f"{satir['en_yuksek']} ({_sayi(satir['en_yuksek_deger'])})."
        )
    return cumleler


def cesitlilik(ozet: pd.DataFrame) -> pd.DataFrame:
    """Hangi eksende geniş, hangisinde dar bir dinleyicisin.

    Yayılım = (p95 − p5) / |medyan|. Geniş eksen "bu boyutta her şeyi
    dinliyorsun", dar eksen "bu boyutta belirli bir zevkin var" demek. İkincisi
    öneri motoru için daha değerli: dar eksende sapma yapan bir aday risklidir.
    """
    if ozet.empty:
        return pd.DataFrame()
    x = ozet.copy()
    x["yayilim"] = ((x["p95"] - x["p5"]) / x["medyan"].abs().replace(0, np.nan)).abs()
    return x[["eksen", "yayilim", "medyan", "n"]].sort_values("yayilim", ascending=False)
