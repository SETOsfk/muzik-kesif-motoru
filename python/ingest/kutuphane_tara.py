"""FLAC kütüphanesini tara, `albums` tablosunu doldur.

Artımlı çalışır (K6): her dosyanın mtime + boyutu `dosyalar` tablosunda tutulur.
İkinci çalıştırmada değişmemiş dosyanın etiketi hiç okunmaz — sadece stat çağrısı
yapılır. Silinen dosyalar tespit edilir, albümün track_count'u yeniden hesaplanır.

Albüm kimliği sanatçı+albüm+yıl üzerinden türetilir (bkz. veri sözleşmesi), yani
albümü başka klasöre taşımak yeni albüm yaratmaz — zenginleştirme emeği korunur.

Kullanım:
    python -m python.ingest.kutuphane_tara --kaynak /yol/muzik
    python -m python.ingest.kutuphane_tara --kaynak /yol/muzik --yeniden
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Iterator

from mutagen import File as MutagenFile

from python.db import VARSAYILAN_DB, baglan
from python.metin import album_kimligi, yil_ayikla

SES_UZANTILARI = (".flac",)
VARSAYILAN_RAPOR = Path("data/raporlar/etiketsiz_dosyalar.csv")

# Vorbis comment alan adları; sırayla denenir, ilk dolu olan kazanır.
ALAN_SANATCI = ("albumartist", "album artist", "artist", "performer")
ALAN_ALBUM = ("album",)
ALAN_YIL = ("originaldate", "originalyear", "date", "year")
ALAN_LABEL = ("label", "organization", "publisher")


@dataclass(frozen=True)
class Parca:
    """Tek bir ses dosyasından okunan, albüm kurmaya yeten asgari bilgi."""

    yol: Path
    mtime: float
    boyut: int
    artist: str
    album: str
    yil: int | None
    label: str | None

    @property
    def album_id(self) -> str:
        return album_kimligi(self.artist, self.album, self.yil)


@dataclass
class Ozet:
    taranan: int = 0
    atlanan: int = 0
    okunan: int = 0
    etiketsiz: list[Path] = field(default_factory=list)
    silinen: int = 0
    yeni_album: int = 0
    guncellenen_album: int = 0
    bos_album: list[str] = field(default_factory=list)

    def yazdir(self, akis=sys.stdout) -> None:
        print(f"Taranan dosya      : {self.taranan}", file=akis)
        print(f"  değişmemiş (atlandı): {self.atlanan}", file=akis)
        print(f"  okunan               : {self.okunan}", file=akis)
        print(f"  etiketsiz/bozuk      : {len(self.etiketsiz)}", file=akis)
        print(f"Kütüphaneden silinen: {self.silinen}", file=akis)
        print(f"Yeni albüm          : {self.yeni_album}", file=akis)
        print(f"Güncellenen albüm   : {self.guncellenen_album}", file=akis)
        if self.bos_album:
            print(
                f"UYARI: {len(self.bos_album)} albümün hiç dosyası kalmadı "
                "(kayıt silinmedi, zenginleştirme verisi korundu).",
                file=akis,
            )


# --------------------------------------------------------------------------- #
# Dosya okuma
# --------------------------------------------------------------------------- #

def dosyalari_bul(kok: Path) -> Iterator[tuple[Path, os.stat_result]]:
    """Kök altındaki ses dosyalarını, deterministik sırayla üret."""
    for dizin, alt_dizinler, dosyalar in os.walk(kok):
        alt_dizinler.sort()
        alt_dizinler[:] = [d for d in alt_dizinler if not d.startswith(".")]
        for ad in sorted(dosyalar):
            if ad.startswith("."):
                continue
            if not ad.lower().endswith(SES_UZANTILARI):
                continue
            yol = Path(dizin) / ad
            try:
                yield yol, yol.stat()
            except OSError as hata:
                print(f"  atlandı (stat): {yol} — {hata}", file=sys.stderr)


def _ilk_deger(etiketler, adlar: tuple[str, ...]) -> str | None:
    """Vorbis comment sözlüğünden ilk dolu alanı çek (değerler liste gelir)."""
    for ad in adlar:
        try:
            ham = etiketler.get(ad)
        except Exception:  # bazı etiket türleri sözlük gibi davranmaz
            ham = None
        if ham is None:
            continue
        if isinstance(ham, (list, tuple)):
            ham = ham[0] if ham else None
        if ham is None:
            continue
        deger = str(ham).strip()
        if deger:
            return deger
    return None


def parca_oku(yol: Path, st: os.stat_result) -> Parca | None:
    """Dosyanın etiketlerini oku. Sanatçı veya albüm yoksa None döner."""
    try:
        ses = MutagenFile(yol)
    except Exception as hata:
        print(f"  okunamadı: {yol} — {hata}", file=sys.stderr)
        return None
    if ses is None or ses.tags is None:
        return None

    artist = _ilk_deger(ses.tags, ALAN_SANATCI)
    album = _ilk_deger(ses.tags, ALAN_ALBUM)
    if not artist or not album:
        return None

    return Parca(
        yol=yol,
        mtime=st.st_mtime,
        boyut=st.st_size,
        artist=artist,
        album=album,
        yil=yil_ayikla(_ilk_deger(ses.tags, ALAN_YIL)),
        label=_ilk_deger(ses.tags, ALAN_LABEL),
    )


# --------------------------------------------------------------------------- #
# Tarama
# --------------------------------------------------------------------------- #

def _ortak_klasor(yollar: list[str]) -> str | None:
    """Albümün dosyalarını kapsayan en dar klasör (CD1/CD2 varsa üst klasör)."""
    if not yollar:
        return None
    klasorler = [str(Path(y).parent) for y in yollar]
    if len(set(klasorler)) == 1:
        return klasorler[0]
    try:
        return os.path.commonpath(klasorler)
    except ValueError:  # farklı sürücüler
        return klasorler[0]


def tara(
    conn: sqlite3.Connection,
    kok: Path,
    *,
    yeniden: bool = False,
    okuyucu: Callable[[Path, os.stat_result], Parca | None] = parca_oku,
) -> Ozet:
    """Kütüphaneyi tarayıp `albums` ve `dosyalar` tablolarını güncelle.

    `okuyucu` testler için enjekte edilebilir; üretimde `parca_oku`.
    """
    ozet = Ozet()

    bilinen = {
        satir["yol"]: (satir["mtime"], satir["boyut"], satir["album_id"])
        for satir in conn.execute("SELECT yol, mtime, boyut, album_id FROM dosyalar")
    }

    gorulen: set[str] = set()
    degisen: list[tuple[Path, os.stat_result]] = []

    for yol, st in dosyalari_bul(kok):
        anahtar = str(yol)
        gorulen.add(anahtar)
        ozet.taranan += 1
        kayit = bilinen.get(anahtar)
        # mtime kayan noktalı; dosya sistemleri arasında son basamak oynayabilir.
        if (
            not yeniden
            and kayit is not None
            and abs(kayit[0] - st.st_mtime) < 1e-6
            and kayit[1] == st.st_size
        ):
            ozet.atlanan += 1
            continue
        degisen.append((yol, st))

    silinen = sorted(set(bilinen) - gorulen)
    ozet.silinen = len(silinen)

    parcalar: list[Parca] = []
    for yol, st in degisen:
        parca = okuyucu(yol, st)
        if parca is None:
            ozet.etiketsiz.append(yol)
            continue
        parcalar.append(parca)
        ozet.okunan += 1

    # Etkilenen albümler: değişen dosyaların albümleri + silinen dosyaların albümleri.
    kirli: set[str] = {p.album_id for p in parcalar}
    kirli.update(bilinen[y][2] for y in silinen)
    # Dosyası başka albüme taşınmış olabilir (etiket düzeltildi) — eskisi de kirli.
    kirli.update(
        bilinen[str(p.yol)][2] for p in parcalar if str(p.yol) in bilinen
    )

    albume_gore: dict[str, list[Parca]] = defaultdict(list)
    for parca in parcalar:
        albume_gore[parca.album_id].append(parca)

    mevcut = {
        satir["album_id"]
        for satir in conn.execute("SELECT album_id FROM albums")
    }
    bugun = date.today().isoformat()

    with conn:
        for yol in silinen:
            conn.execute("DELETE FROM dosyalar WHERE yol = ?", (yol,))

        for album_id, grup in albume_gore.items():
            # Aynı albümün dosyaları arasında etiket tutarsızlığı olabilir;
            # en sık geçen değeri al.
            artist = Counter(p.artist for p in grup).most_common(1)[0][0]
            baslik = Counter(p.album for p in grup).most_common(1)[0][0]
            yillar = [p.yil for p in grup if p.yil]
            yil = Counter(yillar).most_common(1)[0][0] if yillar else None
            labellar = [p.label for p in grup if p.label]
            label = Counter(labellar).most_common(1)[0][0] if labellar else None

            if album_id in mevcut:
                ozet.guncellenen_album += 1
            else:
                ozet.yeni_album += 1
                mevcut.add(album_id)

            # mbid / country / label zenginleştirmeden gelir; tarama onları ezmez.
            conn.execute(
                """
                INSERT INTO albums (album_id, artist, title, year, label, eklenme_tarihi)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(album_id) DO UPDATE SET
                    artist = excluded.artist,
                    title  = excluded.title,
                    year   = COALESCE(excluded.year, albums.year),
                    label  = COALESCE(albums.label, excluded.label)
                """,
                (album_id, artist, baslik, yil, label, bugun),
            )
            for parca in grup:
                conn.execute(
                    """
                    INSERT INTO dosyalar (yol, album_id, mtime, boyut)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(yol) DO UPDATE SET
                        album_id = excluded.album_id,
                        mtime    = excluded.mtime,
                        boyut    = excluded.boyut
                    """,
                    (str(parca.yol), album_id, parca.mtime, parca.boyut),
                )

        # track_count ve path yalnızca etkilenen albümler için yeniden hesaplanır.
        for album_id in kirli:
            yollar = [
                satir["yol"]
                for satir in conn.execute(
                    "SELECT yol FROM dosyalar WHERE album_id = ? ORDER BY yol", (album_id,)
                )
            ]
            if not yollar:
                ozet.bos_album.append(album_id)
            conn.execute(
                "UPDATE albums SET track_count = ?, path = COALESCE(?, path) WHERE album_id = ?",
                (len(yollar), _ortak_klasor(yollar), album_id),
            )

    return ozet


def rapor_yaz(dosyalar: list[Path], hedef: Path) -> None:
    """Etiketi eksik dosyaları elle düzeltme için CSV'ye dök."""
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with hedef.open("w", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)
        yazici.writerow(["yol", "sorun"])
        for yol in dosyalar:
            yazici.writerow([str(yol), "sanatçı veya albüm etiketi yok"])


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(
        description="FLAC kütüphanesini tara ve albums tablosunu doldur."
    )
    ayristirici.add_argument("--kaynak", required=True, type=Path, help="müzik kök klasörü")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument(
        "--yeniden",
        action="store_true",
        help="artımlı atlamayı devre dışı bırak, her dosyanın etiketini yeniden oku",
    )
    ayristirici.add_argument(
        "--rapor", type=Path, default=VARSAYILAN_RAPOR, help="etiketsiz dosya raporu"
    )
    args = ayristirici.parse_args(argv)

    if not args.kaynak.is_dir():
        print(f"HATA: klasör bulunamadı: {args.kaynak}", file=sys.stderr)
        return 2

    conn = baglan(args.db)
    try:
        ozet = tara(conn, args.kaynak, yeniden=args.yeniden)
    finally:
        conn.close()

    ozet.yazdir()
    if ozet.etiketsiz:
        rapor_yaz(ozet.etiketsiz, args.rapor)
        print(f"Etiketsiz dosya listesi: {args.rapor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
