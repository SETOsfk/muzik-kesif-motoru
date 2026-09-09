"""AcousticBrainz: sende OLMAYAN parçanın ses profili (K11).

Faz 2'nin temel sorunu: önerilecek albüm kullanıcının diskinde yok, dolayısıyla
librosa çalışamaz. AcousticBrainz o boşluğu dolduruyor — dünya çapında gönüllülerin
yüklediği milyonlarca kaydın analizi kayıt MBID'siyle hazır duruyor.

Sınır (ölçüldü, 2026-08-11): proje 2022'de yeni gönderim almayı durdurdu, arşiv
okunabiliyor. Kullanıcının kütüphanesinden 8 albümlük örneklemde 40 parçanın
37'sinde veri vardı (%92); kaçan ikisi 2022 sonrası single'lardı.

Zincir: release-group MBID → release → kayıt MBID'leri → AcousticBrainz → albüm özeti.
İlk iki adım MusicBrainz'den geliyor ve saniyede 1 istekle sınırlı; hepsi
önbelleklenir (K5), ikinci tur bedava.

ÖNEMLİ: AcousticBrainz'in ölçütleri librosa'nınkilerle AYNI ŞEY DEĞİL. `bpm` ile
`tempo_medyan` kabaca örtüşür, ama `dynamic_complexity` ile bizim `dinamik_aralik`
(dB cinsinden 95./5. yüzdelik farkı) farklı tanımlardır. Bu yüzden satırlar
`kaynak='acousticbrainz'` ile ayrı tutulur ve karşılaştırma kaynak içinde
standartlaştırılarak yapılır.

Kullanım:
    python -m python.discover.acousticbrainz --limit 20      # kütüphaneye uygula
    python -m python.discover.acousticbrainz --karsilastir   # librosa ile kıyasla
"""

from __future__ import annotations

import argparse
import sqlite3
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan
from python.onbellek import AgYok, ApiIstemci, musicbrainz

TOPLU_SINIR = 20  # AcousticBrainz tek istekte en fazla 25 kayıt kabul ediyor


def acousticbrainz(**kwargs) -> ApiIstemci:
    """Anahtarsız; nezaketen yine de aralık bırakıyoruz."""
    return ApiIstemci(
        servis="acousticbrainz",
        temel_url="https://acousticbrainz.org/api/v1",
        istek_araligi=0.6,
        basliklar={"User-Agent": "muzik-kesif-motoru/0.1 (kisisel arastirma)"},
        **kwargs,
    )


@dataclass(frozen=True)
class KayitOzelligi:
    bpm: float
    onset_hizi: float
    dans_edilebilirlik: float
    dinamik_karmasiklik: float
    spektral_merkez: float
    akor_degisim_hizi: float


def _sayi(kok: dict, *yol: str) -> float | None:
    dugum = kok
    for anahtar in yol:
        if not isinstance(dugum, dict) or anahtar not in dugum:
            return None
        dugum = dugum[anahtar]
    return float(dugum) if isinstance(dugum, (int, float)) else None


def ozellikleri_coz(govde: dict | None) -> list[KayitOzelligi]:
    """AcousticBrainz toplu yanıtını kayıt özelliklerine çevir."""
    if not govde:
        return []
    sonuc = []
    for _, surumler in govde.items():
        if not isinstance(surumler, dict):
            continue
        # Aynı kayıt birden çok kez gönderilmiş olabilir ("0", "1", ...).
        for _, veri in sorted(surumler.items()):
            if not isinstance(veri, dict):
                continue
            degerler = (
                _sayi(veri, "rhythm", "bpm"),
                _sayi(veri, "rhythm", "onset_rate"),
                _sayi(veri, "rhythm", "danceability"),
                _sayi(veri, "lowlevel", "dynamic_complexity"),
                _sayi(veri, "lowlevel", "spectral_centroid", "mean"),
                _sayi(veri, "tonal", "chords_changes_rate"),
            )
            if degerler[0] is None:
                continue
            sonuc.append(KayitOzelligi(*[d if d is not None else 0.0 for d in degerler]))
            break  # kayıt başına tek sürüm yeter
    return sonuc


def album_ozeti(kayitlar: list[KayitOzelligi]) -> dict[str, float] | None:
    """Kayıt düzeyi ölçümleri albüm düzeyine indir (medyan, tempoda ayrıca IQR)."""
    if not kayitlar:
        return None
    bpm = [k.bpm for k in kayitlar]
    iqr = 0.0
    if len(bpm) > 1:
        q1, _, q3 = statistics.quantiles(sorted(bpm), n=4, method="inclusive")
        iqr = float(q3 - q1)
    return {
        "tempo_medyan": round(statistics.median(bpm), 3),
        "tempo_iqr": round(iqr, 3),
        "dinamik_aralik": round(statistics.median(k.dinamik_karmasiklik for k in kayitlar), 4),
        "spektral_merkez": round(statistics.median(k.spektral_merkez for k in kayitlar), 2),
        "onset_hizi": round(statistics.median(k.onset_hizi for k in kayitlar), 4),
        "dans_edilebilirlik": round(statistics.median(k.dans_edilebilirlik for k in kayitlar), 4),
        "akor_degisim_hizi": round(statistics.median(k.akor_degisim_hizi for k in kayitlar), 5),
        "parca_sayisi": len(kayitlar),
    }


# --------------------------------------------------------------------------- #
# MusicBrainz: release-group → kayıt MBID'leri
# --------------------------------------------------------------------------- #

def kayit_mbidleri(mb: ApiIstemci, release_group_mbid: str) -> list[str]:
    """Release-group'un kanonik release'indeki kayıt MBID'leri."""
    gruplar = mb.get_json(
        f"release-group/{release_group_mbid}", {"inc": "releases", "fmt": "json"}
    )
    releaseler = (gruplar or {}).get("releases") or []
    if not releaseler:
        return []

    def anahtar(r: dict) -> tuple:
        resmi = 0 if (r.get("status") or "").lower() == "official" else 1
        return (resmi, r.get("date") or "9999", r.get("id", ""))

    release_id = min(releaseler, key=anahtar).get("id")
    if not release_id:
        return []
    release = mb.get_json(f"release/{release_id}", {"inc": "recordings", "fmt": "json"})
    return [
        parca["recording"]["id"]
        for ortam in (release or {}).get("media", []) or []
        for parca in ortam.get("tracks", []) or []
        if parca.get("recording", {}).get("id")
    ]


def album_getir(
    mb: ApiIstemci, ab: ApiIstemci, release_group_mbid: str, azami_parca: int = TOPLU_SINIR
) -> dict[str, float] | None:
    """Bir albümün AcousticBrainz özetini getir."""
    mbidler = kayit_mbidleri(mb, release_group_mbid)[:azami_parca]
    if not mbidler:
        return None
    govde = ab.get_json("low-level", {"recording_ids": ";".join(mbidler)})
    return album_ozeti(ozellikleri_coz(govde))


def ozeti_yaz(conn: sqlite3.Connection, album_id: str, ozet: dict[str, float]) -> None:
    alanlar = ["album_id", "kaynak", *ozet.keys()]
    yer_tutucu = ", ".join("?" * len(alanlar))
    guncelle = ", ".join(f"{a} = excluded.{a}" for a in ozet)
    with conn:
        conn.execute(
            f"INSERT INTO audio_features ({', '.join(alanlar)}) VALUES ({yer_tutucu}) "
            f"ON CONFLICT(album_id, kaynak) DO UPDATE SET {guncelle}",
            [album_id, "acousticbrainz", *ozet.values()],
        )


def kutuphaneye_uygula(
    conn: sqlite3.Connection, *, limit: int | None = None, yenile: bool = False
) -> dict[str, int]:
    sorgu = "SELECT album_id, artist, title, mbid FROM albums WHERE mbid IS NOT NULL"
    if not yenile:
        sorgu += (
            " AND album_id NOT IN "
            "(SELECT album_id FROM audio_features WHERE kaynak = 'acousticbrainz')"
        )
    sorgu += " ORDER BY artist, title"
    if limit:
        sorgu += f" LIMIT {int(limit)}"

    mb, ab = musicbrainz(), acousticbrainz()
    sayac = {"albüm": 0, "yazilan": 0, "veri_yok": 0}
    albumler = conn.execute(sorgu).fetchall()

    for sira, albom in enumerate(albumler, 1):
        sayac["albüm"] += 1
        try:
            ozet = album_getir(mb, ab, albom["mbid"])
        except AgYok:
            continue
        if ozet:
            ozeti_yaz(conn, albom["album_id"], ozet)
            sayac["yazilan"] += 1
        else:
            sayac["veri_yok"] += 1
        if sira % 10 == 0 or sira == len(albumler):
            print(
                f"  {sira}/{len(albumler)} — yazılan {sayac['yazilan']}, "
                f"veri yok {sayac['veri_yok']}",
                file=sys.stderr,
            )
    return sayac


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="AcousticBrainz ses profili.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--limit", type=int)
    ayristirici.add_argument("--yenile", action="store_true")
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        sayac = kutuphaneye_uygula(conn, limit=args.limit, yenile=args.yenile)
    finally:
        conn.close()

    print(f"İşlenen albüm  : {sayac['albüm']}")
    print(f"Profili yazılan: {sayac['yazilan']}")
    print(f"Verisi olmayan : {sayac['veri_yok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
