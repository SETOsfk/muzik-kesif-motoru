"""Davul stem'i üzerinden müzisyen profili — "benzer davulcuyu duymak" için.

NEDEN AYRI BİR MODÜL: `ses_ozellikleri.py` tüm mikse bakıyor ve davulcu
karakterini yakalayamıyor. İki deneme ölçülüp ELENDİ:

1. Tempogram entropisi — sekiz sanatçıda 0.878–0.891, hiçbir şey ayırt etmedi.
2. HPSS + senkop fazı — Françoise Hardy (0.682) Meshuggah'tan (0.600) yüksek
   çıktı. HPSS yoğun mikste davulu ayıramıyor; onset dedektörü gitar atağını da
   davul sanıyor.

ÇALIŞAN YOL: Demucs ile davul stem'ini AYIRIP yalnız onu ölçmek. Aynı sekiz
sanatçıda sonuç müzikal olarak doğru çıktı:

  Meshuggah   zil %62 / trampet %17   → Haake'nin ride ağırlıklı, trampet cimri stili
  Eminem      ızgara entropisi 0.755  → programlanmış beat, ızgaraya kilitli
  TOOL        tekme %41               → Carey'nin tom/tekme ağırlıklı sesi
  Casiopea    zil %52, dinamik 32 dB  → jazz ride'ı, nefes alan miks

Ölçütler:
  nota_vurus       davul stem'inde vuruş başına nota — tempodan bağımsız yoğunluk
  izgara_entropi   16'lık ızgara histogramının entropisi; MAKİNE düşük, insan yüksek
  tekme_payi       <120 Hz enerji payı
  trampet_payi     120–2000 Hz
  zil_payi         >6000 Hz
  dinamik_db       davul stem'inin 95./5. yüzdelik farkı

Kaynak: 30 sn önizleme (iTunes/Deezer). Yerel FLAC de kullanılabilir ama
önizleme her albüm için var ve TEK KAYNAK olması karşılaştırmayı geçerli kılar
(K11: kaynaklar arası ham değer kıyaslanamaz).

Maliyet: MPS'te klip başına ~12 sn. 40 davulcu × 2 klip ≈ 16 dakika.

Kullanım:
    python -m python.enrich.davul_profili --rol drums --limit 20
    python -m python.enrich.davul_profili --rol drums --klip-basina 2
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import statistics
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import requests

from python.db import VARSAYILAN_DB, baglan
from python.metin import normalize_esleme

CALISMA_ORNEKLEME = 22050


@dataclass(frozen=True)
class DavulOzellik:
    nota_vurus: float
    izgara_entropi: float
    tekme_payi: float
    trampet_payi: float
    zil_payi: float
    dinamik_db: float
    tempo: float


_AYIRICI = None


def _ayirici():
    """Demucs modelini bir kez yükle — her klipte yeniden yüklemek dakikalar yer."""
    global _AYIRICI
    if _AYIRICI is None:
        try:
            import torch
            from demucs.api import Separator
        except ImportError as hata:  # pragma: no cover
            raise SystemExit(
                "demucs kurulu değil: pip install demucs\n"
                "(torch ile birlikte ~2 GB; davul ayrıştırması bunsuz yapılamıyor)"
            ) from hata
        aygit = "mps" if torch.backends.mps.is_available() else "cpu"
        _AYIRICI = Separator(model="htdemucs", device=aygit, progress=False)
        print(f"  demucs yüklendi (aygıt: {aygit})", file=sys.stderr)
    return _AYIRICI


def davul_stemi(yol: str) -> tuple[np.ndarray, int] | None:
    """Ses dosyasından davul stem'ini ayır."""
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
    _, stemler = ayirici.separate_tensor(
        torch.tensor(y, dtype=torch.float32), sr=ayirici.samplerate
    )
    davul = stemler["drums"].mean(0).cpu().numpy()
    return davul, ayirici.samplerate


def stem_ozellikleri(davul: np.ndarray, sr: int) -> DavulOzellik | None:
    import librosa

    if sr != CALISMA_ORNEKLEME:
        davul = librosa.resample(davul, orig_sr=sr, target_sr=CALISMA_ORNEKLEME)
    sr = CALISMA_ORNEKLEME
    if davul.size < sr:
        return None

    zarf = librosa.onset.onset_strength(y=davul, sr=sr)
    onsetler = librosa.onset.onset_detect(onset_envelope=zarf, sr=sr, units="time")
    _, vuruslar = librosa.beat.beat_track(onset_envelope=zarf, sr=sr, units="time")
    if len(vuruslar) < 4 or len(onsetler) < 4:
        return None

    ara = float(np.median(np.diff(vuruslar)))
    if ara <= 0:
        return None
    sure = davul.size / sr
    nota_vurus = len(onsetler) / (sure / ara)
    tempo = 60.0 / ara

    # Kalite koruması: 30 sn davul stem'inde vuruş başına yarım notadan az
    # düşüyorsa klip güvenilmez — sessiz giriş, akustik pasaj ya da vuruş takibi
    # kaçırmış demektir. Ölçüldü: Ian Paice 0.18 nota/vuruş çıkmıştı, oysa Deep
    # Purple'ın davulcusu seyrek çalmaz. Böyle bir klip medyanı zehirliyor.
    if nota_vurus < 0.5 or len(onsetler) < 15:
        return None

    # Bar içi konum histogramı (4/4 varsayımı). Programlanmış beat ızgaraya
    # yığılır → entropi düşük; insan davulcu yayılır → yüksek.
    faz = ((onsetler - vuruslar[0]) % (ara * 4)) / (ara * 4)
    hist, _ = np.histogram(faz, bins=16, range=(0, 1))
    p = hist / max(1, hist.sum())
    p = p[p > 0]
    izgara_entropi = float(-(p * np.log(p)).sum() / np.log(16)) if p.size > 1 else 0.0

    izge = np.abs(librosa.stft(davul, n_fft=2048))
    frek = librosa.fft_frequencies(sr=sr, n_fft=2048)
    tekme = float(izge[frek < 120].sum())
    trampet = float(izge[(frek >= 120) & (frek < 2000)].sum())
    zil = float(izge[frek >= 6000].sum())
    toplam = max(1e-9, tekme + trampet + zil)

    rms = librosa.feature.rms(y=davul)[0]
    rms = rms[rms > 0]
    dinamik = (
        float(20 * np.log10(np.percentile(rms, 95) / max(1e-9, np.percentile(rms, 5))))
        if rms.size
        else 0.0
    )

    return DavulOzellik(
        nota_vurus=round(nota_vurus, 4),
        izgara_entropi=round(izgara_entropi, 4),
        tekme_payi=round(tekme / toplam, 4),
        trampet_payi=round(trampet / toplam, 4),
        zil_payi=round(zil / toplam, 4),
        dinamik_db=round(dinamik, 2),
        tempo=round(tempo, 2),
    )


def klipten_profil(url: str) -> DavulOzellik | None:
    """Önizleme URL'sini indir, davulu ayır, ölç."""
    try:
        yanit = requests.get(url, timeout=60)
        yanit.raise_for_status()
    except Exception as hata:
        print(f"    indirilemedi: {hata}", file=sys.stderr)
        return None
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as dosya:
        dosya.write(yanit.content)
        gecici = dosya.name
    try:
        stem = davul_stemi(gecici)
        return stem_ozellikleri(*stem) if stem else None
    finally:
        os.unlink(gecici)


# --------------------------------------------------------------------------- #
# Müzisyen düzeyi
# --------------------------------------------------------------------------- #

def ozetle(profiller: list[DavulOzellik]) -> dict[str, float] | None:
    """Birden çok klibin medyanı — tek klip yanıltıcı olabilir."""
    if not profiller:
        return None
    alanlar = asdict(profiller[0]).keys()
    return {
        alan: round(statistics.median(getattr(p, alan) for p in profiller), 4)
        for alan in alanlar
    }


def rol_muzisyenleri(
    conn: sqlite3.Connection, rol: str, asgari_album: int = 2
) -> list[dict]:
    """Rolü asıl işi olan müzisyenler + analiz edilecek albümleri."""
    from python.muzisyen import muzisyen_verisi, rolu_ustlenenler

    veri = muzisyen_verisi(conn, None)
    uygun = rolu_ustlenenler(veri, rol)
    if uygun.empty:
        return []
    sonuc = []
    for anahtar, satir in uygun.iterrows():
        albumler = veri.albumleri[
            (veri.albumleri["kisi"] == anahtar) & (veri.albumleri["role"] == rol)
        ].drop_duplicates("album_id")
        if len(albumler) < asgari_album:
            continue
        sonuc.append(
            {
                "anahtar": anahtar,
                "ad": satir["kisi"],
                "albumler": albumler[["artist", "title"]].to_dict("records"),
                "album_sayisi": int(satir["bu_rolde_album"]),
            }
        )
    return sorted(sonuc, key=lambda k: -k["album_sayisi"])


def rol_tanisi(conn: sqlite3.Connection, kisi_adi: str, rol: str) -> tuple[int, float]:
    """(farklı rol sayısı, bu rolün kredi payı) — kullanıcı yargılayabilsin diye.

    Otomatik eşik denendi ve BIRAKILDI: %25 kredi payı eşiği Bruce Swedien'i
    (11 rollü mühendis, davul kredisi %12) doğru eliyor ama Matt Cameron'ı da
    eliyor (%22 — Soundgarden'da şarkı da yazdığı için). Rol genişliği de
    ayırmıyor: Swedien 11, Bottrell 9, Cameron 8 rol. Temiz bir kural yok;
    sayıyı gösterip kararı kullanıcıya bırakmak dürüst olan.
    """
    satirlar = conn.execute(
        "SELECT DISTINCT role, album_id FROM credits WHERE person_name = ?", (kisi_adi,)
    ).fetchall()
    if not satirlar:
        return 0, 0.0
    roller = {s["role"] for s in satirlar}
    bu_rol = sum(1 for s in satirlar if s["role"] == rol)
    return len(roller), round(bu_rol / len(satirlar), 3)


def profil_yaz(conn: sqlite3.Connection, anahtar: str, ad: str, rol: str,
               ozet: dict[str, float], klip: int, url: str | None) -> None:
    rol_sayisi, kredi_payi = rol_tanisi(conn, ad, rol)
    with conn:
        conn.execute(
            """INSERT OR REPLACE INTO davul_profili
               (kisi_anahtar, kisi_adi, rol, nota_vurus, izgara_entropi,
                tekme_payi, trampet_payi, zil_payi, dinamik_db, tempo,
                klip_sayisi, rol_sayisi, rol_kredi_payi, ornek_onizleme)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (anahtar, ad, rol, ozet["nota_vurus"], ozet["izgara_entropi"],
             ozet["tekme_payi"], ozet["trampet_payi"], ozet["zil_payi"],
             ozet["dinamik_db"], ozet["tempo"], klip, rol_sayisi, kredi_payi, url),
        )


def calistir(
    conn: sqlite3.Connection,
    rol: str = "drums",
    *,
    limit: int | None = None,
    klip_basina: int = 2,
    yenile: bool = False,
) -> dict[str, int]:
    from python.discover.onizleme import deezer, deezer_onizleme, itunes, itunes_onizleme

    istemciler = ((itunes_onizleme, itunes()), (deezer_onizleme, deezer()))
    from python.discover.onizleme import onizleme_bul

    mevcut = {
        s["kisi_anahtar"]
        for s in conn.execute("SELECT kisi_anahtar FROM davul_profili WHERE rol = ?", (rol,))
    }
    muzisyenler = rol_muzisyenleri(conn, rol)
    if not yenile:
        muzisyenler = [m for m in muzisyenler if m["anahtar"] not in mevcut]
    if limit:
        muzisyenler = muzisyenler[:limit]

    sayac = {"muzisyen": 0, "yazilan": 0, "klip": 0, "onizleme_yok": 0}
    for sira, kisi in enumerate(muzisyenler, 1):
        sayac["muzisyen"] += 1
        profiller: list[DavulOzellik] = []
        ornek_url = None
        for albom in kisi["albumler"][:klip_basina]:
            onizleme = onizleme_bul(albom["artist"], albom["title"], istemciler=istemciler)
            if not onizleme:
                sayac["onizleme_yok"] += 1
                continue
            ornek_url = ornek_url or onizleme.url
            profil = klipten_profil(onizleme.url)
            if profil:
                profiller.append(profil)
                sayac["klip"] += 1

        ozet = ozetle(profiller)
        if ozet:
            profil_yaz(conn, kisi["anahtar"], kisi["ad"], rol, ozet, len(profiller), ornek_url)
            sayac["yazilan"] += 1
        print(
            f"  {sira}/{len(muzisyenler)} {kisi['ad'][:24]:<24} "
            f"{len(profiller)} klip"
            + (f"  zil %{ozet['zil_payi']*100:.0f} nota/vuruş {ozet['nota_vurus']:.2f}"
               if ozet else "  (profil yok)"),
            file=sys.stderr,
        )
    return sayac


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="Davul stem profili (demucs).")
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--rol", default="drums")
    ayristirici.add_argument("--limit", type=int)
    ayristirici.add_argument("--klip-basina", type=int, default=2)
    ayristirici.add_argument("--yenile", action="store_true")
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        sayac = calistir(
            conn, args.rol, limit=args.limit,
            klip_basina=args.klip_basina, yenile=args.yenile,
        )
    finally:
        conn.close()

    print(f"Müzisyen      : {sayac['muzisyen']}")
    print(f"Profili yazılan: {sayac['yazilan']}")
    print(f"Analiz edilen klip: {sayac['klip']} (önizlemesi bulunamayan albüm: {sayac['onizleme_yok']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
