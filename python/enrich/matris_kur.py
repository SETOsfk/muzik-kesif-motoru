"""Dört bloğu birleştirip kümelemeye giren albüm × öznitelik matrisini yaz.

Bloklar (mimari.md):
  kredi   — sık geçen müzisyenler için ikili gösterge (albümde çaldı mı)
  sahne   — ülke, on yıllık dönem (label çıkarıldı: dağıtım anlaşması müzikal
            yakınlık değildir)
  etiket  — ağırlıklı tür/alt tür vektörü
  ses     — librosa özetleri

Blok içi normalizasyon:
  kredi / sahne / etiket → satır bazında L2. Gerekçe: 40 kredisi belgelenmiş bir
      albüm, 4 kredisi olan albümden 10 kat "daha fazla" değildir; ham sayım
      kullanılırsa mesafeyi albümün Discogs'ta ne kadar iyi belgelendiği belirler,
      müzikal yakınlık değil.
  ses → sütun bazında ROBUST z (medyan / IQR). Tempo ve spektral merkezde aykırı
      değer olağan; ortalama/sd bunlara duyarlı.

Seyreklik eşiği: bir öznitelik en az `--min-album` albümde geçmiyorsa atılır.
Tek albümde geçen müzisyen/etiket hiçbir albüm çiftini birbirine yaklaştırmaz,
sadece boyutu şişirir — FCM üyelikleri yüksek boyutta 1/c'ye yakınsıyordu (K3).

Blok ağırlıkları burada UYGULANMAZ; R/config.R'ye bırakılır (kümeleme kararı).
Sütun adları `blok__ad` biçiminde, R tarafı blokları buradan ayırır.

Çıktı:
  data/ozellikler.parquet       albüm × öznitelik matrisi
  data/ozellikler_sozluk.csv    sütun sözlüğü (blok, ham ad, kaç albümde geçiyor)

Kullanım:
    python -m python.enrich.matris_kur
    python -m python.enrich.matris_kur --min-album 3 --cikti data/ozellikler.parquet
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from python.db import VARSAYILAN_DB, baglan
from python.enrich.rol_eslemesi import ENSTRUMAN_ROLLERI, URETIM_ROLLERI
from python.metin import normalize_esleme

VARSAYILAN_CIKTI = Path("data/ozellikler.parquet")
SES_SUTUNLARI = (
    "tempo_medyan",
    "tempo_iqr",
    "dinamik_aralik",
    "nabiz_netligi",
    "vurus_degiskenligi",
    "spektral_merkez",
)


# --------------------------------------------------------------------------- #
# Bloklar
# --------------------------------------------------------------------------- #

def _seyrekleri_at(cerceve: pd.DataFrame, min_album: int) -> pd.DataFrame:
    """En az `min_album` albümde sıfırdan farklı olmayan sütunları at."""
    if cerceve.empty:
        return cerceve
    kapsam = (cerceve != 0).sum(axis=0)
    return cerceve.loc[:, kapsam >= min_album]


def _l2_normalize(cerceve: pd.DataFrame) -> pd.DataFrame:
    """Satır bazında L2. Tamamı sıfır olan satır sıfır kalır (bölme yok)."""
    if cerceve.empty:
        return cerceve
    normlar = (cerceve**2).sum(axis=1) ** 0.5
    normlar = normlar.replace(0, 1.0)
    return cerceve.div(normlar, axis=0)


def kredi_blogu(
    conn: sqlite3.Connection,
    albumler: pd.Index,
    min_album: int,
    roller: frozenset[str] | None = None,
) -> pd.DataFrame:
    """Müzisyen başına ikili gösterge.

    `roller` verilirse yalnızca o rol ailesi alınır (icracı / üretim ayrımı).
    """
    krediler = pd.read_sql_query("SELECT album_id, person_name, role FROM credits", conn)
    if krediler.empty:
        return pd.DataFrame(index=albumler)
    if roller is not None:
        krediler = krediler[krediler["role"].isin(roller)]
    if krediler.empty:
        return pd.DataFrame(index=albumler)

    # Aynı kişi MusicBrainz'de ve Discogs'ta ayrı person_id ile gelir; iki kaynağı
    # birleştiren tek ortak alan isimdir. Gruplama normalize edilmiş ad üzerinden:
    # düz kesme ile kıvrık kesme ("Brendan O'Brien" / "Brendan O’Brien") aksi halde
    # iki ayrı müzisyen olur ve ikisi de eşiğin altında kalıp matristen düşer.
    krediler["ad"] = krediler["person_name"].str.strip()
    krediler = krediler[krediler["ad"] != ""]
    krediler["anahtar"] = krediler["ad"].map(normalize_esleme)
    krediler = krediler[krediler["anahtar"] != ""]
    if krediler.empty:
        return pd.DataFrame(index=albumler)

    gorunen_ad = krediler.groupby("anahtar")["ad"].first()

    matris = (
        pd.crosstab(krediler["album_id"], krediler["anahtar"])
        .gt(0)
        .astype(float)
        .reindex(albumler, fill_value=0.0)
        .rename(columns=gorunen_ad)
    )
    return _seyrekleri_at(matris, min_album)


def sahne_blogu(conn: sqlite3.Connection, albumler: pd.Index, min_album: int) -> pd.DataFrame:
    """Ülke, label ve on yıllık dönem için tek-sıcak (one-hot) göstergeler."""
    albom = pd.read_sql_query(
        "SELECT album_id, country, label, year FROM albums", conn
    ).set_index("album_id")
    albom = albom.reindex(albumler)

    # label ÇIKARILDI (kullanıcı kararı, 2026-08-11): plak şirketi müzikal yakınlık
    # göstermiyor — aynı label'dan çıkan iki albümün ortak yanı dağıtım anlaşması.
    parcalar = []
    for alan, onek in (("country", "ulke"),):
        seri = albom[alan].fillna("").str.strip()
        seri = seri[seri != ""]
        if not seri.empty:
            kukla = pd.get_dummies(seri, prefix=onek, prefix_sep=":").astype(float)
            parcalar.append(kukla.reindex(albumler, fill_value=0.0))

    yil = pd.to_numeric(albom["year"], errors="coerce")
    donem = (yil // 10 * 10).dropna().astype(int).astype(str) + "lar"
    if not donem.empty:
        parcalar.append(
            pd.get_dummies(donem, prefix="donem", prefix_sep=":")
            .astype(float)
            .reindex(albumler, fill_value=0.0)
        )

    if not parcalar:
        return pd.DataFrame(index=albumler)
    return _seyrekleri_at(pd.concat(parcalar, axis=1), min_album)


def etiket_blogu(conn: sqlite3.Connection, albumler: pd.Index, min_album: int) -> pd.DataFrame:
    etiketler = pd.read_sql_query("SELECT album_id, tag, agirlik FROM tags", conn)
    if etiketler.empty:
        return pd.DataFrame(index=albumler)
    matris = (
        etiketler.pivot_table(
            index="album_id", columns="tag", values="agirlik", aggfunc="sum", fill_value=0.0
        )
        .reindex(albumler, fill_value=0.0)
        .astype(float)
    )
    return _seyrekleri_at(matris, min_album)


def ses_blogu(conn: sqlite3.Connection, albumler: pd.Index) -> tuple[pd.DataFrame, int]:
    """Robust z (medyan/IQR). Eksik albümler 0 = medyan ile doldurulur."""
    ses = pd.read_sql_query(
        f"SELECT album_id, {', '.join(SES_SUTUNLARI)} FROM audio_features", conn
    )
    if ses.empty:
        return pd.DataFrame(index=albumler), len(albumler)

    ses = ses.set_index("album_id").reindex(albumler).astype(float)
    eksik = int(ses[SES_SUTUNLARI[0]].isna().sum())

    for sutun in SES_SUTUNLARI:
        degerler = ses[sutun]
        medyan = degerler.median()
        ceyrekler = degerler.quantile([0.25, 0.75])
        iqr = float(ceyrekler.loc[0.75] - ceyrekler.loc[0.25])
        if iqr <= 0:  # sabit sütun — bilgi taşımıyor
            ses[sutun] = 0.0
            continue
        ses[sutun] = (degerler - medyan) / iqr

    # Eksik albüm medyanda (0) durur; mesafeyi ne kendine ne başkasına bozar.
    ses = ses.fillna(0.0)

    # Blok enerjisini diğer üç blokla karşılaştırılabilir yap. Onlar satır-L2 ile
    # normalize edildiği için her satırın enerjisi tam 1; ses bloğu ham z olarak
    # bırakılırsa 5 sütunla toplam enerjinin yarısını kapar ve blok ağırlıkları
    # söyledikleri şeyi yapmaz. Satır bazında normalize etmek YANLIŞ olurdu:
    # medyana yakın (yani bilgi taşımayan) bir albümün değerlerini yapay olarak
    # büyütürdü. Bu yüzden blok tek bir katsayıyla ölçeklenir — blok içi göreli
    # mesafeler korunur, blok toplamı diğerleriyle aynı mertebeye iner.
    normlar = (ses**2).sum(axis=1) ** 0.5
    dolu = normlar[normlar > 0]
    if len(dolu):
        ses = ses / float(dolu.mean())

    return ses, eksik


# --------------------------------------------------------------------------- #
# Birleştirme
# --------------------------------------------------------------------------- #

def matris_kur(conn: sqlite3.Connection, min_album: int = 2) -> tuple[pd.DataFrame, pd.DataFrame]:
    albumler = pd.Index(
        [
            satir["album_id"]
            for satir in conn.execute("SELECT album_id FROM albums ORDER BY album_id")
        ],
        name="album_id",
    )
    if albumler.empty:
        raise SystemExit("albums tablosu boş — önce kutuphane_tara.py çalıştırılmalı.")

    # Eşik öncesi sütun sayısı: "veri hiç yok" ile "eşik hepsini eledi" ayrımı için.
    # Kredi ikiye ayrılır: kim ÇALDI (tez bu) ve kim ÜRETTİ. Ayrılmazsa
    # mastering mühendisi projenin en güçlü bağlantısı olur — Bob Ludwig bu
    # kütüphanede 15 albümde geçiyor ve o albümlerin müzikal ortak yanı yok.
    ham_bloklar = {
        "kredi": kredi_blogu(conn, albumler, 1, ENSTRUMAN_ROLLERI),
        "uretim": kredi_blogu(conn, albumler, 1, URETIM_ROLLERI),
        "sahne": sahne_blogu(conn, albumler, 1),
        "etiket": etiket_blogu(conn, albumler, 1),
    }
    bloklar = {
        ad: _l2_normalize(_seyrekleri_at(blok, min_album))
        for ad, blok in ham_bloklar.items()
    }
    ses, ses_eksik = ses_blogu(conn, albumler)
    ham_bloklar["ses"] = ses
    bloklar["ses"] = ses

    parcalar = []
    sozluk_satirlari = []
    for blok_adi, blok in bloklar.items():
        if blok.empty or blok.shape[1] == 0:
            ham_sutun = ham_bloklar[blok_adi].shape[1]
            if ham_sutun:
                print(
                    f"UYARI: '{blok_adi}' bloğunun {ham_sutun} özniteliğinin tamamı "
                    f"--min-album {min_album} eşiğine takıldı (hiçbiri {min_album} "
                    "albümde birden geçmiyor).",
                    file=sys.stderr,
                )
            else:
                print(
                    f"UYARI: '{blok_adi}' bloğunda hiç veri yok — ilgili "
                    "zenginleştirme adımı çalıştırılmamış olabilir.",
                    file=sys.stderr,
                )
            continue
        adlandirilmis = blok.copy()
        adlandirilmis.columns = [f"{blok_adi}__{sutun}" for sutun in blok.columns]
        parcalar.append(adlandirilmis)
        for ham_ad, yeni_ad in zip(blok.columns, adlandirilmis.columns):
            sozluk_satirlari.append(
                {
                    "sutun": yeni_ad,
                    "blok": blok_adi,
                    "ham_ad": ham_ad,
                    "kapsam": int((blok[ham_ad] != 0).sum()),
                }
            )

    if not parcalar:
        raise SystemExit("Hiçbir blok dolu değil — zenginleştirme adımları çalıştırılmalı.")

    matris = pd.concat(parcalar, axis=1)
    matris.index.name = "album_id"
    sozluk = pd.DataFrame(sozluk_satirlari)
    sozluk.attrs["ses_eksik"] = ses_eksik
    return matris, sozluk


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Öznitelik matrisini kur.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--cikti", type=Path, default=VARSAYILAN_CIKTI)
    ayristirici.add_argument(
        "--min-album", type=int, default=2,
        help="bir öznitelik en az kaç albümde geçmeli (varsayılan 2)",
    )
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        matris, sozluk = matris_kur(conn, min_album=args.min_album)
    finally:
        conn.close()

    args.cikti.parent.mkdir(parents=True, exist_ok=True)
    matris.reset_index().to_parquet(args.cikti, index=False)
    sozluk_yolu = args.cikti.with_name(args.cikti.stem + "_sozluk.csv")
    sozluk.to_csv(sozluk_yolu, index=False)

    print(f"Matris: {matris.shape[0]} albüm × {matris.shape[1]} öznitelik → {args.cikti}")
    for blok, grup in sozluk.groupby("blok", sort=False):
        print(f"  {blok:<7}: {len(grup):>4} sütun (ortalama kapsam {grup['kapsam'].mean():.1f} albüm)")
    ses_eksik = sozluk.attrs.get("ses_eksik", 0)
    if ses_eksik:
        print(f"  NOT: {ses_eksik} albümde ses özniteliği yok, medyanla dolduruldu.")
    print(f"Sütun sözlüğü: {sozluk_yolu}")

    yogunluk = float((matris != 0).to_numpy().mean())
    print(f"Doluluk oranı: %{yogunluk * 100:.1f} (seyreklik FCM için kritik — bkz. K3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
