"""Müzisyen düzeyinde profil ve benzerlik.

Neden ayrı bir nesne: albüm kümelemesi "birlikte çalmış" kişileri bağlar,
"benzer" kişileri değil. Neil Peart ile Mario Duplantier hiç aynı albümde
bulunmadı; kredi grafiğinde aralarında hiçbir yol yok ve hiçbir blok ağırlığı
onları bir araya getiremez. Ama kullanıcının sorduğu soru tam olarak bu:
"benzer kalibrede davulcular kimler?"

Bu modül müzisyeni kendi başına bir varlık olarak ele alır ve şu profille
tanımlar:

  rol dağılımı      hangi işi yapıyor (davul / gitar / prodüksiyon…)
  tür merkezi       çaldığı albümlerin ağırlıklı etiket vektörü
  ses profili       o albümlerin tempo / ritmik karmaşıklık / dinamik ortalaması
  eksen dağılımı    kullanıcının hangi kümelerinde görünüyor
  dinleme yükü      kullanıcı onun çaldığı albümleri ne kadar dinlemiş

Benzerlik bu profillerin kosinüs yakınlığıdır; tür ile ses arasındaki denge
`ses_agirligi` ile ayarlanır ve hangi temele dayandığı geri döndürülür.

Gerçek kütüphanede ölçülenler (302 albüm, 793 müzisyen):
  ses_agirligi=0     Danny Carey → Portnoy, Garstka          (tür eşleşmesi)
  ses_agirligi=0.5   Danny Carey → Garstka, Lopez, Portnoy   (en iyi denge)
  ses_agirligi=0.85  Mario Duplantier → Ian Paice, Steven Adler (BOZULUYOR)

Ses ağırlığını fazla artırmak sonucu bozuyor, çünkü ses öznitelikleri prodüksiyon
karakterini ölçüyor (kompresyon, parlaklık, nabız düzenliliği), icra kalibresini
değil. Varsayılan 0.5 bu ölçüme dayanıyor.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import numpy as np
import pandas as pd

from python.enrich.rol_eslemesi import ENSTRUMAN_ROLLERI
from python.metin import normalize_esleme

SES_SUTUNLARI = (
    "tempo_medyan",
    "tempo_iqr",
    "dinamik_aralik",
    "nabiz_netligi",
    "vurus_degiskenligi",
    "spektral_merkez",
)


@dataclass
class MuzisyenVerisi:
    profil: pd.DataFrame          # kişi × özet bilgiler
    tur_merkezi: pd.DataFrame     # kişi × etiket
    ses_profili: pd.DataFrame     # kişi × ses özniteliği (boş olabilir)
    eksen_profili: pd.DataFrame   # kişi × küme
    albumleri: pd.DataFrame       # kişi–albüm–rol uzun tablo


def _anahtar(seri: pd.Series, eslesme: dict[str, str] | None = None) -> pd.Series:
    """Profil anahtarı: normalize + (varsa) alias birleştirmesi.

    `normalize_esleme` kaynak ikilemesini ve tipografik farkı çözüyor ama adın
    KENDİSİ farklıysa yetmiyor (神保彰 ↔ Akira Jimbo). `kisi_eslesme` tablosu o
    boşluğu kapatıyor; tablo yoksa davranış eskisiyle birebir aynı kalır.
    """
    anahtarlar = seri.fillna("").map(normalize_esleme)
    if eslesme:
        anahtarlar = anahtarlar.map(lambda a: eslesme.get(a, a))
    return anahtarlar


def muzisyen_verisi(
    conn: sqlite3.Connection,
    uyelik: pd.DataFrame | None = None,
    asgari_album: int = 2,
) -> MuzisyenVerisi:
    """Veritabanından müzisyen profillerini kur."""
    krediler = pd.read_sql_query(
        """
        SELECT c.album_id, c.person_name, c.role, c.kaynak,
               a.artist, a.title, a.year
          FROM credits c JOIN albums a USING (album_id)
        """,
        conn,
    )
    if krediler.empty:
        bos = pd.DataFrame()
        return MuzisyenVerisi(bos, bos, bos, bos, bos)

    from python.enrich.kisi_birlestir import eslesmeleri_oku

    eslesme = eslesmeleri_oku(conn)
    krediler["kisi"] = _anahtar(krediler["person_name"], eslesme)
    krediler = krediler[krediler["kisi"] != ""]
    # Sütun adı olarak ilk görülen yazım kullanılır (okunabilirlik).
    gorunen = krediler.groupby("kisi")["person_name"].first()

    album_sayisi = krediler.groupby("kisi")["album_id"].nunique()
    tutulan = album_sayisi[album_sayisi >= asgari_album].index
    krediler = krediler[krediler["kisi"].isin(tutulan)]
    if krediler.empty:
        bos = pd.DataFrame()
        return MuzisyenVerisi(bos, bos, bos, bos, bos)

    # --- tür merkezi: çaldığı albümlerin etiket vektörlerinin ortalaması ---
    etiketler = pd.read_sql_query("SELECT album_id, tag, agirlik FROM tags", conn)
    if etiketler.empty:
        tur_merkezi = pd.DataFrame(index=sorted(krediler["kisi"].unique()))
    else:
        etiket_matrisi = etiketler.pivot_table(
            index="album_id", columns="tag", values="agirlik",
            aggfunc="sum", fill_value=0.0,
        )
        kisi_album = krediler.drop_duplicates(["kisi", "album_id"])[["kisi", "album_id"]]
        birlesim = kisi_album.merge(
            etiket_matrisi, left_on="album_id", right_index=True, how="left"
        ).drop(columns=["album_id"]).fillna(0.0)
        tur_merkezi = birlesim.groupby("kisi").mean()

    # --- ses profili (albüm düzeyi özniteliklerin ortalaması) ---
    ses = pd.read_sql_query(
        f"SELECT album_id, {', '.join(SES_SUTUNLARI)} FROM audio_features", conn
    )
    if ses.empty:
        ses_profili = pd.DataFrame(index=tur_merkezi.index)
    else:
        kisi_album = krediler.drop_duplicates(["kisi", "album_id"])[["kisi", "album_id"]]
        ses_profili = (
            kisi_album.merge(ses, on="album_id", how="inner")
            .drop(columns=["album_id"])
            .groupby("kisi")
            .mean()
        )

    # --- eksen profili: kullanıcının kümelerine dağılımı ---
    if uyelik is not None and not uyelik.empty:
        kisi_album = krediler.drop_duplicates(["kisi", "album_id"])[["kisi", "album_id"]]
        eksen = (
            kisi_album.merge(uyelik, left_on="album_id", right_index=True, how="inner")
            .drop(columns=["album_id"])
            .groupby("kisi")
            .mean()
        )
        eksen.columns = [f"kume_{k}" for k in eksen.columns]
    else:
        eksen = pd.DataFrame(index=tur_merkezi.index)

    # --- dinleme yükü ---
    dinleme = pd.read_sql_query(
        "SELECT album_id, SUM(adet) AS dinleme FROM plays GROUP BY album_id", conn
    )
    kisi_album = krediler.drop_duplicates(["kisi", "album_id"])[["kisi", "album_id"]]
    if dinleme.empty:
        dinleme_toplami = pd.Series(0, index=sorted(krediler["kisi"].unique()), name="dinleme")
    else:
        dinleme_toplami = (
            kisi_album.merge(dinleme, on="album_id", how="left")
            .fillna({"dinleme": 0})
            .groupby("kisi")["dinleme"]
            .sum()
        )

    # --- özet profil ---
    roller = (
        krediler.groupby(["kisi", "role"])["album_id"].nunique()
        .reset_index().sort_values("album_id", ascending=False)
    )
    ana_rol = roller.drop_duplicates("kisi").set_index("kisi")["role"]
    tum_roller = roller.groupby("kisi")["role"].apply(lambda r: ", ".join(r[:4]))
    sanatcilar = krediler.groupby("kisi")["artist"].apply(
        lambda s: ", ".join(sorted(set(s))[:4])
    )

    profil = pd.DataFrame(
        {
            "kisi": gorunen.reindex(sorted(krediler["kisi"].unique())),
            "ana_rol": ana_rol,
            "roller": tum_roller,
            "album": krediler.groupby("kisi")["album_id"].nunique(),
            "sanatcilar": sanatcilar,
            "dinleme": dinleme_toplami,
            "kaynak": krediler.groupby("kisi")["kaynak"].apply(
                lambda s: "+".join(sorted(set(s)))
            ),
        }
    ).fillna({"dinleme": 0})
    profil.index.name = "anahtar"

    return MuzisyenVerisi(
        profil=profil.sort_values("album", ascending=False),
        tur_merkezi=tur_merkezi,
        ses_profili=ses_profili,
        eksen_profili=eksen,
        albumleri=krediler[["kisi", "album_id", "artist", "title", "year", "role", "kaynak"]],
    )


# --------------------------------------------------------------------------- #
# Benzerlik
# --------------------------------------------------------------------------- #

def _kosinus(matris: pd.DataFrame, hedef: str, *, standartlastir: bool = False) -> pd.Series:
    """Kosinüs benzerliği. `standartlastir` yoğun sayısal bloklar için şart.

    Ses profili gibi az boyutlu ve tamamı pozitif bir blokta ham kosinüs işe
    yaramıyor: bütün vektörler pozitif bölgede aynı yöne bakıyor ve herkes
    herkese ~0.95 benziyor. Ölçüldü — ses ağırlığını 0'dan 0.85'e çıkarmak
    sıralamayı HİÇ değiştirmedi, yalnızca skorları 0.84'ten 0.98'e şişirdi.
    Sütun bazında z ile merkezleyince vektörler gerçekten farklı yönlere
    bakıyor ve benzerlik ayırt etmeye başlıyor.
    """
    if matris.empty or hedef not in matris.index:
        return pd.Series(dtype=float)
    X = matris.to_numpy(dtype=float)
    if standartlastir:
        ortalama = X.mean(axis=0, keepdims=True)
        sapma = X.std(axis=0, keepdims=True)
        sapma[sapma == 0] = 1.0
        X = (X - ortalama) / sapma
    normlar = np.linalg.norm(X, axis=1)
    normlar[normlar == 0] = 1.0
    Xn = X / normlar[:, None]
    v = Xn[matris.index.get_loc(hedef)]
    return pd.Series(Xn @ v, index=matris.index)


def benzer_muzisyenler(
    veri: MuzisyenVerisi,
    hedef_anahtar: str,
    *,
    rol: str | None = None,
    adet: int = 10,
    ses_agirligi: float = 0.5,
) -> tuple[pd.DataFrame, str]:
    """Bir müzisyene benzeyenler. (tablo, benzerliğin neye dayandığı)."""
    if veri.profil.empty or hedef_anahtar not in veri.profil.index:
        return pd.DataFrame(), "veri yok"

    tur = _kosinus(veri.tur_merkezi, hedef_anahtar)
    ses = (
        _kosinus(veri.ses_profili, hedef_anahtar, standartlastir=True)
        if not veri.ses_profili.empty
        else pd.Series(dtype=float)
    )

    if not ses.empty:
        temel = f"tür merkezi (%{(1 - ses_agirligi) * 100:.0f}) + ses profili (%{ses_agirligi * 100:.0f})"
        skor = tur.mul(1 - ses_agirligi).add(ses.mul(ses_agirligi), fill_value=0.0)
    else:
        temel = (
            "YALNIZCA tür merkezi — ses öznitelikleri boş. Bu haliyle sonuç "
            "'aynı türde çalan' demektir, 'aynı kalibrede çalan' değil."
        )
        skor = tur

    sonuc = veri.profil.copy()
    sonuc["benzerlik"] = skor
    sonuc = sonuc.drop(index=hedef_anahtar, errors="ignore")
    sonuc = sonuc[sonuc["benzerlik"].notna()]

    if rol:
        # "Ana rolü davul olanlar" DEĞİL ama "bir kez davul çalanlar" da DEĞİL.
        # Neil Peart'ın en sık kredisi percussion (12), davul (10) ondan az — ana
        # role bakan filtre onu davulcu saymıyordu. Öte yandan Joe Satriani'nin
        # 12 albümünün 1'inde davul kredisi var ve o bir gitarist. Ölçüt: rolün
        # kişinin albümlerindeki payı (bkz. rolu_ustlenenler).
        uygunlar = rolu_ustlenenler(veri, rol)
        sonuc = sonuc[sonuc.index.isin(uygunlar.index)]

    return (
        sonuc.sort_values("benzerlik", ascending=False)
        .head(adet)[["kisi", "ana_rol", "roller", "album", "sanatcilar", "dinleme", "benzerlik"]]
        .round(3),
        temel,
    )


#: Bir rolün "asıl işi" sayılması için gereken asgari pay ve albüm sayısı.
#: Ölçüldü: Joe Satriani'nin 12 albümünün 1'inde davul kredisi var (kendi solo
#: albümünde her şeyi çalmış), Michael Jackson 1/6, Axl Rose 1/3. Bunlar davulcu
#: değil ve davulcu listesinde işleri yok. Neil Peart 10/12, Mario Duplantier 5/5.
ASGARI_ROL_PAYI = 0.40
ASGARI_ROL_ALBUM = 2


def rolu_ustlenenler(
    veri: MuzisyenVerisi,
    rol: str,
    *,
    asgari_pay: float = ASGARI_ROL_PAYI,
    asgari_album: int = ASGARI_ROL_ALBUM,
) -> pd.DataFrame:
    """Rolü ASIL İŞİ olan müzisyenler — bir kez o rolde geçenler değil."""
    if veri.profil.empty:
        return pd.DataFrame()
    tekil = veri.albumleri.drop_duplicates(["kisi", "role", "album_id"])
    rolde = tekil[tekil["role"] == rol].groupby("kisi")["album_id"].nunique()
    toplam = tekil.groupby("kisi")["album_id"].nunique()
    pay = (rolde / toplam.reindex(rolde.index)).rename("rol_payi")
    uygun = pay[(pay >= asgari_pay) & (rolde.reindex(pay.index) >= asgari_album)]
    if uygun.empty:
        return pd.DataFrame()
    cerceve = veri.profil.join(rolde.rename("bu_rolde_album"), how="inner")
    return cerceve.loc[cerceve.index.isin(uygun.index)].join(uygun.round(2))


#: Her enstrüman ailesinin İCRASINI ölçen sütunlar. Aynı ölçütü her role
#: uygulamak yanlış olurdu: davulda perde yok, vokalde tekme/trampet dengesi yok.
#: Bunlar icrayı ölçer (ne çalıyor), tür ya da prodüksiyon karakterini değil —
#: bu yüzden kıyaslamada tür merkezine tercih edilirler. Bkz. K12.
#: BU KÜMELER ELLE SEÇİLMEDİ — `python/enrich/olcut_denetimi.py` üretti (n≈270,
#: 2026-08-16). Her öznitelik diğerlerine regresyon edildi, artık varyans payı
#: 0.30'un altında kalanlar geriye doğru adımsal elemeyle atıldı.
#:
#: Elenenler ve nedeni:
#:   drums   parlaklik (0.092) — zil/tekme/trampet payları zaten aynı şeyi söylüyor
#:           nota_vurus (0.296) — SINIRDA; tempo ve enerji payından türetilebiliyor
#:   diğer   zcr — dört stem'in üçünde parlaklığın kopyası çıktı
#:
#: Eleme SIRAYLA yapıldı, hepsi bir anda değil. Fark kritikti: ilk turda
#: `zil_payi` de 0.234 ile elenecek görünüyordu, oysa müzikal olarak doğrulanmış
#: bir ölçüt (Meshuggah %62 ride). Artıklığı `parlaklik` ile paylaşıyordu ve o
#: zaten eleniyordu; parlaklık gidince zil_payi eşiğin üstüne döndü.
#:
#: `harmonik_pay` dört stem'de de ayakta kaldı (0.45–0.73) — `parlaklik`in
#: kopyası DEĞİL. Gitarda tersi oldu: parlaklık elendi, distorsiyon ölçütü kaldı.
ROL_SUTUNLARI: dict[str, tuple[str, ...]] = {
    "drums": (
        "izgara_entropi", "tekme_payi", "trampet_payi", "zil_payi",
        "harmonik_pay", "sustain_orani", "dinamik_db", "enerji_payi",
        "tempo", "zcr",
    ),
    "bass": (
        "perde_medyan", "perde_araligi", "vibrato_hizi", "nota_vurus",
        "harmonik_pay", "parlaklik", "sustain_orani", "dinamik_db",
        "enerji_payi", "tempo",
    ),
    "guitar": (
        "harmonik_pay", "perde_araligi", "perde_medyan", "nota_vurus",
        "parlaklik", "sustain_orani", "dinamik_db", "enerji_payi",
        "tempo", "vibrato_hizi",
    ),
    "vocals": (
        "perde_medyan", "perde_araligi", "vibrato_hizi", "harmonik_pay",
        "nota_vurus", "parlaklik", "sustain_orani", "dinamik_db",
        "enerji_payi", "tempo",
    ),
}
#: Aynı stem'den beslenen roller aynı ölçüt kümesini kullanır.
ROL_SUTUNLARI["keyboards"] = ROL_SUTUNLARI["guitar"]
ROL_SUTUNLARI["piano"] = ROL_SUTUNLARI["guitar"]
ROL_SUTUNLARI["organ"] = ROL_SUTUNLARI["guitar"]
ROL_SUTUNLARI["synthesizer"] = ROL_SUTUNLARI["guitar"]
ROL_SUTUNLARI["saxophone"] = ROL_SUTUNLARI["guitar"]
ROL_SUTUNLARI["percussion"] = ROL_SUTUNLARI["drums"]
ROL_SUTUNLARI["backing_vocals"] = ROL_SUTUNLARI["vocals"]

#: Geriye dönük ad — eski çağrılar kırılmasın.
DAVUL_SUTUNLARI = ROL_SUTUNLARI["drums"]


def icra_profilleri(conn: sqlite3.Connection, rol: str = "drums") -> pd.DataFrame:
    """Müzisyen × icra özniteliği tablosu.

    Önce `stem_profili` (albüm × stem, dört enstrüman) denenir; yoksa eski
    `davul_profili` tablosuna düşülür. İkisi de aynı ölçütleri üretiyor, fark
    hesaplama birimi: yenisi albüm başına tek demucs geçişiyle dört stem'i
    birden çıkarıyor.
    """
    try:
        from python.enrich.icra_profili import muzisyen_profilleri

        cerceve = muzisyen_profilleri(conn, rol)
        if cerceve is not None and not cerceve.empty:
            return cerceve
    except Exception:
        pass

    if rol != "drums":
        return pd.DataFrame()
    eski = pd.read_sql_query(
        "SELECT * FROM davul_profili WHERE rol = ?", conn, params=(rol,)
    )
    return pd.DataFrame() if eski.empty else eski.set_index("kisi_anahtar")


#: Geriye dönük ad.
davul_profilleri = icra_profilleri


def benzer_icracilar(
    veri: MuzisyenVerisi,
    profiller: pd.DataFrame,
    hedef_anahtar: str,
    *,
    rol: str = "drums",
    adet: int = 10,
    icra_agirligi: float = 0.7,
) -> tuple[pd.DataFrame, str]:
    """İCRA profiline dayalı benzerlik — "aynı kalibrede davulcu" sorusunun cevabı.

    `benzer_muzisyenler` tür merkezine bakıyor ve "aynı TÜRDE çalan" diyor.
    Burada ölçüt davul stem'inden çıkan icra öznitelikleri: vuruş başına nota,
    ızgara entropisi, tekme/trampet/zil dengesi, dinamik. Tür yalnızca ikincil
    ağırlıkla girer — aynı kalibrede ama başka türde çalan davulcu bulunabilsin.
    """
    if profiller.empty or hedef_anahtar not in profiller.index:
        return pd.DataFrame(), "icra profili yok — önce icra_profili.py çalıştırılmalı"

    sutunlar = [
        s for s in ROL_SUTUNLARI.get(rol, ROL_SUTUNLARI["drums"]) if s in profiller.columns
    ]
    if not sutunlar:
        return pd.DataFrame(), f"'{rol}' için icra özniteliği yok"
    # Eksik ölçüm (örn. perde çıkmamış bir klip) sütun medyanıyla doldurulur:
    # kişiyi tamamen atmak, elde olan üç ölçütü de çöpe atmak olurdu.
    sayisal = profiller[sutunlar].astype(float)
    sayisal = sayisal.fillna(sayisal.median(numeric_only=True))
    sayisal = sayisal.dropna(axis=1, how="all")
    if sayisal.empty or hedef_anahtar not in sayisal.index:
        return pd.DataFrame(), f"'{rol}' için yeterli icra ölçümü yok"
    icra = _kosinus(sayisal, hedef_anahtar, standartlastir=True)
    tur = _kosinus(veri.tur_merkezi, hedef_anahtar) if not veri.tur_merkezi.empty else pd.Series(dtype=float)

    skor = icra.mul(icra_agirligi)
    if not tur.empty:
        skor = skor.add(tur.reindex(icra.index).fillna(0.0).mul(1 - icra_agirligi), fill_value=0.0)
        temel = (
            f"{rol} stem'i icra profili (%{icra_agirligi*100:.0f}) + "
            f"tür merkezi (%{(1-icra_agirligi)*100:.0f})"
        )
    else:
        temel = f"yalnızca {rol} stem'i icra profili"

    sonuc = profiller.copy()
    sonuc["benzerlik"] = skor
    sonuc = sonuc.drop(index=hedef_anahtar, errors="ignore")
    sonuc = sonuc[sonuc["benzerlik"].notna()]
    gosterilecek = ["kisi_adi", *sutunlar, "ornek_onizleme", "benzerlik"]
    gosterilecek = [s for s in gosterilecek if s in sonuc.columns]
    return (
        sonuc.sort_values("benzerlik", ascending=False).head(adet)[gosterilecek].round(3),
        temel,
    )


def rol_listesi(veri: MuzisyenVerisi, rol: str = "drums", adet: int = 40) -> pd.DataFrame:
    """Rolü asıl işi olan müzisyenler, o roldeki albüm sayısına göre."""
    cerceve = rolu_ustlenenler(veri, rol)
    if cerceve.empty:
        return pd.DataFrame()
    return (
        cerceve.sort_values(["bu_rolde_album", "rol_payi"], ascending=False)
        .head(adet)[["kisi", "bu_rolde_album", "rol_payi", "album", "sanatcilar", "dinleme"]]
    )


def enstruman_rolleri(veri: MuzisyenVerisi) -> list[str]:
    if veri.albumleri.empty:
        return []
    mevcut = set(veri.albumleri["role"].unique()) & set(ENSTRUMAN_ROLLERI)
    return sorted(mevcut)


# --------------------------------------------------------------------------- #
# Aday albümü kütüphanenin İCRACILARIYLA kıyaslama
#
# Buraya kadar icra karşılaştırması yalnız sahip olunan albümler arasındaydı.
# Öneri ekranının asıl vaadi ise şu: "bu albümün davulcusu, sende olan
# Duplantier kalibresinde çalıyor." Bunun için adayın da stem'i ölçülmüş olmalı
# (`stem_profili.tur = 'aday'`, K11 gereği yine 30 sn önizlemeden).
# --------------------------------------------------------------------------- #

def aday_stem_profili(conn: sqlite3.Connection, aday_id: str, rol: str) -> pd.Series | None:
    """Adayın ilgili stem'inin ölçüm satırı. Ölçülmemişse None."""
    from python.enrich.icra_profili import ROL_STEM

    stem = ROL_STEM.get(rol)
    if not stem:
        return None
    satir = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE album_id = ? AND stem = ?",
        conn, params=(aday_id, stem),
    )
    return None if satir.empty else satir.iloc[0]


def adaya_benzeyen_icracilar(
    conn: sqlite3.Connection, aday_id: str, rol: str = "drums", adet: int = 5
) -> tuple[pd.DataFrame, str]:
    """Adayın stem'ine en yakın KÜTÜPHANE müzisyenleri — en benzerden aza.

    Kıyas müzisyen düzeyinde yapılıyor, albüm düzeyinde değil: soru "bu albüm
    neye benziyor" değil, "bu albümde çalan kişi kimin gibi çalıyor". Kütüphane
    tarafındaki profil kişinin TÜM albümlerinin medyanı olduğu için tek bir
    albümün prodüksiyon tuhaflığı sonucu bozmuyor.

    Standartlaştırma şart (bkz. `_kosinus`): bu öznitelikler tamamı pozitif ve
    az boyutlu, ham kosinüste herkes herkese ~0.95 benziyor.
    """
    profiller = icra_profilleri(conn, rol)
    aday = aday_stem_profili(conn, aday_id, rol)
    if profiller.empty or aday is None:
        return pd.DataFrame(), "adayın ya da kütüphanenin icra profili yok"

    sutunlar = [
        s for s in ROL_SUTUNLARI.get(rol, ())
        if s in profiller.columns and s in aday.index and pd.notna(aday[s])
    ]
    if len(sutunlar) < 3:
        return pd.DataFrame(), "karşılaştırmaya yetecek ölçüt yok"

    # Adayı geçici bir satır olarak ekleyip aynı kosinüs yolundan geçiriyoruz;
    # böylece standartlaştırma aday da dahil TEK ölçekte yapılıyor. Adayı ayrı
    # ölçekleseydik iki farklı z uzayı kıyaslanmış olurdu.
    matris = profiller[sutunlar].astype(float)
    matris = matris.fillna(matris.median())
    ADAY = "__aday__"
    matris.loc[ADAY] = [float(aday[s]) for s in sutunlar]

    skor = _kosinus(matris, ADAY, standartlastir=True).drop(index=ADAY)
    sonuc = profiller.loc[skor.index].copy()
    sonuc["benzerlik"] = skor
    sonuc = sonuc.sort_values("benzerlik", ascending=False).head(adet)
    temel = f"{rol} stem'i, {len(sutunlar)} ölçüt ({', '.join(sutunlar[:4])}…)"
    return sonuc, temel
