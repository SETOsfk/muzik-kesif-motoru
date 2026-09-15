"""Tek kullanıcılık `kesif.sqlite`'ı ikiye ayır: ortak + kullanıcı.

Bu göç bir kez çalışır ve geri dönüşü vardır (özgün dosyaya dokunulmaz).

NE OLUYOR
`data/db/kesif.sqlite` bugün hem albüm zenginleştirmesini (krediler, stem
ölçümü, çalma listesi havuzu) hem kullanıcının kendi kütüphanesini ve
kararlarını taşıyor. Çok kullanıcılığa geçerken ikisi ayrılıyor:

    data/db/ortak.sqlite         herkesin yararlandığı, bir kez hesaplanan
    data/db/kullanici/1.sqlite   Sertan'ın kütüphanesi, eksenleri, kararları

Ayrım ölçütü `python/db.py:ORTAK_TABLOLAR` içinde yazılı ve tek doğru kaynak
orası; bu betik yalnız satırları taşır.

NEDEN KOPYALAMA, TAŞIMA DEĞİL
Özgün `kesif.sqlite` yerinde bırakılıyor. Göç yanlış giderse geri dönüş
dosyayı eski adıyla kullanmaktan ibaret. Disk bedeli 25 MB.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

from python.db import (
    KULLANICI_KOK,
    ORTAK_TABLOLAR,
    ESKI_TEK_DB,
    VARSAYILAN_ORTAK,
    baglan_kullanici,
    kullanici_db,
)


def tablolar(conn: sqlite3.Connection) -> list[str]:
    return [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'")
    ]


def satir_tasi(kaynak: sqlite3.Connection, hedef_conn: sqlite3.Connection,
               tablo: str, hedef_ad: str) -> int:
    """Bir tablonun tüm satırlarını taşı. Sütunlar KESİŞİMDEN alınır.

    Kesişim şart: `kesif.sqlite` göçlerle büyümüş olabilir ve yeni şemada
    olmayan sütun taşınırsa INSERT patlar. Aynı korumanın gerekçesi
    `db._stem_profili_gocu` içinde de yazılı.
    """
    eski = [s[1] for s in kaynak.execute(f"PRAGMA table_info({tablo})")]
    # PRAGMA'da niteleme SQL'den farklı yazılır: `PRAGMA ortak.table_info(x)`,
    # `PRAGMA table_info(ortak.x)` DEĞİL — ikincisi sözdizimi hatası verir.
    if "." in hedef_ad:
        vt, _, sade = hedef_ad.partition(".")
        pragma = f"PRAGMA {vt}.table_info({sade})"
    else:
        pragma = f"PRAGMA table_info({hedef_ad})"
    yeni = [s[1] for s in hedef_conn.execute(pragma)]
    ortak_sutun = [s for s in eski if s in yeni]
    if not ortak_sutun:
        return 0
    sutunlar = ", ".join(f'"{s}"' for s in ortak_sutun)
    satirlar = kaynak.execute(f"SELECT {sutunlar} FROM {tablo}").fetchall()
    if not satirlar:
        return 0
    yer = ", ".join("?" * len(ortak_sutun))
    with hedef_conn:
        hedef_conn.executemany(
            f"INSERT OR REPLACE INTO {hedef_ad} ({sutunlar}) VALUES ({yer})",
            [tuple(r) for r in satirlar],
        )
    return len(satirlar)


def gocur(
    kaynak_yolu: Path = ESKI_TEK_DB, *, ad: str = "Sertan",
    eposta: str | None = None, kuru: bool = False,
) -> dict[str, int]:
    if not kaynak_yolu.exists():
        raise SystemExit(f"kaynak yok: {kaynak_yolu}")

    hedefler = [VARSAYILAN_ORTAK, kullanici_db(1)]
    var_olan = [h for h in hedefler if h.exists()]
    if var_olan and not kuru:
        raise SystemExit(
            f"hedef zaten var: {', '.join(str(h) for h in var_olan)}\n"
            "Göç bir kez çalışır. Yeniden çalıştırmak için önce onları taşı."
        )

    kaynak = sqlite3.connect(kaynak_yolu)
    kaynak.row_factory = sqlite3.Row
    mevcut = set(tablolar(kaynak))

    # Şema kurulumu: bağlantı hem kullanıcıyı hem ortağı oluşturur.
    conn = baglan_kullanici(1)

    # Kullanıcı kaydı — göç edilen kütüphanenin sahibi.
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO kullanici (kullanici_id, ad, eposta, olusturma) "
            "VALUES (1, ?, ?, ?)", (ad, eposta, date.today().isoformat()))

    sayac: dict[str, int] = {}
    for tablo in sorted(mevcut):
        if tablo not in ORTAK_TABLOLAR and tablo in {"kullanici", "oturum"}:
            continue
        hedef_ad = f"ortak.{tablo}" if tablo in ORTAK_TABLOLAR else tablo
        try:
            n = satir_tasi(kaynak, conn, tablo, hedef_ad)
        except sqlite3.Error as hata:
            print(f"  ATLANDI {tablo}: {hata}", file=sys.stderr)
            continue
        if n:
            sayac[f"{'ortak' if tablo in ORTAK_TABLOLAR else 'kullanıcı'}/{tablo}"] = n
    conn.close()
    kaynak.close()
    return sayac


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--kaynak", type=Path, default=ESKI_TEK_DB)
    a.add_argument("--ad", default="Sertan", help="1 numaralı kullanıcının adı")
    a.add_argument("--eposta")
    a.add_argument("--yeniden", action="store_true",
                   help="hedefler varsa üzerine yaz (önce yedekler)")
    args = a.parse_args(argv)

    if args.yeniden:
        for h in (VARSAYILAN_ORTAK, kullanici_db(1)):
            if h.exists():
                shutil.move(str(h), str(h) + ".onceki")
                print(f"  yedeklendi: {h}.onceki", file=sys.stderr)
        for ek in ("-wal", "-shm"):
            for h in (VARSAYILAN_ORTAK, kullanici_db(1)):
                yan = Path(str(h) + ek)
                if yan.exists():
                    yan.unlink()

    sayac = gocur(args.kaynak, ad=args.ad, eposta=args.eposta)
    print(f"\n{'hedef/tablo':<34}{'satır':>10}")
    print("-" * 44)
    for k, v in sorted(sayac.items()):
        print(f"{k:<34}{v:>10}")
    print("-" * 44)
    print(f"{'TOPLAM':<34}{sum(sayac.values()):>10}")
    print(f"\nortak     : {VARSAYILAN_ORTAK}")
    print(f"kullanıcı : {kullanici_db(1)}")
    print(f"özgün dosya yerinde bırakıldı: {args.kaynak}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
