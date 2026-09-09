"""Ölçüt denetimi: hangi stem özniteliği kendi başına bilgi taşıyor?

Bu projede şimdiye kadar BEŞ öznitelik ölçülüp elendi (ritmik_karmasiklik,
tempogram entropisi, HPSS+senkop, duzluk, tepe_orani). Hepsinin ortak hatası
aynıydı: birkaç satıra bakıp "mantıklı görünüyor" demek. Bu modül o kararı
veriye bağlar ve iki soruyu ayrı ayrı sorar.

**1. Ayırt ediyor mu?** Sabit çıkan öznitelik hiçbir işe yaramaz. Ölçüt
(p95−p5)/|medyan|; IQR değil, çünkü bazı öznitelikler işini KUYRUKTA yapar
(bkz. `YAYILIM_ESIGI`). `ritmik_karmasiklik` tüm türlerde 0.878–0.891
çıkmıştı — buradan geçemezdi.

**2. Kendi başına bilgi taşıyor mu?** Asıl tuzak bu. Bir öznitelik ayırt edebilir
ama zaten elimizde olan başka bir özniteliğin kopyası olabilir. `harmonik_pay`
sekiz sanatçıda distorsiyonu doğru sıralamıştı, ama sıralama `parlaklik`
sıralamasıyla neredeyse aynıydı — "distorsiyon ölçüyorum" mu diyordu yoksa
"parlaklık ölçüyorum" mu, ayrılamıyordu.

Ayrım kısmi korelasyonla yapılır: adayı diğer TÜM özniteliklere regresyon
edip artığa bakarız. Artığın varyans payı (1 - R²) düşükse aday, ölçüt
kümesindeki diğerlerinin doğrusal bileşiminden ibarettir; boyut ekler, bilgi
eklemez. FCM'de bu zararlıdır: aynı bilgiyi iki sütunda taşımak o eksene
sessizce çift ağırlık verir (K3'teki boyut indirgeme gerekçesiyle aynı mesele).

Kullanım:
    python -m python.enrich.olcut_denetimi --stem other
    python -m python.enrich.olcut_denetimi            # dört stem birden
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from python.db import VARSAYILAN_DB, baglan

#: Artık varyans payı bunun altındaysa öznitelik "artık bilgi" sayılır.
#: 0.30 = diğer sütunlar adayın varyansının %70'ini zaten açıklıyor.
ARTIK_ESIGI = 0.30

#: Yayılım bunun altındaysa öznitelik pratikte sabittir.
#: IQR/medyan DEĞİL, (p95-p5)/|medyan| kullanılıyor. Fark önemli: `izgara_entropi`
#: kütüphanenin çoğunda ~0.98'de toplanıyor (IQR/medyan = 0.018, "sabit" görünür)
#: ama işi zaten NADİR aykırıyı yakalamak — Eminem 0.755 ile programlanmış beat'i
#: oradan belli ediyor. IQR ölçütü bu ölçütü yanlışlıkla elerdi. Kuyruğu gören
#: bir yayılım ölçüsü gerekiyor.
YAYILIM_ESIGI = 0.05

#: Bileşimsel sütunlar: payları tanım gereği 1'e toplanır, yani biri diğer
#: ikisinin doğrusal fonksiyonudur ve artık payı sıfır çıkar. Bu bir keşif değil,
#: aritmetik zorunluluk — "artık" diye elenmemeleri gerekir. Kümeleme ölçütüne
#: girerken üçünden biri düşürülür (ya da log-oran dönüşümü uygulanır).
BILESIMSEL = (("tekme_payi", "trampet_payi", "zil_payi"),)


def _artik_payi(hedef: np.ndarray, digerleri: np.ndarray) -> float:
    """Hedefin, diğer sütunlara regresyonundan artan varyans payı = 1 - R².

    En küçük kareler `lstsq` ile; sabit terim eklenir. Diğer sütun yoksa
    hedef tanım gereği tamamen kendine ait, 1.0 döner.
    """
    if digerleri.size == 0 or digerleri.shape[1] == 0:
        return 1.0
    X = np.column_stack([np.ones(len(hedef)), digerleri])
    katsayi, *_ = np.linalg.lstsq(X, hedef, rcond=None)
    artik = hedef - X @ katsayi
    toplam = float(((hedef - hedef.mean()) ** 2).sum())
    if toplam <= 0:
        return 0.0
    return float((artik**2).sum() / toplam)


def denetle(cerceve: pd.DataFrame, sutunlar: list[str]) -> pd.DataFrame:
    """Her öznitelik için: kapsama, değişim katsayısı, artık varyans payı, karar."""
    # Kısmi korelasyon eksiksiz satır ister; ölçülemeyen alanları olan satırları
    # atmak yerine sütun medyanıyla dolduruyoruz ki n çökmesin. Doldurma
    # varyansı azaltır, yani bu test adayın LEHİNE değil ALEYHİNE yanlıdır —
    # buradan geçen öznitelik gerçekten geçmiştir.
    var = cerceve[sutunlar].astype(float)
    dolu = var.fillna(var.median())
    satirlar = []
    for sutun in sutunlar:
        seri = var[sutun].dropna()
        medyan = float(seri.median()) if len(seri) else float("nan")
        yayilim = (
            abs(float(seri.quantile(0.95) - seri.quantile(0.05)) / medyan)
            if len(seri) and np.isfinite(medyan) and medyan != 0.0
            else float("nan")
        )

        # Bileşimsel kardeşler regresyondan çıkarılır; yoksa artık payı tanım
        # gereği sıfır çıkar ve gerçek bir bulguymuş gibi görünür.
        kardesler = set()
        for grup in BILESIMSEL:
            if sutun in grup:
                kardesler |= set(grup)
        digerleri = [s for s in sutunlar if s != sutun and s not in kardesler]
        artik = _artik_payi(dolu[sutun].to_numpy(), dolu[digerleri].to_numpy())

        if len(seri) < 20:
            karar = "veri az"
        elif np.isfinite(yayilim) and yayilim < YAYILIM_ESIGI:
            karar = "ELE — sabit"
        elif artik < ARTIK_ESIGI:
            karar = "ELE — artık"
        else:
            karar = "tut"
        satirlar.append({
            "oznitelik": sutun,
            "n": len(seri),
            "medyan": round(medyan, 4) if np.isfinite(medyan) else None,
            "yayilim": round(yayilim, 3) if np.isfinite(yayilim) else None,
            "artik_pay": round(artik, 3),
            "karar": karar,
        })
    return pd.DataFrame(satirlar).sort_values("artik_pay")


def adimsal_ele(cerceve: pd.DataFrame, sutunlar: list[str]) -> tuple[list[str], list[tuple[str, float]]]:
    """Geriye doğru adımsal eleme: her turda EN artık olan tek sütunu at.

    Hepsini aynı anda elemek yanlış sonuç veriyor. Ölçüldü: ilk turda `zil_payi`
    artık payı 0.234 ile elenecek görünüyordu — oysa `zil_payi` müzikal olarak
    doğrulanmış bir ölçüt (Meshuggah %62 ride ağırlığı buradan çıkmıştı).
    Artıklığı `parlaklik` ve `zcr` ile paylaşmasındandı ve o ikisi zaten
    eleniyordu. Zil parlaktır — üçü aynı şeyi farklı isimle söylüyordu.

    Bir sütun atılınca kalanların artık payı yeniden hesaplanır; böylece
    "başkasının kopyası olduğu için elenen" ile "kopyalandığı için eleyen"
    karışmaz. Tur başına tek eleme, eşiğin üstüne çıkılana kadar.
    """
    kalan = list(sutunlar)
    elenen: list[tuple[str, float]] = []
    while len(kalan) > 2:
        sonuc = denetle(cerceve, kalan)
        en_artik = sonuc.iloc[0]
        if en_artik["artik_pay"] >= ARTIK_ESIGI or not str(en_artik["karar"]).startswith("ELE"):
            break
        kalan.remove(en_artik["oznitelik"])
        elenen.append((str(en_artik["oznitelik"]), float(en_artik["artik_pay"])))
    return kalan, elenen


def stem_denetimi(conn, stem: str) -> pd.DataFrame | None:
    # Yalnız KÜTÜPHANE albümleri: aday ölçümleri farklı bir dağılımdan geliyor
    # (30 sn önizleme klibi, tam albüm değil) ve ikisini karıştırmak eşikleri
    # kaydırır.
    cerceve = pd.read_sql_query(
        "SELECT * FROM stem_profili WHERE stem = ? AND tur = 'album'",
        conn, params=(stem,),
    )
    if cerceve.empty:
        return None
    atla = {"album_id", "stem", "onizleme_url", "tur"}
    # SAYISAL OLMAYAN SÜTUN ELENMELİ. `tur` sonradan göçle eklendi ve
    # `SELECT *` onu öznitelik sanıp denetimi çökertti (2026-09-02).
    # Kara liste tek başına yetmez: bir sonraki metin sütunu yine sızar.
    sayisal = cerceve.select_dtypes(include="number").columns
    # Tamamen boş sütunlar bu stem'e ait değil (davulda perde, vokalde tekme).
    sutunlar = [
        s for s in sayisal
        if s not in atla and cerceve[s].notna().sum() >= max(10, 0.5 * len(cerceve))
    ]
    if len(sutunlar) < 2:
        return None
    return cerceve, sutunlar


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--stem", help="tek stem; boşsa dördü birden")
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        stemler = [args.stem] if args.stem else ["drums", "bass", "other", "vocals"]
        for stem in stemler:
            hazir = stem_denetimi(conn, stem)
            print(f"\n=== {stem} ===")
            if hazir is None:
                print("  yeterli veri yok")
                continue
            cerceve, sutunlar = hazir
            kalan, elenen = adimsal_ele(cerceve, sutunlar)
            print(denetle(cerceve, kalan).to_string(index=False))
            if elenen:
                print("  elenme sırası (geriye doğru adımsal):")
                for ad, pay in elenen:
                    print(f"    {ad:<16} artık payı {pay:.3f}")
            print(f"  → ÖLÇÜT KÜMESİ: {', '.join(sorted(kalan))}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
