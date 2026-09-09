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
    ("izgara_entropi", "drums", "ızgara entropisi",
     "programlanmış / ızgaraya kilitli", "insan eli / esneyen"),
    ("zil_payi", "drums", "zil ağırlığı", "tok, zil cimri", "ride/hi-hat ağırlıklı"),
    ("tekme_payi", "drums", "tekme ağırlığı", "hafif ayak", "tom-tekme ağırlıklı"),
    ("harmonik_pay", "other", "ton dokusu (gitar/klavye)",
     "distorsiyonlu / gürültülü", "temiz / tonal"),
    ("perde_medyan", "vocals", "vokal register",
     "kalın / göğüs", "tiz / ince"),
    ("perde_araligi", "vocals", "vokal gezinmesi",
     "düz söyleyiş", "geniş melodik gezinme"),
    ("perde_araligi", "bass", "bas gezinmesi",
     "kök notada duran", "melodik gezinen bas"),
    ("tempo", "drums", "tempo", "ağır", "hızlı"),
)

#: Bu kütüphanede GERÇEKTEN ölçülmüş çapa noktaları. Uydurma norm değil,
#: karar günlüğüne geçmiş ölçümler — profil cümlesi bunlara yaslanıyor.
CAPALAR: dict[tuple[str, str], tuple[tuple[float, str], ...]] = {
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
    ("harmonik_pay", "other"): (
        (0.77, "Annihilator — thrash, distorsiyonlu"),
        (0.97, "A-Ha — temiz synth"),
    ),
}


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


def eksen_ozeti(veri: pd.DataFrame) -> pd.DataFrame:
    """Her eksende kütüphanenin dağılımı + iki ucundaki albümler.

    Uçları isimlendirmek şart: "zil ağırlığın medyanı 0.374" tek başına bir şey
    söylemiyor, "en zil ağırlıklı albümün şu" söylüyor. Kullanıcı kendi
    albümünü görüp ölçümün doğru olup olmadığını anında yargılayabiliyor.
    """
    if veri.empty:
        return pd.DataFrame()
    satirlar = []
    for sutun, stem, ad, dusuk, yuksek in EKSENLER:
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
    return f"ikisinin arasında, {yakin.split(' — ')[0]}'e daha yakın"


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
            f"**{satir['eksen'].capitalize()}**: medyanın {satir['medyan']:.3f}, {capa}. "
            f"Uçların: {satir['en_dusuk']} ({satir['en_dusuk_deger']:.3f}) ↔ "
            f"{satir['en_yuksek']} ({satir['en_yuksek_deger']:.3f})."
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
