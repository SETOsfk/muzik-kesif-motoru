"""İcra profili — davul, bas, gitar/klavye ve vokal, dört stem birden.

`davul_profili.py`'nin genelleştirilmiş hâli. İki şey değişti:

**1. Albüm başına TEK ayrıştırma.** Demucs zaten dört stem'i birlikte üretiyor
(drums / bass / other / vocals). Rol rol ayrı çalıştırmak aynı klibi dört kez
ayrıştırmak demekti — dört kat israf. Artık bir klip bir kez ayrışıyor, dört
profil birden çıkıyor.

**2. Her stem'e kendi ölçütü.** Davulda perde yok, vokalde tekme/trampet yok.
Ortak ölçütler her stem'de hesaplanır, enstrümana özgü olanlar yalnız ilgili
stem'de:

  ortak      nota_vurus, dinamik_db, parlaklik, harmonik_pay, zcr, sustain
  davul      izgara_entropi, tekme_payi, trampet_payi, zil_payi
  perdeli    perde_medyan, perde_araligi, vibrato_hizi   (bas, vokal, gitar)

Rol → stem eşlemesi: davulcu davul stem'inden, basçı bas stem'inden, gitarist
ve klavyeci "other" stem'inden (Demucs bu ikisini ayırmıyor), vokalist vokal
stem'inden değerlendirilir.

NEDEN STEM: `ses_ozellikleri.py` tüm mikse bakıyor ve icracı karakterini
yakalayamıyor. İki deneme ölçülüp elendi (tempogram entropisi: sekiz sanatçıda
0.878–0.891; HPSS+senkop: Françoise Hardy Meshuggah'tan yüksek). Demucs ile
ayrıştırınca ölçüm müzikal olarak doğru çıktı — Meshuggah zil %62/trampet %17,
Eminem ızgara entropisi 0.755 (programlanmış beat).

Kaynak her zaman 30 sn önizleme: tek kaynak olması karşılaştırmayı geçerli
kılıyor (K11).

Kullanım:
    python -m python.enrich.icra_profili --limit 20
    python -m python.enrich.icra_profili --tum          # bütün kütüphane
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import statistics
import sys
import tempfile
from pathlib import Path

import numpy as np
import requests

from python.db import VARSAYILAN_DB, baglan

CALISMA_ORNEKLEME = 22050

#: Demucs'un ürettiği stem'ler ve hangi rollerin oradan değerlendirileceği.
#: Demucs gitar ile klavyeyi ayırmıyor, ikisi de "other" içinde.
ROL_STEM: dict[str, str] = {
    "drums": "drums",
    "percussion": "drums",
    "bass": "bass",
    "guitar": "other",
    "keyboards": "other",
    "piano": "other",
    "organ": "other",
    "synthesizer": "other",
    "saxophone": "other",
    "trumpet": "other",
    "violin": "other",
    "flute": "other",
    "vocals": "vocals",
    "backing_vocals": "vocals",
}

STEMLER = ("drums", "bass", "other", "vocals")

#: Perde ölçümü yapılacak stem'ler — davulda perde aramak anlamsız.
PERDELI_STEMLER = ("bass", "other", "vocals")

_AYIRICI = None


def _ayirici():
    """Demucs modelini bir kez yükle."""
    global _AYIRICI
    if _AYIRICI is None:
        try:
            import torch
            from demucs.api import Separator
        except ImportError as hata:  # pragma: no cover
            raise SystemExit(
                "demucs kurulu değil: pip install demucs"
            ) from hata
        aygit = "mps" if torch.backends.mps.is_available() else "cpu"
        _AYIRICI = Separator(model="htdemucs", device=aygit, progress=False)
        print(f"  demucs yüklendi (aygıt: {aygit})", file=sys.stderr)
    return _AYIRICI


STEM_ONBELLEK = Path("data/cache/stemler")


def _onbellekten(anahtar: str) -> tuple[dict[str, np.ndarray], int, float] | None:
    """Diske alınmış stem'leri oku. Yoksa None."""
    import soundfile as sf

    klasor = STEM_ONBELLEK / anahtar
    enerji_dosyasi = klasor / "toplam_enerji.txt"
    if not enerji_dosyasi.exists():
        return None
    stemler = {}
    for ad in STEMLER:
        dosya = klasor / f"{ad}.flac"
        if dosya.exists():
            veri, _ = sf.read(dosya, dtype="float32")
            stemler[ad] = veri
    if not stemler:
        return None
    return stemler, CALISMA_ORNEKLEME, float(enerji_dosyasi.read_text())


def _onbellege_yaz(
    anahtar: str, stemler: dict[str, np.ndarray], sr: int, toplam_enerji: float
) -> None:
    """Ayrılmış stem'leri diske al.

    Neden: ayrıştırma maliyetin tamamına yakını (klip başına ~12 sn MPS), ölçüm
    ise saniyenin altında. Öznitelik tasarımı bir kerede oturmuyor — davulda iki
    ölçüt ölçülüp elendi, gitarda `duzluk` elendi. Önbellek olmadan her deneme
    tüm kütüphaneyi yeniden ayrıştırmak demek.

    Çalışma örneklemesinde (22.05 kHz) mono FLAC: albüm başına ~1 MB.
    """
    import librosa
    import soundfile as sf

    klasor = STEM_ONBELLEK / anahtar
    klasor.mkdir(parents=True, exist_ok=True)
    for ad, veri in stemler.items():
        if sr != CALISMA_ORNEKLEME:
            veri = librosa.resample(veri, orig_sr=sr, target_sr=CALISMA_ORNEKLEME)
        sf.write(klasor / f"{ad}.flac", veri, CALISMA_ORNEKLEME, subtype="PCM_16")
    (klasor / "toplam_enerji.txt").write_text(str(toplam_enerji))


def stemleri_ayir(yol: str) -> tuple[dict[str, np.ndarray], int, float] | None:
    """Dört stem + örnekleme + toplam enerji. Tek demucs geçişi."""
    import librosa
    import torch

    ayirici = _ayirici()
    try:
        y, _ = librosa.load(yol, sr=ayirici.samplerate, mono=False)
    except Exception as hata:
        print(f"    okunamadı: {hata}", file=sys.stderr)
        return None
    if y.size == 0:
        return None
    if y.ndim == 1:
        y = np.stack([y, y])

    _, ham = ayirici.separate_tensor(
        torch.tensor(y, dtype=torch.float32), sr=ayirici.samplerate
    )
    stemler = {ad: ham[ad].mean(0).cpu().numpy() for ad in STEMLER if ad in ham}
    toplam_enerji = float((y**2).sum())
    return stemler, ayirici.samplerate, toplam_enerji


# --------------------------------------------------------------------------- #
# Öznitelikler
# --------------------------------------------------------------------------- #

def _perde_ozellikleri(sinyal: np.ndarray, sr: int, stem: str) -> dict[str, float]:
    """Perde medyanı, aralığı ve vibrato hızı — yalnız perdeli stem'lerde.

    `yin` kullanılıyor, `pyin` değil: pyin olasılıksal seslilik kararı veriyor ve
    çok daha yavaş — üç stem'de birden koşunca albüm başına 43 saniye tutuyordu
    (302 albüm = 3,6 saat). yin ile aynı iş yaklaşık beşte bir sürede bitiyor.
    Sesli/sessiz ayrımı için pyin'in olasılığı yerine RMS eşiği ve aralık dışı
    değerlerin atılması kullanılıyor; medyan/aralık gibi dayanıklı istatistikler
    için bu yeterli.

    Frekans aralığı stem'e göre daraltılıyor ki bas stem'inde vokal oktavı,
    vokalde bas oktavı aranmasın.
    """
    import librosa

    aralik = {
        "bass": (librosa.note_to_hz("E1"), librosa.note_to_hz("G3")),
        "vocals": (librosa.note_to_hz("C2"), librosa.note_to_hz("C6")),
        "other": (librosa.note_to_hz("E2"), librosa.note_to_hz("C7")),
    }[stem]

    try:
        f0 = librosa.yin(sinyal, fmin=aralik[0], fmax=aralik[1], sr=sr, frame_length=2048)
        rms = librosa.feature.rms(y=sinyal, frame_length=2048, hop_length=512)[0]
    except Exception:
        return {}

    # Sessiz karelerde yin gürültüden rastgele perde uyduruyor; RMS eşiğiyle ele.
    n = min(f0.size, rms.size)
    f0, rms = f0[:n], rms[:n]
    esik = 0.15 * np.percentile(rms[rms > 0], 90) if np.any(rms > 0) else 0.0
    maske = (rms > esik) & np.isfinite(f0) & (f0 > aralik[0] * 1.01) & (f0 < aralik[1] * 0.99)
    gecerli = f0[maske]
    if gecerli.size < 10:
        return {}

    yarim_ton = 12 * np.log2(gecerli / librosa.note_to_hz("C1"))
    ozellik = {
        "perde_medyan": float(np.median(yarim_ton)),
        "perde_araligi": float(np.percentile(yarim_ton, 95) - np.percentile(yarim_ton, 5)),
    }

    # Vibrato: perde eğrisinin salınım hızı. Sürekli perdeli pasajlarda anlamlı.
    if gecerli.size > 40:
        merkezli = yarim_ton - np.convolve(yarim_ton, np.ones(9) / 9, mode="same")
        isaret_degisimi = np.diff(np.sign(merkezli)) != 0
        sure = gecerli.size * 512 / sr
        ozellik["vibrato_hizi"] = float(isaret_degisimi.sum() / max(1e-6, 2 * sure))
    return ozellik


def _sustain(rms: np.ndarray, onsetler: np.ndarray, sr: int, hop: int = 512) -> float:
    """Notanın kendi tepesine göre ne kadar çınladığı — nota başına ölçülür.

    İlk tasarım "RMS, tepe değerinin %20'sinin üstünde kalan kare oranı" idi ve
    ÖLÇÜLDÜ, ELENDİ: sürekli çalan bir stem'de tanım gereği 1.0 çıkıyor. Alice In
    Chains, Animals As Leaders ve Adam Nitti'nin `other` stem'leri tam 1.00 verdi
    — tavana yapışmış bir ölçüt hiçbir şey ayırmaz. Ölçtüğü şey de yanlıştı:
    "hiç susuyor mu", "nota çınlıyor mu" değil.

    Yeni tanım her onset için ayrı bakar: notanın atağındaki tepe ile bir sonraki
    onset'e kadarki (en çok 300 ms) pencerenin sonundaki enerji oranı. Staccato
    icrada enerji düşer, uzun tutan icrada durur. Nota kendi tepesine göre
    normalize edildiği için yoğun pasaj tek başına oranı şişirmez.
    """
    if onsetler.size < 2 or rms.size == 0:
        return float("nan")
    kare = (onsetler * sr / hop).astype(int)
    en_fazla = int(0.30 * sr / hop)
    atak = max(1, int(0.05 * sr / hop))
    oranlar = []
    for i, bas in enumerate(kare[:-1]):
        son = min(bas + en_fazla, kare[i + 1], rms.size - 1)
        if son - bas < atak + 1:
            continue  # notalar üst üste; bu aralıktan çürüme okunamaz
        tepe = float(rms[bas : bas + atak].max())
        if tepe <= 0:
            continue
        oranlar.append(float(rms[son]) / tepe)
    return float(np.median(oranlar)) if oranlar else float("nan")


def stem_ozellikleri(
    sinyal: np.ndarray, sr: int, stem: str, toplam_enerji: float
) -> dict[str, float] | None:
    """Bir stem'in profili. Ortak ölçütler + stem'e özgü olanlar."""
    import librosa

    if sr != CALISMA_ORNEKLEME:
        sinyal = librosa.resample(sinyal, orig_sr=sr, target_sr=CALISMA_ORNEKLEME)
    sr = CALISMA_ORNEKLEME
    if sinyal.size < sr:
        return None

    enerji = float((sinyal**2).sum())
    enerji_payi = enerji / max(1e-9, toplam_enerji)
    # Stem neredeyse boşsa ölçüm gürültüden ibaret olur — o rolü bu albümde
    # değerlendirmemek, uydurma sayı üretmekten iyidir.
    if enerji_payi < 0.005:
        return None

    zarf = librosa.onset.onset_strength(y=sinyal, sr=sr)
    onsetler = librosa.onset.onset_detect(onset_envelope=zarf, sr=sr, units="time")
    _, vuruslar = librosa.beat.beat_track(onset_envelope=zarf, sr=sr, units="time")
    if len(vuruslar) < 4 or len(onsetler) < 8:
        return None
    ara = float(np.median(np.diff(vuruslar)))
    if ara <= 0:
        return None

    sure = sinyal.size / sr
    ozellik: dict[str, float] = {
        "nota_vurus": len(onsetler) / (sure / ara),
        "tempo": 60.0 / ara,
        "enerji_payi": enerji_payi,
    }

    rms = librosa.feature.rms(y=sinyal)[0]
    dolu = rms[rms > 0]
    if dolu.size:
        ozellik["dinamik_db"] = float(
            20 * np.log10(np.percentile(dolu, 95) / max(1e-9, np.percentile(dolu, 5)))
        )
        # Distorsiyon/ton dokusu. ÜÇ ADAY ÖLÇÜLDÜ, İKİSİ ELENDİ:
        #   duzluk (spektral düzlük) — Demucs kaynak dışı binleri sıfırladığı
        #     için geometrik ortalama çöküyor; sekiz sanatçıda 0.000-0.012.
        #   tepe_orani (tepe/RMS dB) — sıralama distorsiyonla ilgisiz çıktı:
        #     Annihilator (thrash) 17.7 ile EN YÜKSEK, Animals As Leaders 12.9.
        #     30 sn'lik karışık pasajda tepe/RMS aranjman yoğunluğunu ölçüyor.
        #   spektral kontrast — A-Ha (temiz synthpop) 24.2 ile en yüksek,
        #     Annihilator 21.1. Yön yanlış.
        # Ayakta kalan ikisi aşağıda. Sekiz sanatçıda doğru sıralıyorlar
        # (Annihilator 0.774/0.160, A-Ha 0.973/0.039) AMA bu örneklemde
        # ikisi de `parlaklik` ile neredeyse aynı sıralamayı veriyor; "distorsiyon"
        # mu "parlaklık" mı ölçtükleri n=8'de ayrılamıyor. İkisi de SAKLANIYOR,
        # kümeleme ölçütüne alınıp alınmayacakları tüm kütüphanede (n~300)
        # parlaklik kontrol edilerek kısmi korelasyonla karara bağlanacak.
        S = np.abs(librosa.stft(sinyal))
        harmonik, vurmali = librosa.decompose.hpss(S)
        hg, vg = float((harmonik**2).sum()), float((vurmali**2).sum())
        ozellik["harmonik_pay"] = hg / max(1e-9, hg + vg)
        ozellik["zcr"] = float(np.mean(librosa.feature.zero_crossing_rate(sinyal)))
        ozellik["sustain_orani"] = _sustain(rms, onsetler, sr)

    ozellik["parlaklik"] = float(np.median(librosa.feature.spectral_centroid(y=sinyal, sr=sr)[0]))

    if stem == "drums":
        faz = ((onsetler - vuruslar[0]) % (ara * 4)) / (ara * 4)
        hist, _ = np.histogram(faz, bins=16, range=(0, 1))
        p = hist / max(1, hist.sum())
        p = p[p > 0]
        ozellik["izgara_entropi"] = (
            float(-(p * np.log(p)).sum() / np.log(16)) if p.size > 1 else 0.0
        )
        izge = np.abs(librosa.stft(sinyal, n_fft=2048))
        frek = librosa.fft_frequencies(sr=sr, n_fft=2048)
        tekme = float(izge[frek < 120].sum())
        trampet = float(izge[(frek >= 120) & (frek < 2000)].sum())
        zil = float(izge[frek >= 6000].sum())
        toplam = max(1e-9, tekme + trampet + zil)
        ozellik.update(
            tekme_payi=tekme / toplam, trampet_payi=trampet / toplam, zil_payi=zil / toplam
        )
    elif stem in PERDELI_STEMLER:
        ozellik.update(_perde_ozellikleri(sinyal, sr, stem))

    return {a: round(float(d), 4) for a, d in ozellik.items() if np.isfinite(d)}


def klipten_stemler(url: str) -> dict[str, dict[str, float]]:
    """Önizlemeyi indir, dört stem'in profilini birden çıkar.

    Ayrıştırma sonucu diske alınır (K5: aynı iş iki kez yapılmaz). Ölçüt tanımı
    değişirse indirme de ayrıştırma da tekrarlanmaz, yalnız ölçüm koşar.
    """
    anahtar = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]

    ayrisim = _onbellekten(anahtar)
    if ayrisim is None:
        try:
            yanit = requests.get(url, timeout=60)
            yanit.raise_for_status()
        except Exception as hata:
            print(f"    indirilemedi: {hata}", file=sys.stderr)
            return {}
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as dosya:
            dosya.write(yanit.content)
            gecici = dosya.name
        try:
            ayrisim = stemleri_ayir(gecici)
        finally:
            os.unlink(gecici)
        if not ayrisim:
            return {}
        _onbellege_yaz(anahtar, *ayrisim)
        ayrisim = _onbellekten(anahtar) or ayrisim

    stemler, sr, toplam = ayrisim
    sonuc = {}
    for ad, sinyal in stemler.items():
        profil = stem_ozellikleri(sinyal, sr, ad, toplam)
        if profil:
            sonuc[ad] = profil
    return sonuc


# --------------------------------------------------------------------------- #
# Veritabanı
# --------------------------------------------------------------------------- #

TUM_SUTUNLAR = (
    "nota_vurus", "tempo", "enerji_payi", "dinamik_db", "sustain_orani",
    "parlaklik", "harmonik_pay", "zcr", "izgara_entropi", "tekme_payi", "trampet_payi",
    "zil_payi", "perde_medyan", "perde_araligi", "vibrato_hizi",
)


def profil_yaz(conn: sqlite3.Connection, album_id: str, stem: str,
               profil: dict[str, float], onizleme: str | None,
               tur: str = "album") -> None:
    alanlar = ["album_id", "tur", "stem", "onizleme_url",
               *[a for a in TUM_SUTUNLAR if a in profil]]
    degerler = [album_id, tur, stem, onizleme,
                *[profil[a] for a in TUM_SUTUNLAR if a in profil]]
    guncelle = ", ".join(f"{a} = excluded.{a}" for a in alanlar[3:])
    with conn:
        conn.execute(
            f"INSERT INTO stem_profili ({', '.join(alanlar)}) "
            f"VALUES ({', '.join('?' * len(alanlar))}) "
            f"ON CONFLICT(album_id, stem) DO UPDATE SET {guncelle}",
            degerler,
        )


def calistir(
    conn: sqlite3.Connection, *, limit: int | None = None, yenile: bool = False,
    adaylar: bool = False,
) -> dict[str, int]:
    """`adaylar=True` ise sahip OLUNMAYAN aday albümleri profiller.

    Neden gerekli: icra karşılaştırması şimdiye kadar yalnız kütüphanedekiler
    arasında yapılabiliyordu. Öneri "bu albümün davulcusu Duplantier kalibresinde"
    diyebilsin diye adayın da stem'i ölçülmeli — ölçüm yine 30 sn önizlemeden,
    yani sende olmayan albüm için de aynı kaynak (K11).
    """
    from python.discover.onizleme import (
        deezer, deezer_onizleme, itunes, itunes_onizleme, onizleme_bul,
    )

    if adaylar:
        # Adayın önizleme URL'si aday üretiminde zaten bulunmuştu; varsa onu
        # kullan, yoksa albümlerdeki gibi ara. Aynı albüm iki stratejiden
        # gelebildiği için (aday_id, ...) tekilleştiriliyor.
        sorgu = """
            SELECT aday_id AS album_id, artist, title, MAX(onizleme_url) AS hazir_url
              FROM adaylar GROUP BY aday_id, artist, title
        """
        if not yenile:
            sorgu += " HAVING aday_id NOT IN (SELECT DISTINCT album_id FROM stem_profili)"
        sorgu += " ORDER BY artist, title"
    else:
        sorgu = "SELECT album_id, artist, title, NULL AS hazir_url FROM albums"
        if not yenile:
            sorgu += " WHERE album_id NOT IN (SELECT DISTINCT album_id FROM stem_profili)"
        sorgu += " ORDER BY artist, title"
    if limit:
        sorgu += f" LIMIT {int(limit)}"
    albumler = conn.execute(sorgu).fetchall()

    istemciler = ((itunes_onizleme, itunes()), (deezer_onizleme, deezer()))
    sayac = {"album": 0, "onizleme_yok": 0, "stem": 0, "profilli_album": 0}

    for sira, albom in enumerate(albumler, 1):
        sayac["album"] += 1
        hazir = albom["hazir_url"] if "hazir_url" in albom.keys() else None
        if hazir:
            onizleme = type("Onizleme", (), {"url": hazir})()
        else:
            onizleme = onizleme_bul(albom["artist"], albom["title"], istemciler=istemciler)
        if not onizleme:
            sayac["onizleme_yok"] += 1
            print(f"  {sira}/{len(albumler)} {albom['artist'][:22]:<22} önizleme yok",
                  file=sys.stderr)
            continue
        profiller = klipten_stemler(onizleme.url)
        for stem, profil in profiller.items():
            profil_yaz(conn, albom["album_id"], stem, profil, onizleme.url,
                       tur="aday" if adaylar else "album")
            sayac["stem"] += 1
        if profiller:
            sayac["profilli_album"] += 1
        print(
            f"  {sira}/{len(albumler)} {albom['artist'][:22]:<22} "
            f"{len(profiller)} stem: {', '.join(sorted(profiller))}",
            file=sys.stderr,
        )
    return sayac


def muzisyen_profilleri(conn: sqlite3.Connection, rol: str) -> "object":
    """Rol için müzisyen × öznitelik tablosu: albümlerinin ilgili stem medyanı."""
    import pandas as pd

    stem = ROL_STEM.get(rol)
    if not stem:
        return pd.DataFrame()

    veri = pd.read_sql_query(
        """
        SELECT c.person_name, s.*
          FROM credits c
          JOIN stem_profili s ON s.album_id = c.album_id
         WHERE c.role = ? AND s.stem = ?
        """,
        conn, params=(rol, stem),
    )
    if veri.empty:
        return pd.DataFrame()

    from python.enrich.kisi_birlestir import eslesmeleri_oku
    from python.metin import normalize_esleme

    # Alias birleştirmesi burada da uygulanmalı: `muzisyen.py` birleştirip
    # burası birleştirmezse iki taraf farklı anahtar üretir ve profil hiç
    # eşleşmez — kişi arayüzde görünür ama icra profili "yok" çıkar.
    eslesme = eslesmeleri_oku(conn)
    veri["anahtar"] = veri["person_name"].map(
        lambda a: eslesme.get(normalize_esleme(a or ""), normalize_esleme(a or ""))
    )
    veri = veri[veri["anahtar"] != ""]
    sayisal = [s for s in TUM_SUTUNLAR if s in veri.columns]
    ozet = veri.groupby("anahtar")[sayisal].median()
    ozet["kisi_adi"] = veri.groupby("anahtar")["person_name"].first()
    ozet["klip_sayisi"] = veri.groupby("anahtar")["album_id"].nunique()
    ozet["ornek_onizleme"] = veri.groupby("anahtar")["onizleme_url"].first()
    return ozet


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Dört stem icra profili.")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--limit", type=int)
    ayristirici.add_argument("--tum", action="store_true")
    ayristirici.add_argument("--yenile", action="store_true")
    ayristirici.add_argument("--adaylar", action="store_true",
                             help="kütüphane yerine aday albümleri profille")
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        sayac = calistir(
            conn, limit=None if args.tum else (args.limit or 10),
            yenile=args.yenile, adaylar=args.adaylar,
        )
    finally:
        conn.close()

    print(f"İşlenen albüm     : {sayac['album']}")
    print(f"Profil çıkan albüm: {sayac['profilli_album']}")
    print(f"Yazılan stem      : {sayac['stem']}")
    print(f"Önizlemesi yok    : {sayac['onizleme_yok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
