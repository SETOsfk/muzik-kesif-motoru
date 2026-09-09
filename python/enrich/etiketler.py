"""Tür / alt tür etiketleri — MusicBrainz tag+genre, Discogs genre+style.

Etiketler tek başına yetersizdir (projenin çıkış noktası bu), ama kredi bloğunun
yanında bağlam verirler: aynı davulcuyu paylaşan iki albümden biri fusion diğeri
prog ise bu ayrımı etiket bloğu taşır.

Ağırlıklar albüm içinde toplamı 1 olacak şekilde normalize edilir. Ham oy sayısını
saklamak yanıltıcı olurdu: MusicBrainz'de popüler albümün 60 oyu, Türkçe bir albümün
2 oyu vardır — bu popülerlik farkıdır, tür farkı değil.

Kullanım:
    python -m python.enrich.etiketler
    python -m python.enrich.etiketler --kaynak mb --limit 100
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.enrich.krediler import discogs_release_bul
from python.onbellek import AgYok, ApiIstemci, discogs, musicbrainz

# Tür bilgisi taşımayan, kullanıcı listesinden sızan etiketler.
COP_ETIKETLER = frozenset(
    {
        "seen live", "favorites", "favourites", "albums i own", "vinyl", "cd",
        "owned", "spotify", "check out", "to listen", "awesome", "good",
        "great album", "masterpiece", "classic", "favorite albums", "10 out of 10",
        "albums", "music", "song", "songs", "band", "male vocalists",
        "female vocalists", "usa", "uk", "american", "british", "türkçe",
        "rock music", "album rock", "music to listen to", "guitar", "instrumental",
    }
)

# Tür değil, kullanıcının rafını anlatan etiket kalıpları.
COP_KALIPLAR = (
    re.compile(r"^\d+\s*[–—-]\s*\d+"),                    # "1–4 wochen"
    re.compile(r"^(19|20)?\d0'?s$"),                      # "80s", "1970s"
    re.compile(r"^(19|20)\d{2}$"),                        # "1981"
    re.compile(r"^(english|german|deutsch|french|spanish|turkish|japanese|"
               r"italian|swedish|finnish|russian)$"),
    re.compile(r"\b(cover|sleeve|artwork|hipgnosis)\b"),  # kapak/tasarım notu
)

_BOSLUK = re.compile(r"\s+")


def etiket_normalize(ham: str | None) -> str | None:
    """Küçük harf, tek boşluk, ayırıcı birliği. Çöp etiketler elenir."""
    if not ham:
        return None
    etiket = _BOSLUK.sub(" ", ham.strip().lower().replace("_", " ").replace("&", "and"))
    etiket = etiket.strip(" -/,")
    if len(etiket) < 2 or etiket in COP_ETIKETLER:
        return None
    if any(kalip.search(etiket) for kalip in COP_KALIPLAR):
        return None
    return etiket


def mb_etiketleri(govde: dict | None) -> dict[str, float]:
    """MB tag/genre listelerini ham ağırlığa çevir (oy sayısı)."""
    if not govde:
        return {}
    agirliklar: dict[str, float] = defaultdict(float)
    for alan, katsayi in (("genres", 1.5), ("tags", 1.0)):
        for kayit in govde.get(alan) or []:
            etiket = etiket_normalize(kayit.get("name"))
            if not etiket:
                continue
            # Oy sayısı doyuma uğratılır: 40 oylu etiket 4 oylunun 10 katı değildir.
            oy = max(1, int(kayit.get("count") or 1))
            agirliklar[etiket] += katsayi * (1 + (oy - 1) ** 0.5)
    return dict(agirliklar)


def discogs_etiketleri(release: dict | None) -> dict[str, float]:
    """Discogs genre (geniş) ve style (dar) alanları."""
    if not release:
        return {}
    agirliklar: dict[str, float] = defaultdict(float)
    for alan, katsayi in (("genres", 1.0), ("styles", 1.5)):
        for ham in release.get(alan) or []:
            etiket = etiket_normalize(ham)
            if etiket:
                # style daha bilgilendiricidir: "Prog Rock" > "Rock"
                agirliklar[etiket] += katsayi
    return dict(agirliklar)


def normalize_agirliklar(agirliklar: dict[str, float]) -> dict[str, float]:
    toplam = sum(agirliklar.values())
    if toplam <= 0:
        return {}
    return {etiket: agirlik / toplam for etiket, agirlik in agirliklar.items()}


def etiketleri_yaz(conn: sqlite3.Connection, album_id: str, agirliklar: dict[str, float]) -> int:
    if not agirliklar:
        return 0
    with conn:
        conn.execute("DELETE FROM tags WHERE album_id = ?", (album_id,))
        conn.executemany(
            "INSERT INTO tags (album_id, tag, agirlik) VALUES (?, ?, ?)",
            [(album_id, etiket, round(agirlik, 5)) for etiket, agirlik in agirliklar.items()],
        )
    return len(agirliklar)


def zenginlestir(
    conn: sqlite3.Connection,
    *,
    mb: ApiIstemci | None,
    dc: ApiIstemci | None,
    limit: int | None = None,
    yenile: bool = False,
) -> dict[str, int]:
    sayac = {"album": 0, "etiketli": 0, "etiket": 0, "bos": 0}

    sorgu = "SELECT album_id, artist, title, year, mbid FROM albums"
    if not yenile:
        sorgu += " WHERE album_id NOT IN (SELECT DISTINCT album_id FROM tags)"
    sorgu += " ORDER BY artist, title"
    if limit:
        sorgu += f" LIMIT {int(limit)}"

    for sira, albom in enumerate(conn.execute(sorgu).fetchall(), 1):
        sayac["album"] += 1
        ham: dict[str, float] = defaultdict(float)

        if mb and albom["mbid"]:
            try:
                govde = mb.get_json(
                    f"release-group/{albom['mbid']}", {"inc": "tags+genres", "fmt": "json"}
                )
                for etiket, agirlik in mb_etiketleri(govde).items():
                    ham[etiket] += agirlik
            except AgYok:
                pass

        if dc:
            try:
                release = discogs_release_bul(dc, albom["artist"], albom["title"], albom["year"])
                for etiket, agirlik in discogs_etiketleri(release).items():
                    ham[etiket] += agirlik
            except AgYok:
                pass

        yazilan = etiketleri_yaz(conn, albom["album_id"], normalize_agirliklar(dict(ham)))
        if yazilan:
            sayac["etiketli"] += 1
            sayac["etiket"] += yazilan
        else:
            sayac["bos"] += 1

        if sira % 25 == 0:
            print(f"  {sira} albüm işlendi", file=sys.stderr)

    return sayac


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Tür/alt tür etiketleri.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--kaynak", default="hepsi", choices=("hepsi", "mb", "discogs"))
    ayristirici.add_argument("--limit", type=int)
    ayristirici.add_argument("--yenile", action="store_true")
    ayristirici.add_argument("--cevrimdisi", action="store_true")
    args = ayristirici.parse_args(argv)

    mb = musicbrainz(cevrimdisi=args.cevrimdisi) if args.kaynak in ("hepsi", "mb") else None
    dc = discogs(cevrimdisi=args.cevrimdisi) if args.kaynak in ("hepsi", "discogs") else None

    conn = baglan(args.db)
    try:
        sayac = zenginlestir(conn, mb=mb, dc=dc, limit=args.limit, yenile=args.yenile)
    finally:
        conn.close()

    print(f"İşlenen albüm    : {sayac['album']}")
    print(f"Etiket alan albüm: {sayac['etiketli']} ({sayac['etiket']} etiket)")
    print(f"Etiketsiz kalan  : {sayac['bos']}")
    for istemci in (mb, dc):
        if istemci:
            print(f"{istemci.servis}: {istemci.sayac.ozet()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
