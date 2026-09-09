"""30 saniyelik önizleme: iTunes Search + Deezer.

İki iş birden görür (K11): kullanıcı dinler VE aday albümün ses profili buradan
çıkarılabilir — `parca_analiz(--sure 30)` doğrudan bu dosyayı yiyebilir.

İkisi de anahtarsız ve ücretsiz (test edildi 2026-08-11): 6 örnek albümün 5'inde
ikisi de önizleme verdi, niş Japon fusion grubunda ikisi de vermedi.

Kullanım:
    python -m python.discover.onizleme --sanatci "Issei Noro" --album "Sweet Sphere"
    python -m python.discover.onizleme --adaylar        # üretilmiş adaylara doldur
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.metin import normalize_esleme
from python.onbellek import AgYok, ApiIstemci, IstekBasarisiz


def itunes(**kwargs) -> ApiIstemci:
    return ApiIstemci(
        servis="itunes",
        temel_url="https://itunes.apple.com",
        istek_araligi=1.5,            # 0.4 sn 403 yedi; Apple sınırı belgelemiyor
        basliklar={"User-Agent": "muzik-kesif-motoru/0.1"},
        **kwargs,
    )


def deezer(**kwargs) -> ApiIstemci:
    return ApiIstemci(
        servis="deezer",
        temel_url="https://api.deezer.com",
        istek_araligi=0.5,
        basliklar={"User-Agent": "muzik-kesif-motoru/0.1"},
        **kwargs,
    )


@dataclass(frozen=True)
class Onizleme:
    kaynak: str
    parca: str
    url: str
    kapak: str | None = None


def _uyuyor_mu(aday_sanatci: str, bulunan_sanatci: str) -> bool:
    """Yanlış sanatçının önizlemesini çalmak, yanlış öneri sunmaktan beterdir."""
    a, b = normalize_esleme(aday_sanatci), normalize_esleme(bulunan_sanatci)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _album_uyuyor_mu(istenen: str, bulunan: str) -> bool:
    """Bulunan klip GERÇEKTEN istenen albümden mi?

    Sanatçıyı doğrulamak yetmiyor. Ölçüldü: 13 aday yanlış albümün klibini
    taşıyordu çünkü arama, zayıf albüm eşleşmesinde sanatçının HIT şarkısına
    düşüyor — Mariya Takeuchi'nin üç ayrı albümü (1978, 1979, 1980) için de
    «Plastic Love» (1984) dönmüştü, üçünün ses uzaklığı bile aynı çıkmıştı.

    Bedeli sadece yanlış şarkı çalmak değil: aday albümün stem ölçümü o klipten
    yapılıyor, yani ölçüm de yanlış albümü anlatıyor. Eşleşme doğrulanamıyorsa
    önizleme YOK saymak, yanlışını göstermekten iyi.
    """
    a, b = normalize_esleme(istenen), normalize_esleme(bulunan)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    # Belirgin ortak sözcük: "Use Your Illusion I" ↔ "Use Your Illusion 1".
    # Tek harflik ve çok yaygın parçacıklar sayılmıyor.
    ax = {p for p in a.split() if len(p) > 2}
    bx = {p for p in b.split() if len(p) > 2}
    return bool(ax and bx) and len(ax & bx) / min(len(ax), len(bx)) >= 0.6


def itunes_onizleme(istemci: ApiIstemci, sanatci: str, album: str) -> Onizleme | None:
    govde = istemci.get_json(
        "search",
        {"term": f"{sanatci} {album}", "entity": "song", "limit": 8, "media": "music"},
    )
    for kayit in (govde or {}).get("results", []):
        if not kayit.get("previewUrl"):
            continue
        if not _uyuyor_mu(sanatci, kayit.get("artistName", "")):
            continue
        if not _album_uyuyor_mu(album, kayit.get("collectionName", "")):
            continue
        return Onizleme(
            kaynak="itunes",
            parca=kayit.get("trackName", ""),
            url=kayit["previewUrl"],
            kapak=kayit.get("artworkUrl100"),
        )
    return None


def deezer_onizleme(istemci: ApiIstemci, sanatci: str, album: str) -> Onizleme | None:
    govde = istemci.get_json("search", {"q": f"{sanatci} {album}", "limit": 8})
    for kayit in (govde or {}).get("data", []):
        if not kayit.get("preview"):
            continue
        bulunan = (kayit.get("artist") or {}).get("name", "")
        if not _uyuyor_mu(sanatci, bulunan):
            continue
        if not _album_uyuyor_mu(album, (kayit.get("album") or {}).get("title", "")):
            continue
        return Onizleme(
            kaynak="deezer",
            parca=kayit.get("title", ""),
            url=kayit["preview"],
            kapak=(kayit.get("album") or {}).get("cover_medium"),
        )
    return None


def onizleme_bul(
    sanatci: str, album: str, *, cevrimdisi: bool = False, istemciler=None
) -> Onizleme | None:
    """Önce iTunes, olmazsa Deezer. İkisi de yoksa None — uydurma yapılmaz.

    Kaynak hatası YUTULUR ve diğerine geçilir: iki kaynak koymanın sebebi tam
    olarak bu. Apple bu IP'yi 403 ile kısıtladığında bütün tur çökmüştü —
    oysa Deezer sorunsuz cevap veriyordu.
    """
    if istemciler is None:
        istemciler = (
            (itunes_onizleme, itunes(cevrimdisi=cevrimdisi)),
            (deezer_onizleme, deezer(cevrimdisi=cevrimdisi)),
        )
    for bulucu, istemci in istemciler:
        try:
            sonuc = bulucu(istemci, sanatci, album)
        except (AgYok, IstekBasarisiz) as hata:
            print(f"  {istemci.servis} atlandı: {hata}", file=sys.stderr)
            continue
        if sonuc:
            return sonuc
    return None


def adaylara_doldur(
    conn: sqlite3.Connection, calisma_id: str | None = None, limit: int | None = None
) -> dict[str, int]:
    # `onizleme_parca IS NULL` de dahil: URL'si olan ama parça adı olmayan eski
    # satırlar da doldurulsun. İstemci önbellekli, tekrar sorgu bedavaya yakın.
    sorgu = ("SELECT rowid, artist, title FROM adaylar "
             "WHERE onizleme_url IS NULL OR onizleme_parca IS NULL")
    params: list = []
    if calisma_id:
        sorgu += " AND calisma_id = ?"
        params.append(calisma_id)
    sorgu += " ORDER BY skor DESC"
    if limit:
        sorgu += f" LIMIT {int(limit)}"

    # İstemciler bir kez kurulur: her aday için yenisini yaratmak rate-limit
    # sayacını sıfırlıyor ve Apple'ın sınırına arka arkaya toslamaya yol açıyor.
    istemciler = ((itunes_onizleme, itunes()), (deezer_onizleme, deezer()))

    sayac = {"bakilan": 0, "bulunan": 0}
    for satir in conn.execute(sorgu, params).fetchall():
        sayac["bakilan"] += 1
        onizleme = onizleme_bul(satir["artist"], satir["title"], istemciler=istemciler)
        if not onizleme:
            continue
        with conn:
            conn.execute(
                "UPDATE adaylar SET onizleme_url = ?, onizleme_parca = ?, "
                "kapak = ? WHERE rowid = ?",
                (onizleme.url, onizleme.parca, onizleme.kapak, satir["rowid"]),
            )
        sayac["bulunan"] += 1
        if sayac["bakilan"] % 10 == 0:
            print(f"  {sayac['bakilan']} bakıldı, {sayac['bulunan']} bulundu", file=sys.stderr)
    return sayac


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="30 sn önizleme bul.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--sanatci")
    ayristirici.add_argument("--album")
    ayristirici.add_argument("--adaylar", action="store_true")
    ayristirici.add_argument("--limit", type=int)
    args = ayristirici.parse_args(argv)

    if args.sanatci and args.album:
        onizleme = onizleme_bul(args.sanatci, args.album)
        if onizleme:
            print(f"{onizleme.kaynak}: {onizleme.parca}\n{onizleme.url}")
            return 0
        print("Önizleme bulunamadı.", file=sys.stderr)
        return 1

    if not args.adaylar:
        ayristirici.error("--sanatci/--album ya da --adaylar verilmeli")

    conn = baglan(args.db)
    try:
        sayac = adaylara_doldur(conn, limit=args.limit)
    finally:
        conn.close()
    print(f"Bakılan aday: {sayac['bakilan']}, önizleme bulunan: {sayac['bulunan']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
