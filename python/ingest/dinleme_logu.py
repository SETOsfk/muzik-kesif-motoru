"""Symfonium / ListenBrainz / Last.fm dışa aktarımını `plays` tablosuna aktar.

Albüm eşlemesi bulanıktır: dışa aktarımdaki "Pink Floyd — Meddle (2011 Remaster)"
ile kütüphanedeki "Meddle" aynı albümdür. Sıra: normalize tam eşleşme → sanatçı
içinde bulanık albüm eşleşmesi → bulanık sanatçı + bulanık albüm. Eşleşmeyenler
CSV'ye raporlanır; sessizce yutulmaz.

İçe aktarım idempotenttir: (kaynak, albüm, gün, parça) dörtlüsü tekildir, aynı
dosyayı iki kez aktarmak dinleme sayısını şişirmez. Kaynak ayrı tutulduğu için
Last.fm ve ListenBrainz aynı günü kapsasa bile birbirini ezmez.

Kullanım:
    python -m python.ingest.dinleme_logu --dosya ~/indirilenler/listenbrainz.json
    python -m python.ingest.dinleme_logu --dosya scrobbles.csv --bicim lastfm --kuru
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.metin import normalize

VARSAYILAN_RAPOR = Path("data/raporlar/eslesmeyen_dinlemeler.csv")

# Bulanık eşleşme eşikleri. Yanlış eşleşme, eşleşmemekten daha zararlı:
# dinleme profili öznitelik matrisine giriyor, kirlenmesi kümelemeyi bozar.
ALBUM_ESIGI = 0.85
SANATCI_ESIGI = 0.90

# Genel CSV'lerde sütun adı eşlemesi (küçük harfe indirgenmiş).
SUTUN_ADLARI: dict[str, tuple[str, ...]] = {
    "artist": ("artist", "artist_name", "albumartist", "album artist", "sanatci", "sanatçı"),
    "album": ("album", "album_name", "release", "release_name", "albüm", "albums"),
    "track": ("track", "track_name", "title", "song", "name", "parca", "parça"),
    "tarih": ("date", "uts", "timestamp", "listened_at", "last_played", "played_at",
              "play_date", "tarih", "son_calma"),
    "adet": ("count", "play count", "playcount", "plays", "play_count", "scrobbles", "adet"),
}

TARIH_BICIMLERI = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d %b %Y %H:%M",
    "%d %b %Y, %H:%M",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%m/%d/%Y %H:%M",
)


@dataclass(frozen=True)
class Dinleme:
    artist: str
    album: str
    track: str
    tarih: str  # ISO gün
    adet: int = 1


@dataclass
class Ozet:
    okunan: int = 0
    tarihsiz: int = 0
    eslesen: int = 0
    yazilan: int = 0
    yontemler: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    eslesmeyen: list[Dinleme] = field(default_factory=list)

    def yazdir(self, akis=sys.stdout) -> None:
        print(f"Okunan satır        : {self.okunan}", file=akis)
        print(f"Eşleşen dinleme     : {self.eslesen}", file=akis)
        for yontem, adet in sorted(self.yontemler.items()):
            print(f"  {yontem:<18}: {adet}", file=akis)
        print(f"Eşleşmeyen satır    : {len(self.eslesmeyen)}", file=akis)
        print(f"plays'e yazılan satır: {self.yazilan}", file=akis)
        if self.tarihsiz:
            print(f"UYARI: {self.tarihsiz} satırda tarih yok, --tarih değeri kullanıldı.", file=akis)


# --------------------------------------------------------------------------- #
# Tarih
# --------------------------------------------------------------------------- #

def tarih_coz(ham, varsayilan: str) -> tuple[str, bool]:
    """Serbest biçimli tarihi ISO güne çevir. (tarih, varsayilan_kullanildi)."""
    if ham is None or ham == "":
        return varsayilan, True
    if isinstance(ham, (int, float)):
        return datetime.fromtimestamp(float(ham), tz=timezone.utc).date().isoformat(), False

    metin = str(ham).strip()
    if not metin:
        return varsayilan, True
    if metin.isdigit() and len(metin) >= 9:  # epoch saniye
        return datetime.fromtimestamp(int(metin), tz=timezone.utc).date().isoformat(), False
    for bicim in TARIH_BICIMLERI:
        try:
            return datetime.strptime(metin, bicim).date().isoformat(), False
        except ValueError:
            continue
    try:  # ISO 8601, "Z" son eki dahil
        return datetime.fromisoformat(metin.replace("Z", "+00:00")).date().isoformat(), False
    except ValueError:
        return varsayilan, True


# --------------------------------------------------------------------------- #
# Okuyucular
# --------------------------------------------------------------------------- #

def bicim_sez(dosya: Path) -> str:
    """Dosya uzantısına ve içeriğine bakarak biçmi tahmin et."""
    uzanti = dosya.suffix.lower()
    if uzanti in (".json", ".jsonl", ".ndjson"):
        return "listenbrainz"
    return "csv"


def _listenbrainz_kayitlari(icerik: str) -> list[dict]:
    icerik = icerik.strip()
    if not icerik:
        return []
    if icerik.startswith("["):
        return json.loads(icerik)
    try:
        veri = json.loads(icerik)
    except json.JSONDecodeError:  # JSONL
        return [json.loads(satir) for satir in icerik.splitlines() if satir.strip()]
    if isinstance(veri, dict):
        for anahtar in ("listens", "payload", "items"):
            if isinstance(veri.get(anahtar), list):
                return veri[anahtar]
        if isinstance(veri.get("payload"), dict):
            return veri["payload"].get("listens", [])
        return []
    return veri if isinstance(veri, list) else []


def listenbrainz_oku(dosya: Path, varsayilan_tarih: str) -> tuple[list[Dinleme], int]:
    satirlar: list[Dinleme] = []
    tarihsiz = 0
    for kayit in _listenbrainz_kayitlari(dosya.read_text(encoding="utf-8")):
        if not isinstance(kayit, dict):
            continue
        meta = kayit.get("track_metadata") or kayit
        tarih, varsayilan_mi = tarih_coz(
            kayit.get("listened_at") or kayit.get("inserted_at"), varsayilan_tarih
        )
        tarihsiz += varsayilan_mi
        satirlar.append(
            Dinleme(
                artist=str(meta.get("artist_name") or meta.get("artist") or "").strip(),
                album=str(meta.get("release_name") or meta.get("album") or "").strip(),
                track=str(meta.get("track_name") or meta.get("track") or "").strip(),
                tarih=tarih,
            )
        )
    return satirlar, tarihsiz


def csv_oku(dosya: Path, varsayilan_tarih: str, *, bicim: str = "csv") -> tuple[list[Dinleme], int]:
    """Last.fm / Symfonium / genel CSV. Başlık yoksa Last.fm sırası varsayılır."""
    with dosya.open(newline="", encoding="utf-8-sig") as f:
        ornek = f.read(4096)
        f.seek(0)
        try:
            ayirici = csv.Sniffer().sniff(ornek, delimiters=",;\t").delimiter
        except csv.Error:
            ayirici = ","
        okuyucu = csv.reader(f, delimiter=ayirici)
        tum_satirlar = [s for s in okuyucu if any(h.strip() for h in s)]

    if not tum_satirlar:
        return [], 0

    baslik = [h.strip().lower() for h in tum_satirlar[0]]
    esleme = {}
    for alan, adaylar in SUTUN_ADLARI.items():
        for i, ad in enumerate(baslik):
            if ad in adaylar:
                esleme[alan] = i
                break

    if "artist" in esleme:
        govde = tum_satirlar[1:]
    else:
        # Başlıksız Last.fm dışa aktarımı: artist, album, track, date
        esleme = {"artist": 0, "album": 1, "track": 2, "tarih": 3}
        govde = tum_satirlar
        if bicim == "csv":
            print(
                "UYARI: başlık satırı tanınmadı, Last.fm sırası varsayıldı "
                "(sanatçı, albüm, parça, tarih).",
                file=sys.stderr,
            )

    def hucre(satir: list[str], alan: str) -> str:
        i = esleme.get(alan)
        if i is None or i >= len(satir):
            return ""
        return satir[i].strip()

    satirlar: list[Dinleme] = []
    tarihsiz = 0
    for satir in govde:
        tarih, varsayilan_mi = tarih_coz(hucre(satir, "tarih") or None, varsayilan_tarih)
        tarihsiz += varsayilan_mi
        ham_adet = hucre(satir, "adet")
        try:
            adet = max(1, int(float(ham_adet))) if ham_adet else 1
        except ValueError:
            adet = 1
        satirlar.append(
            Dinleme(
                artist=hucre(satir, "artist"),
                album=hucre(satir, "album"),
                track=hucre(satir, "track"),
                tarih=tarih,
                adet=adet,
            )
        )
    return satirlar, tarihsiz


def dosyayi_oku(dosya: Path, bicim: str, varsayilan_tarih: str) -> tuple[list[Dinleme], int]:
    if bicim == "otomatik":
        bicim = bicim_sez(dosya)
    if bicim == "listenbrainz":
        return listenbrainz_oku(dosya, varsayilan_tarih)
    return csv_oku(dosya, varsayilan_tarih, bicim=bicim)


# --------------------------------------------------------------------------- #
# Eşleştirme
# --------------------------------------------------------------------------- #

class AlbumIndeksi:
    """Kütüphanedeki albümleri normalize anahtarlarla indeksler."""

    def __init__(self, satirlar) -> None:
        self.tam: dict[str, str] = {}
        self.sanatciya_gore: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for satir in satirlar:
            n_sanatci = normalize(satir["artist"])
            n_album = normalize(satir["title"])
            self.tam.setdefault(f"{n_sanatci}|{n_album}", satir["album_id"])
            self.sanatciya_gore[n_sanatci].append((n_album, satir["album_id"]))
        self.sanatcilar = list(self.sanatciya_gore)

    def _album_ara(self, n_sanatci: str, n_album: str) -> str | None:
        adaylar = self.sanatciya_gore.get(n_sanatci)
        if not adaylar:
            return None
        if len(adaylar) == 1 and not n_album:
            # Albüm adı yok ama sanatçının kütüphanede tek albümü var.
            return adaylar[0][1]
        if not n_album:
            return None
        yakin = difflib.get_close_matches(
            n_album, [a for a, _ in adaylar], n=1, cutoff=ALBUM_ESIGI
        )
        if not yakin:
            return None
        return next(album_id for a, album_id in adaylar if a == yakin[0])

    def bul(self, artist: str, album: str) -> tuple[str | None, str]:
        """(album_id, kullanılan yöntem) döner."""
        n_sanatci, n_album = normalize(artist), normalize(album)
        if not n_sanatci:
            return None, "sanatçı yok"

        album_id = self.tam.get(f"{n_sanatci}|{n_album}")
        if album_id:
            return album_id, "tam"

        album_id = self._album_ara(n_sanatci, n_album)
        if album_id:
            return album_id, "bulanık albüm"

        yakin_sanatci = difflib.get_close_matches(
            n_sanatci, self.sanatcilar, n=1, cutoff=SANATCI_ESIGI
        )
        if yakin_sanatci:
            album_id = self._album_ara(yakin_sanatci[0], n_album)
            if album_id:
                return album_id, "bulanık sanatçı"
        return None, "eşleşmedi"


# --------------------------------------------------------------------------- #
# İçe aktarım
# --------------------------------------------------------------------------- #

def iceri_aktar(
    conn: sqlite3.Connection,
    satirlar: list[Dinleme],
    kaynak: str,
    *,
    kuru: bool = False,
) -> Ozet:
    """Dinlemeleri eşleştir, gün+parça bazında topla ve `plays`e yaz."""
    ozet = Ozet(okunan=len(satirlar))
    indeks = AlbumIndeksi(conn.execute("SELECT album_id, artist, title FROM albums"))

    toplam: dict[tuple[str, str, str], int] = defaultdict(int)
    onbellek: dict[tuple[str, str], tuple[str | None, str]] = {}

    for dinleme in satirlar:
        anahtar = (dinleme.artist, dinleme.album)
        if anahtar not in onbellek:
            onbellek[anahtar] = indeks.bul(dinleme.artist, dinleme.album)
        album_id, yontem = onbellek[anahtar]
        if album_id is None:
            ozet.eslesmeyen.append(dinleme)
            continue
        ozet.eslesen += dinleme.adet
        ozet.yontemler[yontem] += dinleme.adet
        toplam[(album_id, dinleme.tarih, dinleme.track)] += dinleme.adet

    ozet.yazilan = len(toplam)
    if kuru:
        return ozet

    with conn:
        for (album_id, tarih, track), adet in sorted(toplam.items()):
            conn.execute(
                """
                INSERT INTO plays (album_id, tarih, track, adet, kaynak)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (kaynak, album_id, tarih, COALESCE(track, ''))
                DO UPDATE SET adet = excluded.adet
                """,
                (album_id, tarih, track, adet, kaynak),
            )
    return ozet


def rapor_yaz(eslesmeyen: list[Dinleme], hedef: Path) -> None:
    """Eşleşmeyenleri sanatçı+albüm bazında topla ve CSV'ye yaz."""
    hedef.parent.mkdir(parents=True, exist_ok=True)
    gruplar: dict[tuple[str, str], int] = defaultdict(int)
    for dinleme in eslesmeyen:
        gruplar[(dinleme.artist, dinleme.album)] += dinleme.adet
    with hedef.open("w", newline="", encoding="utf-8") as f:
        yazici = csv.writer(f)
        yazici.writerow(["sanatci", "album", "dinleme_adedi", "album_id_elle"])
        for (artist, album), adet in sorted(gruplar.items(), key=lambda x: -x[1]):
            yazici.writerow([artist, album, adet, ""])


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(
        description="Dinleme geçmişi dışa aktarımını plays tablosuna aktar."
    )
    ayristirici.add_argument("--dosya", required=True, type=Path)
    ayristirici.add_argument(
        "--bicim",
        default="otomatik",
        choices=("otomatik", "listenbrainz", "lastfm", "symfonium", "csv"),
    )
    ayristirici.add_argument(
        "--etiket", help="plays.kaynak değeri (varsayılan: biçim adı)"
    )
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument(
        "--tarih",
        default=date.today().isoformat(),
        help="tarihi olmayan satırlar için kullanılacak gün (salt sayaç dışa aktarımları)",
    )
    ayristirici.add_argument("--rapor", type=Path, default=VARSAYILAN_RAPOR)
    ayristirici.add_argument(
        "--kuru", action="store_true", help="yazma, sadece eşleşmeyi raporla"
    )
    args = ayristirici.parse_args(argv)

    if not args.dosya.is_file():
        print(f"HATA: dosya bulunamadı: {args.dosya}", file=sys.stderr)
        return 2

    bicim = bicim_sez(args.dosya) if args.bicim == "otomatik" else args.bicim
    kaynak = args.etiket or bicim

    satirlar, tarihsiz = dosyayi_oku(args.dosya, bicim, args.tarih)
    if not satirlar:
        print("HATA: dosyadan hiç satır okunamadı.", file=sys.stderr)
        return 1

    conn = baglan(args.db)
    try:
        if not conn.execute("SELECT 1 FROM albums LIMIT 1").fetchone():
            print(
                "HATA: albums tablosu boş. Önce kutuphane_tara.py çalıştırılmalı.",
                file=sys.stderr,
            )
            return 1
        ozet = iceri_aktar(conn, satirlar, kaynak, kuru=args.kuru)
    finally:
        conn.close()

    ozet.tarihsiz = tarihsiz
    ozet.yazdir()
    if args.kuru:
        print("(kuru çalışma — veritabanına yazılmadı)")
    if ozet.eslesmeyen:
        rapor_yaz(ozet.eslesmeyen, args.rapor)
        print(f"Eşleşmeyen dinlemeler: {args.rapor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
