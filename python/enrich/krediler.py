"""MusicBrainz + Discogs'tan kredi çek, `credits` tablosunu doldur.

Sistemin çekirdeği burası: tür etiketinin söylemediğini krediler söyler.

MusicBrainz iki katmandan okunur — albüm düzeyi ilişkiler (prodüktör, mix, mastering)
ve parça düzeyi ilişkiler (kim ne çalmış). İkincisi pahalıdır ama projenin tezi orada.
Discogs, MusicBrainz'in zayıf kaldığı yerde (özellikle metal/prog/jazz kadrosu) devreye
girer ve label/ülke bilgisini de getirir; token yoksa sessizce atlanır.

Kaldığı yerden devam: bir albümün o kaynaktan kredisi varsa tekrar bakılmaz.
Ayrı bir "durum" tablosu tutulmuyor — kredinin kendisi zaten durumun kanıtı, ve
kredisi çıkmayan albüm için yanıt önbellekte olduğundan tekrar denemek bedava (K5).

Kullanım:
    python -m python.enrich.krediler                     # iki kaynak da
    python -m python.enrich.krediler --kaynak mb --limit 50
    python -m python.enrich.krediler --cevrimdisi        # sadece önbellekten
"""

from __future__ import annotations

import argparse
import csv
import difflib
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.enrich.rol_eslemesi import rollere_ayir
from python.metin import normalize, yil_ayikla
from python.onbellek import AgYok, ApiIstemci, discogs, musicbrainz

VARSAYILAN_RAPOR = Path("data/raporlar/bilinmeyen_roller.csv")


@dataclass(frozen=True)
class Kredi:
    person_id: str | None
    person_name: str
    role: str
    kaynak: str


# --------------------------------------------------------------------------- #
# MusicBrainz
# --------------------------------------------------------------------------- #

def release_sec(govde: dict | None) -> str | None:
    """Release-group içinden kanonik release'i seç: resmi ve en eski."""
    if not govde:
        return None
    releaseler = govde.get("releases") or []
    if not releaseler:
        return None

    def anahtar(r: dict) -> tuple:
        resmi = 0 if (r.get("status") or "").lower() == "official" else 1
        return (resmi, r.get("date") or "9999", r.get("id", ""))

    return min(releaseler, key=anahtar).get("id")


# MusicBrainz nitelikleri rolü değil, rolün NİTELİĞİNİ anlatabilir:
# type=engineer, attributes=['task'] → rol "engineer"dır, "task" değil.
# type=instrument, attributes=['additional','guitar'] → rol "guitar".
# Bunlar ayıklanmazsa ilişkinin gerçek türü tamamen kaybolur (ölçüldü: 111
# mühendislik/prodüksiyon kredisi "task" diye bilinmeyene düşmüştü).
MB_DEGISTIRICILER = frozenset(
    {
        "additional", "co", "guest", "solo", "lead", "minor", "task", "bonus",
        "live", "medley", "partial", "original", "assistant",
    }
)


def _iliski_rolleri(iliski: dict) -> tuple[list[str], list[str]]:
    """MB ilişkisinden kanonik roller ve bilinmeyen ham roller."""
    nitelikler = [
        n for n in (iliski.get("attributes") or [])
        if str(n).strip().lower() not in MB_DEGISTIRICILER
    ]
    hamlar = nitelikler if nitelikler else [iliski.get("type") or ""]
    roller: list[str] = []
    bilinmeyen: list[str] = []
    for ham in hamlar:
        ayrim = rollere_ayir(ham)
        roller.extend(ayrim.roller)
        bilinmeyen.extend(ayrim.bilinmeyen)
    return roller, bilinmeyen


def mb_kredileri(release: dict | None) -> tuple[list[Kredi], list[str]]:
    """Release gövdesinden kredileri çıkar. (krediler, bilinmeyen ham roller)."""
    if not release:
        return [], []

    krediler: set[Kredi] = set()
    bilinmeyen: list[str] = []

    def iliskileri_isle(iliskiler: list[dict]) -> None:
        for iliski in iliskiler or []:
            sanatci = iliski.get("artist")
            if not sanatci:
                continue
            roller, bilinmeyenler = _iliski_rolleri(iliski)
            bilinmeyen.extend(bilinmeyenler)
            for rol in roller:
                krediler.add(
                    Kredi(sanatci.get("id"), sanatci.get("name", ""), rol, "musicbrainz")
                )

    iliskileri_isle(release.get("relations", []))
    for ortam in release.get("media", []) or []:
        for parca in ortam.get("tracks", []) or []:
            kayit = parca.get("recording") or {}
            iliskileri_isle(kayit.get("relations", []))

    return sorted(krediler, key=lambda k: (k.role, k.person_name)), bilinmeyen


def mb_albumu_getir(istemci: ApiIstemci, mbid: str) -> tuple[list[Kredi], list[str]]:
    grup = istemci.get_json(f"release-group/{mbid}", {"inc": "releases", "fmt": "json"})
    release_id = release_sec(grup)
    if not release_id:
        return [], []
    release = istemci.get_json(
        f"release/{release_id}",
        {
            "inc": "artist-rels+recordings+recording-level-rels+artist-credits",
            "fmt": "json",
        },
    )
    return mb_kredileri(release)


# --------------------------------------------------------------------------- #
# Discogs
# --------------------------------------------------------------------------- #

def discogs_kredileri(release: dict | None) -> tuple[list[Kredi], list[str]]:
    """Discogs release gövdesinden kredileri çıkar."""
    if not release:
        return [], []

    krediler: set[Kredi] = set()
    bilinmeyen: list[str] = []

    def kisileri_isle(kisiler: list[dict]) -> None:
        for kisi in kisiler or []:
            ad = (kisi.get("name") or "").strip()
            if not ad:
                continue
            # Discogs aynı adlı sanatçıları "Nick (2)" diye ayırır — kimlikte kalsın,
            # isimde temizlensin.
            temiz_ad = ad.rsplit(" (", 1)[0] if ad.endswith(")") and " (" in ad else ad
            kimlik = f"discogs:{kisi['id']}" if kisi.get("id") else None
            ayrim = rollere_ayir(kisi.get("role"))
            bilinmeyen.extend(ayrim.bilinmeyen)
            for rol in ayrim.roller:
                krediler.add(Kredi(kimlik, temiz_ad, rol, "discogs"))

    kisileri_isle(release.get("extraartists", []))
    for parca in release.get("tracklist", []) or []:
        kisileri_isle(parca.get("extraartists", []))

    return sorted(krediler, key=lambda k: (k.role, k.person_name)), bilinmeyen


def _aday_parcala(aday: dict) -> tuple[str, str]:
    """Discogs arama sonucu "Artist - Title" biçiminde tek dize döndürür."""
    ham = aday.get("title", "")
    if " - " in ham:
        sanatci, baslik = ham.split(" - ", 1)
        return sanatci.strip(), baslik.strip()
    return "", ham.strip()


def _yakin(a: str, b: str, esik: float = 0.85) -> bool:
    if a == b:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= esik


def aday_uygun_mu(aday: dict, artist: str, title: str) -> bool:
    """Adayın gerçekten bu albüm olduğundan emin ol.

    Kapı olmazsa arama ne döndürdüyse o kabul edilir ve yanlış albümün kredileri
    kütüphaneye yazılır — MBID tarafındaki disiplinin aynısı burada da gerekli.
    """
    aday_sanatci, aday_baslik = _aday_parcala(aday)
    if not _yakin(normalize(aday_baslik), normalize(title)):
        return False
    if aday_sanatci and not _yakin(normalize(aday_sanatci), normalize(artist)):
        return False
    return True


def discogs_release_bul(
    istemci: ApiIstemci, artist: str, title: str, yil: int | None
) -> dict | None:
    """Arama sonuçlarından doğru release'i seç ve tam kaydını getir.

    Üç kademe: yıllı arama → yılsız arama → normalize başlıkla arama.
    ("Meddle (2011 Remaster)" Discogs'ta da yok, "Meddle" var.)
    Master kaydı olan adaya öncelik verilir: kaset/promo baskılarının kredileri
    çoğu zaman eksiktir, master'ın ana baskısı en iyi belgelenmiş olandır.
    """

    def ara(sanatci: str, baslik: str, yil_: int | None) -> list[dict]:
        params: dict[str, object] = {
            "artist": sanatci,
            "release_title": baslik,
            "type": "release",
            "per_page": 10,
        }
        if yil_:
            params["year"] = yil_
        sonuc = istemci.get_json("database/search", params)
        return (sonuc or {}).get("results") or []

    n_artist, n_title = normalize(artist), normalize(title)
    denemeler = [(artist, title, yil), (artist, title, None)]
    if (n_artist, n_title) != (artist.lower(), title.lower()):
        denemeler.append((n_artist, n_title, None))

    uygunlar: list[dict] = []
    for sanatci, baslik, yil_ in denemeler:
        adaylar = ara(sanatci, baslik, yil_)
        uygunlar = [a for a in adaylar if aday_uygun_mu(a, artist, title)]
        if uygunlar:
            break
    if not uygunlar:
        return None

    def puan(aday: dict) -> tuple:
        return (0 if aday.get("master_id") else 1, str(aday.get("year") or "9999"))

    en_iyi = min(uygunlar, key=puan)

    master_id = en_iyi.get("master_id")
    if master_id:
        master = istemci.get_json(f"masters/{master_id}", {})
        ana_release = (master or {}).get("main_release")
        if ana_release:
            return istemci.get_json(f"releases/{ana_release}", {})
    return istemci.get_json(f"releases/{en_iyi['id']}", {})


def discogs_kunye(release: dict | None) -> dict:
    """Label / ülke / yıl — sözleşmede bu alanlar zenginleştirmeden gelir."""
    if not release:
        return {}
    labellar = release.get("labels") or []
    return {
        "label": (labellar[0].get("name") if labellar else None),
        "country": release.get("country"),
        "year": yil_ayikla(release.get("year")),
    }


# --------------------------------------------------------------------------- #
# Yürütme
# --------------------------------------------------------------------------- #

def kredileri_yaz(conn: sqlite3.Connection, album_id: str, krediler: list[Kredi]) -> int:
    with conn:
        imlec = conn.executemany(
            """
            INSERT OR IGNORE INTO credits (album_id, person_id, person_name, role, kaynak)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(album_id, k.person_id, k.person_name, k.role, k.kaynak) for k in krediler],
        )
    return imlec.rowcount


def zenginlestir(
    conn: sqlite3.Connection,
    *,
    mb: ApiIstemci | None,
    dc: ApiIstemci | None,
    limit: int | None = None,
    yenile: bool = False,
) -> tuple[dict[str, int], Counter]:
    sayac = {"album": 0, "mb_kredi": 0, "dc_kredi": 0, "mb_bos": 0, "dc_bos": 0, "kunye": 0}
    bilinmeyen: Counter = Counter()

    sorgu = "SELECT album_id, artist, title, year, mbid FROM albums ORDER BY artist, title"
    if limit:
        sorgu += f" LIMIT {int(limit)}"
    albumler = conn.execute(sorgu).fetchall()

    islenmis = {
        (satir["album_id"], satir["kaynak"])
        for satir in conn.execute("SELECT DISTINCT album_id, kaynak FROM credits")
    }

    for sira, albom in enumerate(albumler, 1):
        album_id = albom["album_id"]
        sayac["album"] += 1

        if mb and albom["mbid"] and (yenile or (album_id, "musicbrainz") not in islenmis):
            try:
                krediler, bilinmeyenler = mb_albumu_getir(mb, albom["mbid"])
                bilinmeyen.update(bilinmeyenler)
                if krediler:
                    sayac["mb_kredi"] += kredileri_yaz(conn, album_id, krediler)
                else:
                    sayac["mb_bos"] += 1
            except AgYok:
                pass

        if dc and (yenile or (album_id, "discogs") not in islenmis):
            try:
                release = discogs_release_bul(dc, albom["artist"], albom["title"], albom["year"])
                krediler, bilinmeyenler = discogs_kredileri(release)
                bilinmeyen.update(bilinmeyenler)
                if krediler:
                    sayac["dc_kredi"] += kredileri_yaz(conn, album_id, krediler)
                else:
                    sayac["dc_bos"] += 1
                kunye = discogs_kunye(release)
                if kunye.get("label") or kunye.get("country"):
                    with conn:
                        conn.execute(
                            """
                            UPDATE albums
                               SET label   = COALESCE(label, ?),
                                   country = COALESCE(country, ?)
                             WHERE album_id = ?
                            """,
                            (kunye.get("label"), kunye.get("country"), album_id),
                        )
                    sayac["kunye"] += 1
            except AgYok:
                pass

        if sira % 10 == 0 or sira == len(albumler):
            print(f"  {sira}/{len(albumler)} albüm işlendi", file=sys.stderr)

    return sayac, bilinmeyen


def bilinmeyen_rapor_yaz(bilinmeyen: Counter, hedef: Path) -> None:
    """Sözlüğe eklenmeyi bekleyen roller — rol_eslemesi.py böyle büyür."""
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with hedef.open("w", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)
        yazici.writerow(["ham_rol", "gorulme"])
        yazici.writerows(bilinmeyen.most_common())


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Kredi zenginleştirme.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--kaynak", default="hepsi", choices=("hepsi", "mb", "discogs"))
    ayristirici.add_argument("--limit", type=int)
    ayristirici.add_argument("--yenile", action="store_true", help="işlenmişleri de tekrar çek")
    ayristirici.add_argument("--cevrimdisi", action="store_true")
    ayristirici.add_argument("--rapor", type=Path, default=VARSAYILAN_RAPOR)
    args = ayristirici.parse_args(argv)

    mb = musicbrainz(cevrimdisi=args.cevrimdisi) if args.kaynak in ("hepsi", "mb") else None
    dc = discogs(cevrimdisi=args.cevrimdisi) if args.kaynak in ("hepsi", "discogs") else None
    if args.kaynak in ("hepsi", "discogs") and dc is None:
        print(
            "NOT: DISCOGS_TOKEN yok, Discogs atlanıyor. "
            "Ücretsiz token: discogs.com/settings/developers (.env dosyasına yaz).",
            file=sys.stderr,
        )

    conn = baglan(args.db)
    try:
        sayac, bilinmeyen = zenginlestir(
            conn, mb=mb, dc=dc, limit=args.limit, yenile=args.yenile
        )
    finally:
        conn.close()

    print(f"İşlenen albüm       : {sayac['album']}")
    print(f"MusicBrainz kredisi : {sayac['mb_kredi']} (kredisiz albüm: {sayac['mb_bos']})")
    print(f"Discogs kredisi     : {sayac['dc_kredi']} (kredisiz albüm: {sayac['dc_bos']})")
    print(f"Label/ülke yazılan  : {sayac['kunye']}")
    for istemci in (mb, dc):
        if istemci:
            print(f"{istemci.servis}: {istemci.sayac.ozet()}")
    if bilinmeyen:
        bilinmeyen_rapor_yaz(bilinmeyen, args.rapor)
        print(f"Sözlükte olmayan {len(bilinmeyen)} rol: {args.rapor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
