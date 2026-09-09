"""Geri bildirim döngüsü — Faz 3.

Kullanıcı her aday için üç şeyden birini diyebiliyor: beğendim / tutmadı /
zaten biliyorum. Bu modül o kararları ölçüme çevirir.

## Üç karar, İKİ AYRI eksen

En kolay hata üçünü tek bir "iyi–kötü" ekseninde toplamak olurdu. Oysa
"zaten biliyorum" bambaşka bir şey söylüyor:

    beğendim         → zevk tuttu   ✓   keşif oldu   ✓
    tutmadı          → zevk tutmadı ✗   keşif oldu   ✓  (yeni bir şeydi)
    zaten biliyorum  → zevk hakkında BİLGİ YOK       ✗  keşif OLMADI

Yani iki ayrı oran hesaplanmalı:

    zevk isabeti = beğendim / (beğendim + tutmadı)     ← "zaten biliyorum" HARİÇ
    keşif oranı  = 1 − zaten_biliyorum / toplam

Bir strateji zevk isabetinde mükemmel olup keşifte tamamen başarısız olabilir:
kullanıcının kesin seveceği ama zaten bildiği albümleri önermek. Ölçüldü —
`sahne_komsulugu` sekiz kez "zaten biliyorum" aldı (çoğu Nirvana). Projenin
çıkış noktası "yeni müzikler keşfedemiyorum" olduğu için bu, zevk hatasından
DAHA ÖNEMLİ bir başarısızlık.

## Küçük örneklem

Kullanıcı bir avuç karar verdi. Ham oran bu boyutta yanıltıcı: 1/1 = %100 ile
80/80 = %100 aynı sayı değil. Wilson skor aralığı kullanılıyor — küçük n'de
normal yaklaşımdan daha dürüst ve oran 0 ya da 1'e dayandığında bile çalışıyor.
Arayüz aralığı gösterir, tek bir sayı göstermez.

## Geri bildirimin işe yaradığı yer

Vagon "eksen ağırlıklarını güncelle"mek değil — kullanıcı zaten ekseni kendi
seçiyor. Somut ve doğrudan işleyen kullanım şu: bir sanatçıyı "zaten biliyorum"
dediysen, o sanatçının DİĞER albümleri de büyük olasılıkla biliniyordur.
`bilinen_sanatcilar()` bunu çıkarır, öneri listesi bu sanatçıları geri plana
atar. Ölçülebilir bir şeyi ölçülebilir biçimde kullanmak, bulanık bir ağırlık
çarpanından daha dürüst.
"""

from __future__ import annotations

import math
import sqlite3

import pandas as pd

#: Wilson aralığı için z (0.90 güven — küçük örneklemde 0.95 aralıkları
#: neredeyse (0,1) çıkıp hiçbir şey söylemiyor).
Z = 1.645

#: Bir strateji hakkında CÜMLE kurmak için gereken en az karar sayısı. Aralık
#: hesabı her n'de çalışır ve tabloda gösterilir; ama kullanıcıya "bu strateji
#: şöyle" demek için dörtten az karar yetmez.
ASGARI_N = 4


def wilson(basari: int, toplam: int, z: float = Z) -> tuple[float, float, float]:
    """Wilson skor aralığı: (nokta tahmini, alt sınır, üst sınır).

    Neden Wilson: normal yaklaşım (p ± z·√(p(1−p)/n)) küçük n'de aralığı
    [0,1] dışına taşırıyor ve p=0 ya da p=1 olduğunda genişliği SIFIR veriyor —
    yani "1/1 beğendim" için %100 kesinlik iddia ediyor. Wilson ikisinde de
    doğru davranır.
    """
    if toplam <= 0:
        return (0.0, 0.0, 1.0)
    p = basari / toplam
    payda = 1 + z**2 / toplam
    merkez = (p + z**2 / (2 * toplam)) / payda
    yayilim = z * math.sqrt(p * (1 - p) / toplam + z**2 / (4 * toplam**2)) / payda
    return (p, max(0.0, merkez - yayilim), min(1.0, merkez + yayilim))


def kararlar(conn: sqlite3.Connection, calisma_id: str | None = None) -> pd.DataFrame:
    """Geri bildirim × aday birleşimi.

    Bir aday İKİ stratejiden birden gelmiş olabilir (tasarım gereği — ikisinin
    gerekçesi farklı, ikisi de saklanıyor). O yüzden birleşim geri bildirim
    satırından fazla satır üretir ve bu doğrudur: kullanıcının kararı her iki
    stratejiyi de ilgilendiriyor.
    """
    sorgu = """
        SELECT f.aday_id, f.karar, f.eksen, f.tarih, a.strateji, a.artist, a.title
          FROM feedback f
          JOIN adaylar a ON a.aday_id = f.aday_id AND a.calisma_id = f.calisma_id
    """
    kosul, parametre = "", []
    if calisma_id:
        kosul, parametre = " WHERE f.calisma_id = ?", [calisma_id]
    try:
        return pd.read_sql_query(sorgu + kosul, conn, params=parametre)
    except Exception:
        return pd.DataFrame()


def strateji_isabeti(veri: pd.DataFrame) -> pd.DataFrame:
    """Strateji başına zevk isabeti ve KEŞİF oranı, Wilson aralıklarıyla.

    İkisi ayrı ölçülür (bkz. modül başlığı): "zaten biliyorum" zevk isabetinin
    paydasına GİRMEZ — kullanıcı o albümü beğenip beğenmediğini söylemedi —
    ama keşif oranının paydasına girer, çünkü keşif tam olarak orada başarısız.
    """
    if veri.empty:
        return pd.DataFrame()
    satirlar = []
    for strateji, grup in veri.groupby("strateji"):
        begendim = int((grup["karar"] == "begendim").sum())
        tutmadi = int((grup["karar"] == "tutmadi").sum())
        bilinen = int((grup["karar"] == "zaten_biliyorum").sum())
        toplam = len(grup)

        zevk_n = begendim + tutmadi
        zevk, zevk_alt, zevk_ust = wilson(begendim, zevk_n)
        kesif, kesif_alt, kesif_ust = wilson(toplam - bilinen, toplam)

        satirlar.append({
            "strateji": strateji,
            "toplam": toplam,
            "begendim": begendim,
            "tutmadi": tutmadi,
            "zaten_biliyorum": bilinen,
            "zevk_isabeti": zevk if zevk_n else None,
            "zevk_alt": zevk_alt if zevk_n else None,
            "zevk_ust": zevk_ust if zevk_n else None,
            "zevk_n": zevk_n,
            "kesif_orani": kesif,
            "kesif_alt": kesif_alt,
            "kesif_ust": kesif_ust,
        })
    return pd.DataFrame(satirlar).sort_values("toplam", ascending=False)


def bilinen_sanatcilar(conn: sqlite3.Connection) -> set[str]:
    """"Zaten biliyorum" denen adayların sanatçıları.

    Kullanım: bir sanatçıyı bildiğini söylediysen, o sanatçının başka albümleri
    de büyük olasılıkla biliniyordur. Öneri listesi bunları geri plana atar.

    ELEMİYOR, geri plana atıyor — fark önemli. Bir sanatçının bir albümünü
    bilmek diğerlerini bildiğin anlamına gelmez; Nirvana'yı bilip «Bleach»i
    duymamış olabilirsin. Karar kullanıcının.
    """
    from python.metin import normalize_esleme

    try:
        satirlar = conn.execute(
            """
            SELECT DISTINCT a.artist
              FROM feedback f
              JOIN adaylar a ON a.aday_id = f.aday_id AND a.calisma_id = f.calisma_id
             WHERE f.karar = 'zaten_biliyorum'
            """
        ).fetchall()
    except Exception:
        return set()
    return {normalize_esleme(r[0]) for r in satirlar if r[0]}


def uzaklik_tercihi(
    conn: sqlite3.Connection, veri: pd.DataFrame, calisma_id: str
) -> pd.DataFrame:
    """Beğenilen adaylar, tutmayanlardan daha mı uzak?

    Doğrudan bir soru: "ne kadar uzağa gitmeye hazırsın?" Cevabı varsa öneri
    sıralaması buna göre ayarlanabilir. Ama n küçük olduğu sürece cevap YOK
    demek doğru olan — bu yüzden karar başına en az 3 ölçüm aranıyor ve
    altındaysa satır hiç üretilmiyor.
    """
    from python.discover.ses_uzakligi import (
        aday_uzakligi, eksen_ses_merkezi, kutuphane_olcegi,
    )

    if veri.empty:
        return pd.DataFrame()
    olcek = kutuphane_olcegi(conn)
    stemler = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE tur = 'aday'", conn
    )
    if not olcek or stemler.empty:
        return pd.DataFrame()

    merkezler: dict[int, dict] = {}
    kayitlar = []
    for satir in veri.itertuples():
        eksen = int(satir.eksen)
        if eksen not in merkezler:
            merkezler[eksen] = eksen_ses_merkezi(conn, calisma_id, eksen)
        merkez = merkezler[eksen]
        if not merkez:
            continue
        uzaklik, boyut, _ = aday_uzakligi(
            stemler[stemler["album_id"] == satir.aday_id], merkez, olcek
        )
        if uzaklik is not None and boyut >= 5:
            kayitlar.append({"karar": satir.karar, "uzaklik": uzaklik})

    if not kayitlar:
        return pd.DataFrame()
    cerceve = pd.DataFrame(kayitlar)
    ozet = cerceve.groupby("karar")["uzaklik"].agg(["count", "median"]).reset_index()
    return ozet[ozet["count"] >= 3].round(3)


def ozet_cumleleri(isabet: pd.DataFrame) -> list[str]:
    """Ölçümü cümleye çevir — şablon, LLM yok (K2).

    Sayıya güvenilmeyecek kadar az veri varsa cümle KURULMAZ. "Bu strateji
    %100 isabetli" demek 1/1'de yanlış bilgi vermektir.
    """
    cumleler = []
    for satir in isabet.itertuples():
        # Asgari n şart. İlk sürümde yalnız `kesif_ust < 0.75` aranıyordu ve
        # tek kararlık bir strateji (n=1, üst sınır 0.73) on kararlık bir
        # stratejiyle aynı alarmı alıyordu — bu modülün baştan kaçınmak için
        # yazıldığı hatanın ta kendisi.
        if satir.toplam >= ASGARI_N and satir.zaten_biliyorum and satir.kesif_ust < 0.75:
            cumleler.append(
                f"**{satir.strateji}** sana çoğunlukla bildiğin şeyleri getiriyor: "
                f"{satir.toplam} karardan {satir.zaten_biliyorum}'i «zaten biliyorum». "
                f"Keşif oranı %{satir.kesif_orani*100:.0f} "
                f"(%{satir.kesif_alt*100:.0f}–%{satir.kesif_ust*100:.0f}). "
                "Zevk hatası değil, KEŞİF hatası — asıl sorun bu."
            )
        if satir.zevk_n >= ASGARI_N and satir.zevk_alt > 0.5:
            cumleler.append(
                f"**{satir.strateji}** zevkini tutturuyor: {satir.zevk_n} kararda "
                f"%{satir.zevk_isabeti*100:.0f} beğeni "
                f"(alt sınır %{satir.zevk_alt*100:.0f})."
            )
    if not cumleler:
        cumleler.append(
            "Henüz güvenilir bir sonuç çıkaracak kadar geri bildirim yok. "
            "Wilson alt sınırları geniş — birkaç karar daha gerekiyor."
        )
    return cumleler


# --------------------------------------------------------------------------- #
# Döngüyü kapatma — kararlar sıralamayı değiştirir
# --------------------------------------------------------------------------- #

#: Geri bildirimin sıralamayı kaydırabileceği azami miktar, aday skorlarının
#: KENDİ standart sapması cinsinden. 0,5 σ görünür ama baskın değil.
#:
#: Bilerek küçük. Şu an 3 «beğendim» ve 3 «tutmadı» var; bu, etkiyi ölçmeye
#: yetmez (K19). Katsayı, sinyal güçlenene kadar kararların sıralamayı
#: DEVİRMESİNİ değil, ETKİLEMESİNİ sağlıyor. Ölçüm mümkün olduğunda
#: (`python/degerlendirme.py`) süpürülüp yeniden seçilecek.
ETKI_TAVANI = 0.5

#: Etkinin görünmesi için gereken asgari benzerlik. Altındaki adaylar
#: "benziyor" sayılmaz; herkese küçük bir itki vermek sıralamayı değiştirmez,
#: yalnız gürültü ekler.
ASGARI_BENZERLIK = 0.02


def yargilanan_sanatcilar(
    conn: sqlite3.Connection, calisma_id: str | None = None,
) -> dict[str, set[str]]:
    """{"begendim": {anahtar...}, "tutmadi": {...}} — sanatçı düzeyinde.

    Karar albüm/parça üzerine veriliyor ama tercih SANATÇIYA ait: bir albümü
    beğendiysen o sanatçının başka işi de ilgini çeker. Aynı gerekçe
    `bilinen_sanatcilar`'da da var.
    """
    from python.metin import normalize_esleme

    sonuc: dict[str, set[str]] = {"begendim": set(), "tutmadi": set()}
    sorgu = """
        SELECT f.karar, a.artist
          FROM feedback f
          JOIN adaylar a ON a.aday_id = f.aday_id AND a.calisma_id = f.calisma_id
         WHERE f.karar IN ('begendim', 'tutmadi')
    """
    parametre: tuple = ()
    if calisma_id:
        sorgu += " AND f.calisma_id = ?"
        parametre = (calisma_id,)
    try:
        satirlar = conn.execute(sorgu, parametre).fetchall()
    except Exception:
        return sonuc
    for karar, ad in satirlar:
        if ad:
            sonuc[karar].add(normalize_esleme(ad))
    return sonuc


def yakinlik_etkisi(
    conn: sqlite3.Connection, calisma_id: str | None = None,
) -> dict[str, tuple[float, str]]:
    """{aday sanatçı anahtarı: (etki, gerekçe)} — kararlardan türeyen kayma.

    DÖNGÜYÜ KAPATAN ŞEY BU. Şimdiye kadar kararlar yalnız kaydediliyordu;
    sıralamaya tek etkisi "bildiklerimi geri at" kutusuydu.

    Yöntem: beğendiğin sanatçıya CLAP uzayında yakın adaylar yukarı,
    tutmadığına yakın olanlar aşağı. Etki = en_yakın(beğendiğin) −
    en_yakın(tutmadığın), [-1, +1]'e ölçeklenmiş.

    NEDEN CLAP, ÇALMA LİSTESİ DEĞİL: `liste_birlikteligi` yalnız
    KÜTÜPHANE↔aday bağı taşıyor; iki adayın birbirine yakınlığını söylemiyor.
    Beğendiğin sanatçı da bir aday olduğu için o tablo burada kullanılamaz.

    ÖLÇÜLMEDİ ve bu yazılmalı: n=3 beğendim, n=3 tutmadı. K19 "ölçülmeden
    üretime girmez" diyor; buradaki istisna bilinçli ve bedeli `ETKI_TAVANI`
    ile sınırlandı — kararlar sıralamayı deviremez, yalnız kaydırır. Etki
    ölçülebilir hâle geldiğinde katsayı süpürülecek.
    """
    import numpy as np

    from python.metin import normalize_esleme
    from python.ses_kume import havuz_gomuleri

    yargi = yargilanan_sanatcilar(conn, calisma_id)
    if not yargi["begendim"] and not yargi["tutmadi"]:
        return {}

    try:
        kayitlar, A = havuz_gomuleri(conn)
    except Exception:
        return {}
    if not kayitlar or A.size == 0:
        return {}

    # Sanatçı başına gömüler. Aynı sanatçının birden çok parçası olabilir;
    # en yakın olanı kullanıyoruz, ortalama almıyoruz — ortalama, çok yönlü
    # bir sanatçının hiçbir yönüne benzemeyen bir nokta üretir (K4 ile aynı
    # gerekçe).
    satir_sanatci = [normalize_esleme(k["sanatci"]) for k in kayitlar]
    indeks: dict[str, list[int]] = {}
    for i, anahtar in enumerate(satir_sanatci):
        indeks.setdefault(anahtar, []).append(i)

    def _blok(anahtarlar: set[str]) -> np.ndarray | None:
        satirlar = [i for a in anahtarlar for i in indeks.get(a, [])]
        return A[satirlar] if satirlar else None

    artı, eksi = _blok(yargi["begendim"]), _blok(yargi["tutmadi"])
    if artı is None and eksi is None:
        return {}

    okunur = {normalize_esleme(k["sanatci"]): k["sanatci"] for k in kayitlar}
    ham: dict[str, tuple[float, str]] = {}
    for anahtar, satirlar in indeks.items():
        if anahtar in yargi["begendim"] or anahtar in yargi["tutmadi"]:
            continue  # kendi kararı zaten var
        V = A[satirlar]
        iyi = float((V @ artı.T).max()) if artı is not None else 0.0
        kotu = float((V @ eksi.T).max()) if eksi is not None else 0.0
        fark = iyi - kotu
        if abs(fark) < ASGARI_BENZERLIK:
            continue
        if fark > 0:
            kaynak = max(yargi["begendim"],
                         key=lambda a: float((V @ A[indeks[a]].T).max())
                         if indeks.get(a) else -9)
            gerekce = f"👍 dediğin «{okunur.get(kaynak, kaynak)}» ile aynı sesten"
        else:
            kaynak = max(yargi["tutmadi"],
                         key=lambda a: float((V @ A[indeks[a]].T).max())
                         if indeks.get(a) else -9)
            gerekce = f"👎 dediğin «{okunur.get(kaynak, kaynak)}» ile aynı sesten"
        ham[anahtar] = (fark, gerekce)

    if not ham:
        return {}
    # [-1, +1]'e ölçekle: en büyük mutlak fark 1 olsun.
    en_buyuk = max(abs(f) for f, _ in ham.values()) or 1.0
    return {a: (f / en_buyuk, g) for a, (f, g) in ham.items()}
