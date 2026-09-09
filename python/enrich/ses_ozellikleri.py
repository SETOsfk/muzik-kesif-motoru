"""librosa ile ses öznitelikleri — albüm başına özet.

Yavaş adım, ayrı çalışır (görev listesinde de öyle yazıyor). Yükü sınırlı tutmak
için her parçanın tamamı değil, ortasından bir kesit analiz edilir: intro/outro
albümün karakterini temsil etmez, ortadaki 60 saniye eder. `--sure 0` ile tam
parça analizi açılabilir.

Öznitelikler (veri sözleşmesi):
  tempo_medyan       parça tempolarının medyanı (BPM)
  tempo_iqr          tempo çeyrekler açıklığı — albüm içi tempo tutarlılığı
  dinamik_aralik     RMS'in 95. ve 5. yüzdeliği arası (dB) — kompresyon/nefes
  nabiz_netligi      tempogram tepe/ortalama oranı — tek ve net bir nabız var mı
  vurus_degiskenligi vuruş aralıklarının değişim katsayısı — tempo oturuyor mu

  spektral_merkez    spektral ağırlık merkezi medyanı (Hz) — parlaklık

DİKKAT: nabiz_netligi ve vurus_degiskenligi nabız DÜZENLİLİĞİNİ ölçer, teknik
zorluğu değil. Meshuggah polritmik olarak yaşayan en karmaşık gruplardan biri
ama metronomik olarak katı olduğu için "düzenli" çıkar (ölçüldü: vuruş
değişkenliği 0.028 — Michael Jackson 0.019, Animals As Leaders 0.068).
"İyi davulcu" sorusunun cevabı burada DEĞİL; bkz. karar günlüğü.

Kaldığı yerden devam eder: `audio_features` tablosunda satırı olan albüme
dokunulmaz. Parça yolları `dosyalar` tablosundan gelir, kütüphane yeniden
taranmaz.

Kullanım:
    python -m python.enrich.ses_ozellikleri --isci 4
    python -m python.enrich.ses_ozellikleri --limit 50 --sure 30
"""

from __future__ import annotations

import argparse
import sqlite3
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

from python.db import VARSAYILAN_DB, baglan

ORNEKLEME = 22050          # tempo/centroid için fazlası gereksiz, yarı hız iki kat hız
VARSAYILAN_SURE = 60.0     # saniye, parçanın ortasından


@dataclass(frozen=True)
class ParcaOzellik:
    tempo: float
    dinamik_aralik: float
    nabiz_netligi: float
    vurus_degiskenligi: float
    spektral_merkez: float


# --------------------------------------------------------------------------- #
# Tek parça analizi (librosa gerektirir)
# --------------------------------------------------------------------------- #

def parca_analiz(yol: str, sure: float = VARSAYILAN_SURE) -> ParcaOzellik | None:
    """Tek parçayı analiz et. Okunamayan dosyada None."""
    try:
        import librosa
        import numpy as np
    except ImportError as hata:  # pragma: no cover - ortam sorunu
        raise SystemExit(
            "librosa/numpy kurulu değil: pip install -r requirements.txt"
        ) from hata

    try:
        toplam = librosa.get_duration(path=yol)
        if sure and toplam > sure:
            baslangic = max(0.0, (toplam - sure) / 2)  # ortadan kesit
            y, sr = librosa.load(yol, sr=ORNEKLEME, mono=True, offset=baslangic, duration=sure)
        else:
            y, sr = librosa.load(yol, sr=ORNEKLEME, mono=True)
    except Exception as hata:  # bozuk dosya, desteklenmeyen kodek
        print(f"  okunamadı: {yol} — {hata}", file=sys.stderr)
        return None

    if y.size == 0 or not np.any(np.isfinite(y)):
        return None

    onset = librosa.onset.onset_strength(y=y, sr=sr)
    # librosa 0.10'da beat.tempo → feature.tempo'ya taşındı; eski ad hâlâ var ama
    # uyarı basıyor. Doğrudan feature.tempo'yu ara, yoksa eskisine düş.
    tempo_islevi = getattr(librosa.feature, "tempo", None) or librosa.beat.tempo
    tempo = float(np.atleast_1d(tempo_islevi(onset_envelope=onset, sr=sr))[0])

    rms = librosa.feature.rms(y=y)[0]
    rms = rms[rms > 0]
    if rms.size:
        ust, alt = np.percentile(rms, 95), np.percentile(rms, 5)
        dinamik = float(20 * np.log10(ust / alt)) if alt > 0 else 0.0
    else:
        dinamik = 0.0

    # Nabız netliği: tempogramın tepe/ortalama oranı. Entropi denendi ve ELENDİ —
    # tüm türlerde 0.88'e sıkışıyordu (Eminem 0.892, Casiopea 0.879, Gojira 0.891),
    # yani hiçbir şey ayırt etmiyordu. Tepe/ortalama gerçekten ayırıyor.
    tempogram = librosa.feature.tempogram(onset_envelope=onset, sr=sr)
    dagilim = np.mean(np.abs(tempogram), axis=1)
    ortalama = float(dagilim.mean())
    nabiz_netligi = float(dagilim.max() / ortalama) if ortalama > 0 else 0.0

    # Vuruş değişkenliği: vuruş aralıklarının değişim katsayısı. Tempo oturmuşsa
    # düşük, metre değişiyorsa/serbestse yüksek.
    try:
        _, vuruslar = librosa.beat.beat_track(onset_envelope=onset, sr=sr, units="time")
        araliklar = np.diff(vuruslar)
        vurus_degiskenligi = (
            float(np.std(araliklar) / np.mean(araliklar))
            if araliklar.size > 2 and np.mean(araliklar) > 0
            else 0.0
        )
    except Exception:
        vurus_degiskenligi = 0.0

    merkez = float(np.median(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))

    return ParcaOzellik(
        tempo=tempo,
        dinamik_aralik=dinamik,
        nabiz_netligi=nabiz_netligi,
        vurus_degiskenligi=vurus_degiskenligi,
        spektral_merkez=merkez,
    )


def _isci(arguman: tuple[str, str, float]) -> tuple[str, str, ParcaOzellik | None]:
    album_id, yol, sure = arguman
    return album_id, yol, parca_analiz(yol, sure)


# --------------------------------------------------------------------------- #
# Albüm özeti (saf — librosa'sız test edilebilir)
# --------------------------------------------------------------------------- #

def _iqr(degerler: list[float]) -> float:
    if len(degerler) < 2:
        return 0.0
    sirali = sorted(degerler)
    # statistics.quantiles n=4 → [Q1, Q2, Q3]
    q1, _, q3 = statistics.quantiles(sirali, n=4, method="inclusive")
    return float(q3 - q1)


def album_ozeti(parcalar: list[ParcaOzellik]) -> dict[str, float] | None:
    """Parça özniteliklerini albüm düzeyine indir (medyan + tempo IQR)."""
    parcalar = [p for p in parcalar if p is not None]
    if not parcalar:
        return None
    tempolar = [p.tempo for p in parcalar]
    return {
        "tempo_medyan": round(statistics.median(tempolar), 3),
        "tempo_iqr": round(_iqr(tempolar), 3),
        "dinamik_aralik": round(statistics.median(p.dinamik_aralik for p in parcalar), 3),
        "nabiz_netligi": round(statistics.median(p.nabiz_netligi for p in parcalar), 4),
        "vurus_degiskenligi": round(
            statistics.median(p.vurus_degiskenligi for p in parcalar), 5
        ),
        "spektral_merkez": round(statistics.median(p.spektral_merkez for p in parcalar), 2),
    }


def ozeti_yaz(conn: sqlite3.Connection, album_id: str, ozet: dict[str, float]) -> None:
    with conn:
        conn.execute(
            """
            INSERT INTO audio_features
                (album_id, tempo_medyan, tempo_iqr, dinamik_aralik,
                 nabiz_netligi, vurus_degiskenligi, spektral_merkez)
            VALUES (:album_id, :tempo_medyan, :tempo_iqr, :dinamik_aralik,
                    :nabiz_netligi, :vurus_degiskenligi, :spektral_merkez)
            ON CONFLICT(album_id) DO UPDATE SET
                tempo_medyan       = excluded.tempo_medyan,
                tempo_iqr          = excluded.tempo_iqr,
                dinamik_aralik     = excluded.dinamik_aralik,
                nabiz_netligi      = excluded.nabiz_netligi,
                vurus_degiskenligi = excluded.vurus_degiskenligi,
                spektral_merkez    = excluded.spektral_merkez
            """,
            {"album_id": album_id, **ozet},
        )


# --------------------------------------------------------------------------- #
# Yürütme
# --------------------------------------------------------------------------- #

def isler(
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    yenile: bool = False,
    sure: float = VARSAYILAN_SURE,
    isci: int = 1,
    parca_basina: int | None = None,
) -> dict[str, int]:
    sorgu = """
        SELECT d.album_id, d.yol
          FROM dosyalar d
         WHERE 1 = 1
    """
    if not yenile:
        sorgu += " AND d.album_id NOT IN (SELECT album_id FROM audio_features)"
    sorgu += " ORDER BY d.album_id, d.yol"

    isler_: dict[str, list[str]] = {}
    for satir in conn.execute(sorgu):
        isler_.setdefault(satir["album_id"], []).append(satir["yol"])
    if limit:
        isler_ = dict(list(isler_.items())[:limit])
    if parca_basina:  # her albümden en fazla N parça — hızlı ilk tur için
        isler_ = {a: y[:parca_basina] for a, y in isler_.items()}

    gorevler = [(album_id, yol, sure) for album_id, yollar in isler_.items() for yol in yollar]
    sayac = {"album": len(isler_), "parca": len(gorevler), "basarisiz": 0, "yazilan": 0}
    if not gorevler:
        return sayac

    sonuclar: dict[str, list[ParcaOzellik]] = {album_id: [] for album_id in isler_}
    tamamlanan = 0

    def kaydet(album_id: str, ozellik: ParcaOzellik | None) -> None:
        nonlocal tamamlanan
        tamamlanan += 1
        if ozellik is None:
            sayac["basarisiz"] += 1
        else:
            sonuclar[album_id].append(ozellik)
        if tamamlanan % 20 == 0 or tamamlanan == len(gorevler):
            print(f"  {tamamlanan}/{len(gorevler)} parça", file=sys.stderr)

    if isci > 1:
        with ProcessPoolExecutor(max_workers=isci) as havuz:
            gelecekler = {havuz.submit(_isci, gorev): gorev for gorev in gorevler}
            for gelecek in as_completed(gelecekler):
                album_id, _, ozellik = gelecek.result()
                kaydet(album_id, ozellik)
    else:
        for gorev in gorevler:
            album_id, _, ozellik = _isci(gorev)
            kaydet(album_id, ozellik)

    for album_id, parcalar in sonuclar.items():
        ozet = album_ozeti(parcalar)
        if ozet:
            ozeti_yaz(conn, album_id, ozet)
            sayac["yazilan"] += 1

    return sayac


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="librosa ses öznitelikleri.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--limit", type=int, help="en fazla kaç albüm")
    ayristirici.add_argument("--yenile", action="store_true")
    ayristirici.add_argument(
        "--sure", type=float, default=VARSAYILAN_SURE,
        help="parça başına analiz edilecek saniye (0 = tamamı)",
    )
    ayristirici.add_argument("--isci", type=int, default=1, help="paralel süreç sayısı")
    ayristirici.add_argument(
        "--parca-basina", type=int, help="albüm başına en fazla kaç parça analiz edilsin"
    )
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        sayac = isler(
            conn,
            limit=args.limit,
            yenile=args.yenile,
            sure=args.sure,
            isci=max(1, args.isci),
            parca_basina=args.parca_basina,
        )
    finally:
        conn.close()

    print(f"Albüm            : {sayac['album']}")
    print(f"Analiz edilen parça: {sayac['parca']} (başarısız: {sayac['basarisiz']})")
    print(f"Özeti yazılan albüm: {sayac['yazilan']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
