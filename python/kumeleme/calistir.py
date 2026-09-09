"""Kümeleme boru hattı: matris → ağırlık → boyut indirgeme → FCM → stabilite → DB.

Sonuç `memberships` ve `clusters` tablolarına, `calisma_id` ile versiyonlanarak
yazılır. Eski çalışmalar silinmez: parametre değiştirip tekrar çalıştırdığında
ikisini karşılaştırabilirsin.

Deterministik: aynı matris + aynı ayar + aynı tohum = aynı sonuç. Bu bir K1/K2
gereği, kümelemenin tekrarlanabilir olması zorunlu.

Kullanım:
    python -m python.kumeleme.calistir
    python -m python.kumeleme.calistir --m 1.5 --c 3 8 --yontem umap
    python -m python.kumeleme.calistir --kuru        # yazmadan sadece rapor
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from python.db import baglan
from python.kumeleme.ayar import VARSAYILAN, Ayar
from python.kumeleme.boyut_indirgeme import blok_ozeti, bloklari_agirlikla, boyut_indir
from python.kumeleme.fcm import c_tara, en_iyi_c
from python.kumeleme.stabilite import bootstrap_jaccard
from python.kumeleme.temsilciler import kume_profili, ortusen_albumler, temsilci_sec


def matrisi_oku(yol: Path) -> pd.DataFrame:
    """Parquet (yoksa CSV) oku, album_id'yi indeks yap."""
    if yol.suffix == ".parquet" and yol.is_file():
        cerceve = pd.read_parquet(yol)
    else:
        csv_yolu = yol.with_suffix(".csv")
        if not csv_yolu.is_file():
            raise SystemExit(
                f"Matris bulunamadı: {yol}. Önce `python -m python.enrich.matris_kur`."
            )
        cerceve = pd.read_csv(csv_yolu)
    if "album_id" not in cerceve.columns:
        raise SystemExit("Matriste album_id sütunu yok.")
    return cerceve.set_index("album_id")


def calisma_kimligi(ayar: Ayar, c: int) -> str:
    damga = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"{damga}-c{c}-m{ayar.m:g}-{ayar.yontem}"


def temsilcileri_yaz(
    conn: sqlite3.Connection,
    calisma_id: str,
    album_ids: pd.Index,
    uyelik: np.ndarray,
    X: np.ndarray,
    sanatcilar: np.ndarray | None,
    ayar: Ayar,
) -> int:
    satirlar = []
    for kume in range(uyelik.shape[1]):
        secilenler = temsilci_sec(
            X, uyelik, kume,
            adet=ayar.temsilci_sayisi,
            ust_dilim=ayar.temsilci_ust_dilim,
            ayni_sanatci_cezasi=sanatcilar,
        )
        for sira, satir in enumerate(secilenler):
            satirlar.append(
                (calisma_id, kume, album_ids[satir], sira, float(uyelik[satir, kume]))
            )
    with conn:
        conn.executemany(
            """INSERT OR REPLACE INTO temsilciler
               (calisma_id, kume_id, album_id, sira, uyelik) VALUES (?,?,?,?,?)""",
            satirlar,
        )
    return len(satirlar)


def sonuclari_yaz(
    conn: sqlite3.Connection,
    calisma_id: str,
    album_ids: pd.Index,
    uyelik: np.ndarray,
    jaccard: np.ndarray,
    esik: float,
) -> None:
    with conn:
        conn.executemany(
            """INSERT OR REPLACE INTO clusters
               (kume_id, calisma_id, kullanici_adi, stabilite, stabil_mi)
               VALUES (?,?,?,?,?)""",
            [
                (kume, calisma_id, None, float(jaccard[kume]), int(jaccard[kume] >= esik))
                for kume in range(uyelik.shape[1])
            ],
        )
        conn.executemany(
            """INSERT OR REPLACE INTO memberships
               (album_id, kume_id, uyelik, calisma_id)
               VALUES (?,?,?,?)""",
            [
                (album_id, kume, float(uyelik[sira, kume]), calisma_id)
                for sira, album_id in enumerate(album_ids)
                for kume in range(uyelik.shape[1])
            ],
        )


def calistir(ayar: Ayar, *, kuru: bool = False, sessiz: bool = False) -> dict:
    yaz = (lambda *a, **k: None) if sessiz else print

    matris = matrisi_oku(ayar.matris)
    yaz(f"Matris: {matris.shape[0]} albüm × {matris.shape[1]} öznitelik")

    ozet = blok_ozeti(matris, ayar.blok_agirliklari)
    for _, satir in ozet.iterrows():
        yaz(
            f"  {satir['blok']:<7} {satir['sutun']:>4} sütun  ağırlık {satir['agirlik']:.2f}"
            f"  enerji payı %{satir['enerji_payi'] * 100:.1f}"
        )

    agirlikli = bloklari_agirlikla(matris, ayar.blok_agirliklari)
    indirgeme = boyut_indir(agirlikli, ayar)
    yaz(indirgeme.ozet())

    yaz(f"c taraması {ayar.c_araligi[0]}–{ayar.c_araligi[1]} (m={ayar.m:g})...")
    taramalar = c_tara(
        indirgeme.X,
        ayar.c_araligi,
        ayar.m,
        baslangic=ayar.baslangic,
        yineleme=ayar.yineleme,
        tolerans=ayar.tolerans,
        tohum=ayar.tohum,
    )
    if not taramalar:
        raise SystemExit("c taraması boş — albüm sayısı yetersiz olabilir.")

    # Her c için ucuz stabilite: K3'ün üçüncü ölçütü seçimin parçası olmalı,
    # sonradan yapılan bir kontrol değil.
    stabil_oranlar: dict[int, float] = {}
    yaz(f"  {'c':>3} {'Xie-Beni':>10} {'PE(norm)':>9} {'PC':>7} {'stabil':>9} {'en küçük':>9}")
    for tarama in taramalar:
        on_stabilite = bootstrap_jaccard(
            indirgeme.X,
            tarama.sonuc.keskin_atama(),
            tarama.c,
            ayar.m,
            tekrar=ayar.tarama_bootstrap,
            esik=ayar.stabilite_esigi,
            tohum=ayar.tohum,
        )
        oran = float(on_stabilite.stabil_mi.mean())
        stabil_oranlar[tarama.c] = oran
        boyutlar = np.bincount(tarama.sonuc.keskin_atama(), minlength=tarama.c)
        yaz(
            f"  {tarama.c:>3} {tarama.xie_beni:>10.4f} "
            f"{tarama.partition_entropy:>9.4f} {tarama.partition_coefficient:>7.4f} "
            f"{int(on_stabilite.stabil_mi.sum()):>4}/{tarama.c:<4} {boyutlar.min():>9}"
        )

    secilen = en_iyi_c(taramalar, stabil_oranlar)
    yaz(
        f"Seçilen c = {secilen.c} — tüm kümeleri stabil olan adaylar arasında "
        f"Xie-Beni minimumu"
    )

    stabilite = bootstrap_jaccard(
        indirgeme.X,
        secilen.sonuc.keskin_atama(),
        secilen.c,
        ayar.m,
        tekrar=ayar.bootstrap,
        esik=ayar.stabilite_esigi,
        tohum=ayar.tohum,
    )
    yaz(stabilite.ozet())
    for kume in range(secilen.c):
        boyut = int((secilen.sonuc.keskin_atama() == kume).sum())
        damga = "stabil" if stabilite.stabil_mi[kume] else "KARARSIZ"
        yaz(f"  küme {kume}: {boyut:>3} albüm, Jaccard {stabilite.jaccard[kume]:.3f}  {damga}")

    calisma_id = calisma_kimligi(ayar, secilen.c)
    if not kuru:
        conn = baglan(ayar.db)
        try:
            sonuclari_yaz(
                conn, calisma_id, matris.index, secilen.sonuc.uyelik,
                stabilite.jaccard, ayar.stabilite_esigi,
            )
            # Temsilciler kümelemeyle birlikte donar: arayüz sonradan yeniden
            # hesaplarsa başka albümler gösterebilir (bkz. veri sözleşmesi).
            sanatcilar = (
                pd.read_sql_query("SELECT album_id, artist FROM albums", conn)
                .set_index("album_id")
                .reindex(matris.index)["artist"]
                .fillna("")
                .to_numpy()
            )
            adet = temsilcileri_yaz(
                conn, calisma_id, matris.index, secilen.sonuc.uyelik,
                indirgeme.X, sanatcilar, ayar,
            )
        finally:
            conn.close()
        yaz(f"Yazıldı: calisma_id = {calisma_id} ({adet} temsilci)")
    else:
        yaz("(kuru çalışma — veritabanına yazılmadı)")

    ortusen = ortusen_albumler(secilen.sonuc.uyelik)
    yaz(f"Birden fazla ekseni besleyen albüm: {len(ortusen)}")

    return {
        "calisma_id": calisma_id,
        "c": secilen.c,
        "xie_beni": secilen.xie_beni,
        "partition_entropy": secilen.partition_entropy,
        "uyelik": secilen.sonuc.uyelik,
        "jaccard": stabilite.jaccard,
        "indirgeme": indirgeme,
        "matris": matris,
        "taramalar": taramalar,
    }


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Bulanık kümeleme boru hattı.")
    ayristirici.add_argument("--matris", type=Path, default=VARSAYILAN.matris)
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN.db)
    ayristirici.add_argument("--m", type=float, default=VARSAYILAN.m)
    ayristirici.add_argument("--c", type=int, nargs=2, metavar=("ALT", "UST"))
    ayristirici.add_argument("--yontem", choices=("pca", "umap"), default=VARSAYILAN.yontem)
    ayristirici.add_argument("--bootstrap", type=int, default=VARSAYILAN.bootstrap)
    ayristirici.add_argument("--tohum", type=int, default=VARSAYILAN.tohum)
    ayristirici.add_argument(
        "--agirlik", action="append", metavar="BLOK=DEGER",
        help="blok ağırlığını geçersiz kıl, örn: --agirlik kredi=1.5",
    )
    ayristirici.add_argument("--kuru", action="store_true", help="yazma, sadece raporla")
    args = ayristirici.parse_args(argv)

    agirliklar = dict(VARSAYILAN.blok_agirliklari)
    for ham in args.agirlik or []:
        if "=" not in ham:
            print(f"HATA: --agirlik biçimi BLOK=DEGER olmalı: {ham}", file=sys.stderr)
            return 2
        blok, _, deger = ham.partition("=")
        agirliklar[blok.strip()] = float(deger)

    ayar = VARSAYILAN.ile(
        matris=args.matris,
        db=args.db,
        m=args.m,
        c_araligi=tuple(args.c) if args.c else VARSAYILAN.c_araligi,
        yontem=args.yontem,
        bootstrap=args.bootstrap,
        tohum=args.tohum,
        blok_agirliklari=agirliklar,
    )

    sonuc = calistir(ayar, kuru=args.kuru)

    # Temsilciler: kümeleri gözle doğrulamanın en hızlı yolu.
    matris = sonuc["matris"]
    uyelik = sonuc["uyelik"]
    conn = baglan(ayar.db)
    try:
        albom = pd.read_sql_query(
            "SELECT album_id, artist, title, year FROM albums", conn
        ).set_index("album_id").reindex(matris.index)
    finally:
        conn.close()

    sanatcilar = albom["artist"].fillna("").to_numpy()
    print("\nKüme temsilcileri (K4: üst %20 üyelikten maksimum çeşitlilik)")
    for kume in range(uyelik.shape[1]):
        damga = "" if sonuc["jaccard"][kume] >= ayar.stabilite_esigi else "  [KARARSIZ]"
        print(f"\nküme {kume} (Jaccard {sonuc['jaccard'][kume]:.2f}){damga}")
        for sira in temsilci_sec(
            sonuc["indirgeme"].X, uyelik, kume,
            adet=ayar.temsilci_sayisi, ust_dilim=ayar.temsilci_ust_dilim,
            ayni_sanatci_cezasi=sanatcilar,
        ):
            satir = albom.iloc[sira]
            print(
                f"   u={uyelik[sira, kume]:.2f}  {satir['artist']} — {satir['title']}"
                f" ({satir['year'] or '?'})"
            )
        profil = kume_profili(matris, uyelik, kume, adet=5)
        oneCikan = ", ".join(f"{s.ozellik} [{s.blok}]" for s in profil.itertuples())
        print(f"   öne çıkan: {oneCikan}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
