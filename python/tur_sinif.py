"""Tür sınıflandırıcı — FMA ile eğitilmiş, DENETİMLİ.

## Neden gerekti

Sıfır-atışlı CLAP denendi ve YETMEDİ (`etiket_clap.py`). Sebep ölçüldü: istem
yanlılığı. "anadolu" istemi tüm kütüphanede ortalama +0.506, "türk rock" +0.505
alıyor — Eminem'e de A-Ha'ya da yapışıyorlar. İstem başına standartlaştırma
bazılarını düzeltti (Casiopea: hard rock → funk) ama başkalarını bozdu
(TOOL → klasik). Altı albümde üç doğru; bir etiket sisteminin altına imza
atılacak oran değil.

Eksik olan şey denetimdi: CLAP bizim etiket kümemiz için hiç örnek görmedi.

## Kaynak

FMA (Free Music Archive) — kullanıcının önerdiği veri kümesi. `fma_metadata.zip`
yalnız 342 MB ve SES İNDİRMEYİ GEREKTİRMİYOR: içinde 106.574 parçanın librosa
öznitelikleri (518 sütun) ve tür etiketleri var. Metadata CC BY 4.0.

Etik not: The Atlantic'in haberi FMA sesinin ticari AI müzik modellerini
eğitmekte, sanatçılara sorulmadan kullanılmasıyla ilgiliydi. Burada ses
indirilmiyor, üretken model eğitilmiyor, hiçbir şey dağıtılmıyor — yalnız
açık lisanslı öznitelik tablosundan kişisel keşif için sınıflandırıcı
öğreniliyor.

## Öznitelikler birebir aynı olmak zorunda

FMA'nın 518 sütunu 11 aileden ve her aile için 7 istatistik (kurtosis, max,
mean, median, min, skew, std). Bizim kliplerimizden AYNI hesap yapılmazsa
sınıflandırıcı eğitildiği uzaydan farklı bir uzayda tahmin eder ve sessizce
saçmalar. `oznitelikler()` bu düzeni birebir izliyor.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

FMA_KLASOR = Path("data/dis/fma_metadata")
MODEL_DOSYA = Path("data/dis/tur_sinif.joblib")

#: (aile, boyut) — FMA'nın features.csv düzeni. Sıra ÖNEMLİ.
AILELER: tuple[tuple[str, int], ...] = (
    ("chroma_cens", 12), ("chroma_cqt", 12), ("chroma_stft", 12),
    ("mfcc", 20), ("rmse", 1), ("spectral_bandwidth", 1),
    ("spectral_centroid", 1), ("spectral_contrast", 7),
    ("spectral_rolloff", 1), ("tonnetz", 6), ("zcr", 1),
)

#: FMA'nın kullandığı yedi istatistik, alfabetik — sütun sırası bu.
ISTATISTIKLER = ("kurtosis", "max", "mean", "median", "min", "skew", "std")


def _istatistikler(x: np.ndarray) -> np.ndarray:
    """(boyut, kare) dizisinden (boyut, 7) istatistik — FMA sırasıyla."""
    from scipy import stats

    return np.column_stack([
        stats.kurtosis(x, axis=1), np.max(x, axis=1), np.mean(x, axis=1),
        np.median(x, axis=1), np.min(x, axis=1), stats.skew(x, axis=1),
        np.std(x, axis=1),
    ])


def oznitelikler(y: np.ndarray, sr: int) -> np.ndarray:
    """FMA'nın 518 özniteliğini birebir aynı düzende hesapla."""
    import librosa

    cqt = np.abs(librosa.cqt(y, sr=sr, n_bins=7 * 12, bins_per_octave=12))
    stft = np.abs(librosa.stft(y))
    parcalar = []
    for aile, _boyut in AILELER:
        if aile == "chroma_cens":
            v = librosa.feature.chroma_cens(C=cqt, n_chroma=12)
        elif aile == "chroma_cqt":
            v = librosa.feature.chroma_cqt(C=cqt, n_chroma=12)
        elif aile == "chroma_stft":
            v = librosa.feature.chroma_stft(S=stft**2, n_chroma=12)
        elif aile == "mfcc":
            mel = librosa.feature.melspectrogram(S=stft**2, sr=sr)
            v = librosa.feature.mfcc(S=librosa.power_to_db(mel), n_mfcc=20)
        elif aile == "rmse":
            v = librosa.feature.rms(S=stft)
        elif aile == "spectral_bandwidth":
            v = librosa.feature.spectral_bandwidth(S=stft)
        elif aile == "spectral_centroid":
            v = librosa.feature.spectral_centroid(S=stft)
        elif aile == "spectral_contrast":
            v = librosa.feature.spectral_contrast(S=stft, n_bands=6)
        elif aile == "spectral_rolloff":
            v = librosa.feature.spectral_rolloff(S=stft)
        elif aile == "tonnetz":
            v = librosa.feature.tonnetz(
                chroma=librosa.feature.chroma_cqt(C=cqt, n_chroma=12))
        else:  # zcr
            v = librosa.feature.zero_crossing_rate(y, frame_length=2048,
                                                   hop_length=512)
        parcalar.append(_istatistikler(np.atleast_2d(v)))
    return np.concatenate([p.T.ravel() for p in parcalar])


def sutun_sirasi() -> list[tuple[str, str, int]]:
    """`oznitelikler()` çıktısının FMA sütunlarına karşılığı."""
    sira = []
    for aile, boyut in AILELER:
        for ist in ISTATISTIKLER:
            for i in range(1, boyut + 1):
                sira.append((aile, ist, i))
    return sira


def fma_veri(*, asgari_ornek: int = 800) -> tuple[pd.DataFrame, pd.Series]:
    """FMA öznitelikleri + üst düzey tür etiketi.

    `asgari_ornek`: az örnekli türler atılıyor. Dengesiz sınıf, doğruluk
    sayısını şişirip işe yaramaz bir model üretir.
    """
    ozellik = pd.read_csv(FMA_KLASOR / "features.csv", index_col=0,
                          header=[0, 1, 2])
    parcalar = pd.read_csv(FMA_KLASOR / "tracks.csv", index_col=0,
                           header=[0, 1])
    etiket = parcalar[("track", "genre_top")].dropna()
    ortak = ozellik.index.intersection(etiket.index)
    X, y = ozellik.loc[ortak], etiket.loc[ortak]
    sayim = y.value_counts()
    tutulan = sayim[sayim >= asgari_ornek].index
    maske = y.isin(tutulan)
    return X[maske], y[maske]


def egit(*, tohum: int = 0) -> dict:
    """Sınıflandırıcıyı eğit ve DÜRÜST doğruluk raporla.

    Sanatçı sızıntısına dikkat: FMA'da aynı sanatçının çok parçası var ve
    rastgele bölme, aynı sanatçıyı hem eğitime hem teste koyup doğruluğu
    şişirir. Bölme SANATÇIYA göre yapılıyor.
    """
    import joblib
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import classification_report
    from sklearn.model_selection import GroupShuffleSplit

    X, y = fma_veri()
    parcalar = pd.read_csv(FMA_KLASOR / "tracks.csv", index_col=0,
                           header=[0, 1])
    grup = parcalar.loc[X.index, ("artist", "id")].fillna(-1).astype(int)

    bolucu = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=tohum)
    egitim, test = next(bolucu.split(X, y, groups=grup))
    model = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.1, random_state=tohum)
    model.fit(X.iloc[egitim], y.iloc[egitim])

    tahmin = model.predict(X.iloc[test])
    rapor = classification_report(y.iloc[test], tahmin, output_dict=True,
                                  zero_division=0)
    MODEL_DOSYA.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "sutunlar": list(X.columns)}, MODEL_DOSYA)
    return {
        "dogruluk": rapor["accuracy"],
        "makro_f1": rapor["macro avg"]["f1-score"],
        "siniflar": {k: round(v["f1-score"], 3) for k, v in rapor.items()
                     if isinstance(v, dict) and k not in
                     ("macro avg", "weighted avg")},
        "egitim": len(egitim), "test": len(test),
    }


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--egit", action="store_true")
    ayristirici.add_argument("--uygula", action="store_true")
    ayristirici.add_argument("--limit", type=int)
    args = ayristirici.parse_args(argv)

    if args.uygula:
        from python.db import baglan

        conn = baglan("data/db/kesif.sqlite")
        try:
            satirlar = tahmin_et(conn, limit=args.limit)
            print(f"{tahminleri_yaz(conn, satirlar)} tür tahmini yazıldı")
        finally:
            conn.close()
        return 0

    if args.egit:
        print("FMA yükleniyor…", file=sys.stderr)
        sonuc = egit()
        print(f"eğitim {sonuc['egitim']} · test {sonuc['test']}")
        print(f"doğruluk {sonuc['dogruluk']:.3f} · makro F1 {sonuc['makro_f1']:.3f}")
        for tur, f1 in sorted(sonuc["siniflar"].items(), key=lambda x: -x[1]):
            print(f"  {tur:<18} F1 {f1:.3f}")
    return 0



# --------------------------------------------------------------------------- #
# Kendi kliplerimize uygulama
# --------------------------------------------------------------------------- #

#: FMA öznitelikleri 44.1 kHz'te çıkarılmış. Bizim önbelleğimiz 22.05 kHz ve
#: spektral öznitelikler (merkez, bant genişliği, rolloff) örnekleme hızıyla
#: ÖLÇEKLENİYOR — aynı ses 22 kHz'te farklı sayı verir. Eğitildiği uzayda
#: tahmin etmek için yeniden örnekleme şart.
FMA_ORNEKLEME = 44100


def klip_oznitelikleri(onizleme_url: str) -> np.ndarray | None:
    """Önbellekteki stem'leri toplayıp 44.1 kHz'te FMA özniteliklerini çıkar."""
    import hashlib

    import librosa
    import soundfile as sf

    klasor = Path("data/cache/stemler") / hashlib.sha1(
        onizleme_url.encode("utf-8")).hexdigest()[:16]
    if not klasor.exists():
        return None
    parcalar = [
        sf.read(klasor / f"{s}.flac", dtype="float32")[0]
        for s in ("drums", "bass", "other", "vocals")
        if (klasor / f"{s}.flac").exists()
    ]
    if not parcalar:
        return None
    n = min(len(p) for p in parcalar)
    miks = np.sum([p[:n] for p in parcalar], axis=0)
    miks = miks / (float(np.abs(miks).max()) or 1.0)
    miks = librosa.resample(miks, orig_sr=22050, target_sr=FMA_ORNEKLEME)
    try:
        return oznitelikler(miks, FMA_ORNEKLEME)
    except Exception:
        return None


def tahmin_et(conn, *, limit: int | None = None) -> list[tuple[str, str, float]]:
    """(album_id, tür, olasılık) — kütüphane ve adaylar için."""
    import joblib

    if not MODEL_DOSYA.exists():
        raise SystemExit("model yok: python -m python.tur_sinif --egit")
    paket = joblib.load(MODEL_DOSYA)
    model, sutunlar = paket["model"], paket["sutunlar"]

    hedefler = conn.execute(
        """SELECT DISTINCT album_id, onizleme_url FROM stem_profili
            WHERE onizleme_url IS NOT NULL"""
    ).fetchall()
    if limit:
        hedefler = hedefler[:limit]

    sonuc = []
    for sira, (album_id, url) in enumerate(hedefler, 1):
        x = ozgun_oznitelikler(url)
        if x is None or len(x) != len(sutunlar):
            continue
        p = model.predict_proba(pd.DataFrame([x], columns=sutunlar))[0]
        i = int(np.argmax(p))
        sonuc.append((album_id, str(model.classes_[i]), float(p[i])))
        if sira % 50 == 0:
            print(f"  {sira}/{len(hedefler)}", file=sys.stderr)
    return sonuc


def tahminleri_yaz(conn, satirlar) -> int:
    with conn:
        conn.execute("DELETE FROM album_etiket WHERE kaynak = 'fma'")
        conn.executemany(
            "INSERT OR REPLACE INTO album_etiket "
            "(album_id, eksen, etiket, kaynak, skor) VALUES (?,'fma_tur',?,'fma',?)",
            [(a, t, round(p, 4)) for a, t, p in satirlar],
        )
    return len(satirlar)


#: Özgün önizleme önbelleği. Stem önbelleği 22.05 kHz mono (disk tasarrufu) ve
#: FMA öznitelikleri için YETMİYOR: Nyquist 11 kHz olduğu için tizde hiçbir şey
#: yok, `spectral_rolloff max` 4.2 kHz çıkıyor (FMA ortalaması 9.4 kHz) ve en
#: üst `spectral_contrast` bandı boş sessizlik görüp uçuk değer veriyor.
#: Ölçüldü: 518 öznitelikten 25'i |z|>3 sapıyor ve sınıflandırıcı her şeye
#: "Experimental" diyor.
#:
#: Ayrıca stem TOPLAMI özgün miks değil — Demucs artığı spektrumu değiştiriyor.
#: Burada klip olduğu gibi, ayrıştırılmadan ve tam bant genişliğinde tutuluyor.
ONIZLEME_ONBELLEK = Path("data/cache/onizleme")


def onizleme_indir(url: str) -> Path | None:
    """Özgün 30 sn klibi diske al (tam bant, ayrıştırılmamış)."""
    import hashlib

    import requests

    ONIZLEME_ONBELLEK.mkdir(parents=True, exist_ok=True)
    dosya = ONIZLEME_ONBELLEK / f"{hashlib.sha1(url.encode()).hexdigest()[:16]}.m4a"
    if dosya.exists():
        return dosya
    try:
        yanit = requests.get(url, timeout=45)
        yanit.raise_for_status()
    except Exception:
        return None
    dosya.write_bytes(yanit.content)
    return dosya


def ozgun_oznitelikler(url: str) -> np.ndarray | None:
    """Özgün klipten FMA özniteliklerini 44.1 kHz'te çıkar."""
    import librosa

    dosya = onizleme_indir(url)
    if dosya is None:
        return None
    try:
        y, _ = librosa.load(dosya, sr=FMA_ORNEKLEME, mono=True)
        if y.size < FMA_ORNEKLEME:
            return None
        return oznitelikler(y, FMA_ORNEKLEME)
    except Exception:
        return None

if __name__ == "__main__":
    raise SystemExit(main())
