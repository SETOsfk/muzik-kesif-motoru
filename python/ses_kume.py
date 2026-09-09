"""Ses kümeleri — türü ETİKETTEN değil, sesin kendisinden keşfet.

Kullanıcının cümlesi: "biz de müzik genrelerine takılı kalmayalım. gerekirse
tüm müzikleri analiz edip yeni genreler keşfedelim."

## Neden mevcut kümelemeden ayrı

`python/kumeleme/` kredi + tür etiketi + sahne + ses bloklarından kurulan bir
matriste çalışıyor; ağırlıklı olarak METADATA. Buradaki kümeleme yalnız CLAP
gömüsünde, yani sesin kendisinde.

İkisi AYNI ŞEYİ GÖRMÜYOR — ölçüldü, uyum (ARI) 0.073. Bu bir çelişki değil,
iki ayrı bakış: biri "kim çalmış, nasıl etiketlenmiş", diğeri "kulağa nasıl
geliyor". Ölçülen örnek: ses kümesi 6'da Masayoshi Takanaka, Casiopea ve Plini
yan yana — hiçbir tür etiketi kullanılmadan, çünkü üçü de aynı sesi çıkarıyor.

## Boyut indirgeme şart

512 boyutta siluet 0.10'da takılıyor (yüksek boyutta mesafe yoğunlaşması —
K3'teki FCM gerekçesinin aynısı). PCA 16 boyuta indirince 0.168'e çıkıyor.
İndirgeme burada bir hile değil, gereklilik.

## Ne için kullanılıyor

Kullanıcının asıl isteği: "j-fusion önerisi istediğimde elimde olmayan bir
öneri gelsin." Ses kümesi tam bunu veriyor — kümeyi seç, o sese en yakın ama
SENDE OLMAYAN kayıtları getir. Havuz: aday albümler + çalma listesi parçaları.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from python.db import VARSAYILAN_DB, baglan
from python.etiket_clap import GOMU_KLASOR, PARCA_GOMU

#: PCA hedef boyutu. 16'da siluet en yüksek (0.168); 32 ve 64'te düşüyor.
PCA_BOYUT = 16

#: Küme sayısı. Kullanıcının 302 albümü için 12; küme başına ~25 albüm.
KUME_SAYISI = 12


def kutuphane_gomuleri(conn: sqlite3.Connection) -> tuple[list[str], np.ndarray]:
    ad = {r[0] for r in conn.execute("SELECT album_id FROM albums")}
    dosyalar = [f for f in sorted(GOMU_KLASOR.glob("*.npy")) if f.stem in ad]
    if not dosyalar:
        return [], np.zeros((0, 512), dtype="float32")
    return [f.stem for f in dosyalar], np.stack([np.load(f) for f in dosyalar])


def kumele(conn: sqlite3.Connection, *, kume_sayisi: int = KUME_SAYISI) -> pd.DataFrame:
    """Kütüphaneyi ses uzayında kümele. album_id → küme + merkeze uzaklık."""
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA

    kimlik, A = kutuphane_gomuleri(conn)
    if len(kimlik) < kume_sayisi * 2:
        return pd.DataFrame()

    pca = PCA(n_components=min(PCA_BOYUT, A.shape[0] - 1), random_state=0)
    X = pca.fit_transform(A)
    km = KMeans(n_clusters=kume_sayisi, n_init=12, random_state=0).fit(X)

    uzaklik = np.linalg.norm(X - km.cluster_centers_[km.labels_], axis=1)
    return pd.DataFrame({
        "album_id": kimlik, "kume": km.labels_, "merkez_uzakligi": uzaklik,
    })


def kume_adi(conn: sqlite3.Connection, uyeler: pd.DataFrame, adet: int = 3) -> str:
    """Kümenin adı, merkezine EN YAKIN albümlerden.

    Etiket uydurulmuyor: küme "Casiopea · Takanaka · Plini gibi" diye
    anlatılıyor. Kullanıcı isterse kendi adını verir — küme isimlendirmede
    olduğu gibi (K4 gerekçesi: gösterilen şey, hesabın verdiği karar olmalı).
    """
    ad = {r[0]: f"{r[1]}" for r in conn.execute(
        "SELECT album_id, artist FROM albums")}
    yakin = uyeler.nsmallest(adet * 2, "merkez_uzakligi")
    gorulen, isimler = set(), []
    for album_id in yakin["album_id"]:
        sanatci = ad.get(album_id, "?")
        if sanatci not in gorulen:
            gorulen.add(sanatci)
            isimler.append(sanatci)
        if len(isimler) >= adet:
            break
    return " · ".join(isimler)


def havuz_gomuleri(conn: sqlite3.Connection) -> tuple[list[dict], np.ndarray]:
    """Sende OLMAYAN her şey: aday albümler + çalma listesi parçaları."""
    kayitlar, vektorler = [], []

    aday_ad = {
        r[0]: (r[1], r[2], r[3]) for r in conn.execute(
            "SELECT aday_id, artist, title, onizleme_url FROM adaylar")
    }
    for dosya in sorted(GOMU_KLASOR.glob("*.npy")):
        veri = aday_ad.get(dosya.stem)
        if veri:
            kayitlar.append({"kimlik": dosya.stem, "sanatci": veri[0],
                             "ad": veri[1], "onizleme": veri[2],
                             "tur": "album"})
            vektorler.append(np.load(dosya))

    parca_ad = {
        int(r[0]): (r[1], r[2]) for r in conn.execute(
            "SELECT parca_id, sanatci, parca FROM liste_parca "
            "WHERE parca_id IS NOT NULL")
    }
    sahip = {
        r[0].lower() for r in conn.execute("SELECT DISTINCT artist FROM albums")
    }
    for dosya in sorted(PARCA_GOMU.glob("*.npy")):
        try:
            veri = parca_ad.get(int(dosya.stem))
        except ValueError:
            continue
        if not veri or veri[0].lower() in sahip:
            continue
        kayitlar.append({"kimlik": dosya.stem, "sanatci": veri[0],
                         "ad": veri[1], "onizleme": None, "tur": "parca"})
        vektorler.append(np.load(dosya))

    if not vektorler:
        return [], np.zeros((0, 512), dtype="float32")
    return kayitlar, np.stack(vektorler)


def kumeye_yakinlar(
    conn: sqlite3.Connection, uyeler: pd.DataFrame, *, adet: int = 20
) -> list[dict]:
    """Bu sese en yakın ama SENDE OLMAYAN kayıtlar.

    Kümenin merkezine değil ÜYELERİNE yakınlık: merkez, heterojen bir kümeyi
    ortalayıp hiçbir albüme benzemeyen bir nokta üretiyor. Üyeye yakınlık hem
    daha doğru hem açıklanabilir — hangi albümüne benzediğini yazabiliyoruz.

    Hubness düzeltmesi: adayın TÜM kütüphaneye ortalama benzerliği çıkarılıyor.
    Ham kosinüste bazı kayıtlar her şeye yakın çıkıyor (ölçüldü, bkz.
    `etiket_clap.benzer_adaylar`).
    """
    kimlik, A_tum = kutuphane_gomuleri(conn)
    indeks = {k: i for i, k in enumerate(kimlik)}
    satirlar = [indeks[a] for a in uyeler["album_id"] if a in indeks]
    if not satirlar:
        return []
    A_uye = A_tum[satirlar]

    havuz, H = havuz_gomuleri(conn)
    if not havuz:
        return []

    taban = (H @ A_tum.T).mean(axis=1, keepdims=True)
    S = H @ A_uye.T - taban
    en_yakin, skor = S.argmax(axis=1), S.max(axis=1)

    ad = {r[0]: f"{r[1]} — {r[2]}" for r in conn.execute(
        "SELECT album_id, artist, title FROM albums")}

    # Aynı parça birden çok listede geçtiği için farklı kimliklerle iki kez
    # gömülmüş olabiliyor (ölçüldü: «Green Onions» iki kez çıkıyordu).
    # Sanatçı+ad ikilisiyle tekilleştir, en yüksek skorlusu kalsın.
    from python.metin import normalize_esleme

    sonuc, gorulen = [], set()
    for i in np.argsort(-skor):
        kayit = dict(havuz[i])
        anahtar = (normalize_esleme(kayit["sanatci"]),
                   normalize_esleme(kayit["ad"] or ""))
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        kayit["skor"] = float(skor[i])
        kayit["benzedigi"] = ad.get(kimlik[satirlar[en_yakin[i]]], "?")
        sonuc.append(kayit)
        if len(sonuc) >= adet:
            break
    return sonuc


def yaz(conn: sqlite3.Connection, kumeler: pd.DataFrame) -> int:
    with conn:
        conn.execute("DELETE FROM ses_kumesi")
        conn.executemany(
            "INSERT INTO ses_kumesi (album_id, kume, merkez_uzakligi) "
            "VALUES (?,?,?)",
            kumeler[["album_id", "kume", "merkez_uzakligi"]].itertuples(
                index=False, name=None),
        )
    return len(kumeler)


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--kume", type=int, default=KUME_SAYISI)
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        kumeler = kumele(conn, kume_sayisi=args.kume)
        if kumeler.empty:
            print("yeterli CLAP gömüsü yok")
            return 1
        print(f"{yaz(conn, kumeler)} albüm kümelendi\n")
        for kume, grup in kumeler.groupby("kume"):
            print(f"  KÜME {kume} ({len(grup)}): {kume_adi(conn, grup)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
