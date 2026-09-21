"""Yeniden kümelemede kullanıcı emeğini taşı: küme adları ve kararlar.

Kümeleme `calisma_id` ile versiyonlanıyor ve arayüz EN YENİ çalışmayı
gösteriyor. Yeni bir çalışma açmak (yeni krediler, yeni matris) bu yüzden
kullanıcının verdiği küme adlarını ve geri bildirimlerini eskide bırakıyordu —
kümelemeyi iyileştirmenin bedeli emeği kaybetmekti. 2026-09-21'de 10 yeni
MBID + 476 kredi sonrası yeni kümeleme ölçüldü ve daha iyi çıktı (liste @10
0,12→0,16, melez @50 0,09→0,11); bu modül onu kayıpsız devreye almak için.

## Eşleme

Eksen kimliği iki çalışma arasında ANLAM taşımaz (küme 4 başka bir şey
olabilir). Eşleme keskin üyelerin Jaccard benzerliğiyle, açgözlü ve bire bir:
en yüksek Jaccard'lı çift önce eşlenir, iki taraf da bir kez kullanılır.

- **Ad** yalnız `Jaccard >= AD_ESIGI` ise taşınır. «metal» adını üyelerinin
  yarısından azını paylaşan bir kümeye yapıştırmak, adı yalan yapar.
- **Karar** her durumda taşınır — karar bir ADAY hakkında, eksen yalnız
  bağlam. Eşlenmeyen eski eksenin kararları en çok örtüşen yeni eksene gider.

Eski çalışma silinmez; eski hâline dönmek arayüzde `?calisma=` ile mümkün.
"""

from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan

#: Adın taşınması için gereken asgari üye örtüşmesi.
AD_ESIGI = 0.5


def keskin_uyeler(conn: sqlite3.Connection, calisma_id: str) -> dict[int, set[str]]:
    en_iyi: dict[str, tuple[int, float]] = {}
    for album_id, kume_id, uyelik in conn.execute(
        "SELECT album_id, kume_id, uyelik FROM memberships WHERE calisma_id = ?",
        (calisma_id,),
    ):
        if album_id not in en_iyi or uyelik > en_iyi[album_id][1]:
            en_iyi[album_id] = (int(kume_id), uyelik)
    uyeler: dict[int, set[str]] = defaultdict(set)
    for album_id, (kume_id, _) in en_iyi.items():
        uyeler[kume_id].add(album_id)
    return dict(uyeler)


def eslestir(
    eski: dict[int, set[str]], yeni: dict[int, set[str]],
) -> tuple[dict[int, tuple[int, float]], dict[int, int]]:
    """(bire bir eşleme {eski: (yeni, J)}, en iyi yakınlık {eski: yeni})."""
    ciftler = sorted(
        ((len(a & b) / len(a | b), e, y)
         for e, a in eski.items() for y, b in yeni.items() if a | b),
        reverse=True,
    )
    bire_bir: dict[int, tuple[int, float]] = {}
    kullanilan: set[int] = set()
    for j, e, y in ciftler:
        if j <= 0 or e in bire_bir or y in kullanilan:
            continue
        bire_bir[e] = (y, j)
        kullanilan.add(y)
    en_yakin = {}
    for j, e, y in ciftler:
        en_yakin.setdefault(e, y)
    return bire_bir, en_yakin


def tasi(
    conn: sqlite3.Connection, eski_id: str, yeni_id: str, *, ad_esigi: float = AD_ESIGI,
) -> dict[str, list]:
    """Adları ve kararları yeni çalışmaya yaz. Rapor döner."""
    bire_bir, en_yakin = eslestir(keskin_uyeler(conn, eski_id),
                                  keskin_uyeler(conn, yeni_id))
    adlar = dict(conn.execute(
        "SELECT kume_id, kullanici_adi FROM clusters WHERE calisma_id = ? "
        "AND kullanici_adi IS NOT NULL AND kullanici_adi != ''", (eski_id,)).fetchall())

    rapor: dict[str, list] = {"tasinan_ad": [], "tasinmayan_ad": [], "karar": []}
    with conn:
        for eski_kume, ad in sorted(adlar.items()):
            eslesme = bire_bir.get(eski_kume)
            if eslesme and eslesme[1] >= ad_esigi:
                conn.execute(
                    "UPDATE clusters SET kullanici_adi = ? WHERE calisma_id = ? "
                    "AND kume_id = ? AND (kullanici_adi IS NULL OR kullanici_adi = '')",
                    (ad, yeni_id, eslesme[0]))
                rapor["tasinan_ad"].append((ad, eski_kume, eslesme[0], round(eslesme[1], 2)))
            else:
                rapor["tasinmayan_ad"].append(
                    (ad, eski_kume, round(eslesme[1], 2) if eslesme else 0.0))

        sutunlar = [s[1] for s in conn.execute("PRAGMA table_info(feedback)")]
        for satir in conn.execute(
            f"SELECT {', '.join(sutunlar)} FROM feedback WHERE calisma_id = ?",
            (eski_id,)).fetchall():
            kayit = dict(zip(sutunlar, satir))
            eski_eksen = int(kayit["eksen"])
            kayit["eksen"] = (bire_bir[eski_eksen][0] if eski_eksen in bire_bir
                              else en_yakin.get(eski_eksen, eski_eksen))
            kayit["calisma_id"] = yeni_id
            yer = ", ".join("?" * len(sutunlar))
            imlec = conn.execute(
                f"INSERT OR IGNORE INTO feedback ({', '.join(sutunlar)}) VALUES ({yer})",
                [kayit[s] for s in sutunlar])
            if imlec.rowcount:
                rapor["karar"].append((kayit["aday_id"], eski_eksen, kayit["eksen"]))
    return rapor


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    a.add_argument("--eski", required=True, help="adların ve kararların olduğu çalışma")
    a.add_argument("--yeni", required=True, help="hedef çalışma")
    args = a.parse_args(argv)
    conn = baglan(args.db)
    try:
        rapor = tasi(conn, args.eski, args.yeni)
    finally:
        conn.close()
    for ad, e, y, j in rapor["tasinan_ad"]:
        print(f"  «{ad}»: küme {e} → {y} (Jaccard {j})")
    for ad, e, j in rapor["tasinmayan_ad"]:
        print(f"  TAŞINMADI «{ad}» (küme {e}, en iyi Jaccard {j} < {AD_ESIGI})")
    print(f"  {len(rapor['karar'])} karar taşındı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
