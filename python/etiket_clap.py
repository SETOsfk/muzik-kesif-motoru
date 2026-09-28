"""Sıfır-atışlı ses etiketleme — CLAP.

## Neden bu, elle kesilmiş yüzdelikler yerine

`etiket.py` ölçüm eksenlerini yüzdeliklerden kesip etiket üretiyor. İşe yarıyor
ama sınırı belli: yalnız ölçebildiğimiz sekiz eksen, yalnız kuyruklar, ve
"distorsiyonlu" gibi etiketler dolaylı vekiller.

CLAP (Contrastive Language-Audio Pretraining) sesi ve METNİ aynı uzaya
gömüyor. Sonuç: etiketi doğal dille yazıyorsun, eğitim verisi gerekmiyor,
sözlük istediğin kadar geniş olabiliyor. Netflix insan etiketçi tutmuştu; bu
onun otomatiği ve sınırsız sözlüklüsü.

## Hangi model — ölçüldü

`laion/larger_clap_music` BOZUK çıktı (transformers 5.15): ses kulesi girdiden
bağımsız neredeyse sabit gömü üretiyor, dört etiket de 0.25 alıyor. Beyaz
gürültüyle saf sinüs arasında kosinüs 0.98.

`laion/clap-htsat-unfused` doğru çalışıyor. Aynı kliplerle ölçüldü:
Meshuggah → heavy metal 0.99, Eminem → hip hop 0.75.

## Gömü ÖNBELLEĞE alınır — mimarinin kilit kararı

Pahalı olan ses gömüsünü çıkarmak (klip başına ~1 sn). Metin tarafı ve
karşılaştırma milisaniye. Gömüler saklanınca SÖZLÜĞÜ DEĞİŞTİRMEK BEDAVA:
yeni etiket denemek tüm kütüphaneyi yeniden işlemek değil, bir matris çarpımı.

Aynı ders stem önbelleğinde alınmıştı — öznitelik tasarımı bir kerede
oturmuyor, o yüzden pahalı adımın çıktısı saklanır.

## Skorlar ham kosinüs DEĞİL

CLAP'te ses–metin kosinüsü küçük ve taban yüksek; ham değer okunamıyor. Etiket
kümesi üzerinde softmax alınıyor, yani "bu klip bu sözlükteki etiketler
arasında en çok neye benziyor". Sözlük değişirse skorlar da değişir — bu bir
kusur değil, ölçünün tanımı.

Kullanım:
    python -m python.etiket_clap --gomu        # gömüleri çıkar (bir kez)
    python -m python.etiket_clap --etiketle    # sözlüğü uygula (istediğin kadar)
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path

import numpy as np

from python.db import VARSAYILAN_DB, baglan
from python.metin import normalize_esleme

MODEL = "laion/clap-htsat-unfused"
CLAP_ORNEKLEME = 48000
GOMU_KLASOR = Path("data/cache/clap")

#: Sözlük: eksen -> {gösterilecek Türkçe etiket: CLAP'e verilecek İngilizce istem}
#:
#: İstemler CÜMLE, tek kelime değil: CLAP metin kulesi RoBERTa ve doğal dilde
#: eğitilmiş; "metal" yerine "aggressive heavy metal with distorted guitars"
#: belirgin biçimde daha iyi ayırıyor.
SOZLUK: dict[str, dict[str, str]] = {
    "tur": {
        "metal": "aggressive heavy metal with distorted electric guitars",
        "prog metal": "progressive metal with complex odd time signatures",
        "death metal": "extreme death metal with growled vocals and blast beats",
        "doom": "slow heavy doom metal with downtuned guitars",
        "hard rock": "hard rock with electric guitar riffs and drums",
        "klasik rock": "classic rock from the 1970s with guitar solos",
        "grunge": "grunge rock with fuzzy guitars and raw vocals",
        "punk": "fast punk rock with shouted vocals",
        "prog rock": "progressive rock with keyboards and long instrumental passages",
        "psychedelic": "psychedelic rock with swirling effects",
        "jazz": "acoustic jazz with upright bass and brushed drums",
        "jazz füzyon": "jazz fusion with electric guitar, synthesizer and virtuoso solos",
        "funk": "funky groove with slap bass and rhythm guitar",
        "soul": "soul music with warm vocals and horns",
        "blues": "blues with expressive guitar bends",
        "hip hop": "hip hop beat with rapping over programmed drums",
        "elektronik": "electronic dance music with synthesizers and a drum machine",
        "ambient": "ambient electronic music with slow evolving textures",
        "pop": "catchy mainstream pop song with polished production",
        "synth pop": "1980s synth pop with drum machine and analog synthesizers",
        "folk": "acoustic folk with fingerpicked guitar and gentle singing",
        "klasik": "orchestral classical music with strings",
        "türk rock": "Turkish rock music with vocals in Turkish",
        "anadolu": "Anatolian rock blending Turkish folk melodies with electric guitar",
        "city pop": "Japanese city pop with lush chords and smooth production",
    },
    "ruh": {
        "agresif": "aggressive and angry music",
        "sakin": "calm peaceful relaxing music",
        "melankolik": "sad melancholic music",
        "epik": "epic cinematic and grand music",
        "neşeli": "happy upbeat joyful music",
        "karanlık": "dark ominous music",
        "hüzünlü güzel": "bittersweet beautiful melancholy",
        "hipnotik": "hypnotic repetitive trance-like music",
        "gergin": "tense anxious music",
        "romantik": "romantic tender love song",
    },
    "enstruman": {
        "gitar odaklı": "music dominated by electric guitar",
        "klavye odaklı": "music dominated by keyboards and synthesizers",
        "piyano": "solo piano performance",
        "yaylı": "music with prominent string section",
        "üflemeli": "music with saxophone or trumpet",
        "enstrümantal": "instrumental music with no singing",
        "kadın vokal": "song with a female lead singer",
        "erkek vokal": "song with a male lead singer",
        "korolu": "music with layered choir vocals",
        "akustik": "acoustic unplugged recording",
    },
}

#: Bir etiketin yapışması için gereken en düşük softmax payı. Sözlükteki etiket
#: sayısına göre ayarlanır: rastgele dağılımda her etiket 1/n alır, eşik bunun
#: birkaç katı olmalı ki "belirgin" sayılsın.
ESIK_CARPANI = 3.0

_MODEL = None
_ISLEMCI = None


def _yukle():
    global _MODEL, _ISLEMCI
    if _MODEL is None:
        import torch
        from transformers import ClapModel, ClapProcessor

        print(f"  {MODEL} yükleniyor…", file=sys.stderr)
        _MODEL = ClapModel.from_pretrained(MODEL).eval()
        _ISLEMCI = ClapProcessor.from_pretrained(MODEL)
        torch.set_grad_enabled(False)
    return _MODEL, _ISLEMCI


def klip_gomusu(y: np.ndarray) -> np.ndarray:
    """48 kHz tek kanal sesten birim uzunluklu 512 boyutlu CLAP gömüsü.

    `get_audio_features(...).pooler_output` ZATEN yansıtılmış 512 boyutlu
    gömü — üstüne `audio_projection` uygulamak (768→512) boyut hatası veriyor.
    """
    model, islemci = _yukle()
    girdi = islemci(audio=y, sampling_rate=CLAP_ORNEKLEME, return_tensors="pt")
    e = model.get_audio_features(**girdi).pooler_output
    e = (e / e.norm(dim=-1, keepdim=True)).squeeze(0)
    return e.cpu().numpy().astype("float32")


def onizleme_gomusu(url: str) -> np.ndarray | None:
    """Bir önizleme URL'sini indirip göm. Klip bir saniyeden kısaysa None.

    URL TAZE olmalı: Deezer imzaları kısa ömürlü (bkz. `PARCA_GOMU` notu).
    Geçici dosya şart — librosa mp3'ü bellekten değil yoldan okuyor.
    """
    import tempfile

    import librosa
    import requests

    # Tek yeniden deneme: ölçüldü, Deezer CDN'i arada bir aktarımı yarıda
    # kesiyor (IncompleteRead). İkinci deneme de düşerse hata yukarı çıkar.
    for deneme in (1, 2):
        try:
            yanit = requests.get(url, timeout=30)
            yanit.raise_for_status()
            break
        except requests.RequestException:
            if deneme == 2:
                raise
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as gecici:
        gecici.write(yanit.content)
        gecici.flush()
        y, _ = librosa.load(gecici.name, sr=CLAP_ORNEKLEME, mono=True)
    if y.size < CLAP_ORNEKLEME:
        return None
    return klip_gomusu(y)


def klip_miksi(onizleme_url: str) -> np.ndarray | None:
    """Önbellekteki dört stem'i toplayıp 48 kHz'e çıkar.

    Stem'ler zaten diskte (Demucs geçişinden). Ayrı ayrı değil TOPLAMLARI
    kullanılıyor: CLAP tam mikste eğitilmiş, tek kanal ona yabancı gelir.

    48 kHz şart — 22.05 kHz sesi 48 diye vermek modele yanlış perde ve tempo
    gösteriyor; ölçüldü, o durumda her klip "hip hop" çıkıyordu.
    """
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
    tepe = float(np.abs(miks).max()) or 1.0
    return librosa.resample(miks / tepe, orig_sr=22050, target_sr=CLAP_ORNEKLEME)


def gomu_cikar(conn: sqlite3.Connection, *, limit: int | None = None) -> int:
    """Ses gömülerini hesapla ve diske al.

    Pahalı adım bu; sözlük değiştikçe TEKRARLANMAMASI için saklanıyor.
    """
    import torch

    GOMU_KLASOR.mkdir(parents=True, exist_ok=True)
    model, islemci = _yukle()

    hedefler = conn.execute(
        """SELECT DISTINCT album_id, tur, onizleme_url FROM stem_profili
            WHERE onizleme_url IS NOT NULL"""
    ).fetchall()
    if limit:
        hedefler = hedefler[:limit]

    sayac = 0
    for sira, (album_id, tur, url) in enumerate(hedefler, 1):
        dosya = GOMU_KLASOR / f"{album_id}.npy"
        if dosya.exists():
            continue
        ses = klip_miksi(url)
        if ses is None:
            continue
        girdi = islemci(audio=ses, sampling_rate=CLAP_ORNEKLEME,
                        return_tensors="pt")
        # `get_audio_features(...).pooler_output` ZATEN yansıtılmış 512
        # boyutlu gömü — üstüne `audio_projection` uygulamak (768→512)
        # boyut hatası veriyor.
        cikti = model.get_audio_features(**girdi)
        gomu = cikti.pooler_output
        gomu = (gomu / gomu.norm(dim=-1, keepdim=True)).squeeze(0)
        np.save(dosya, gomu.cpu().numpy().astype("float32"))
        sayac += 1
        if sira % 25 == 0:
            print(f"  {sira}/{len(hedefler)} · {sayac} yeni", file=sys.stderr)
    return sayac


def metin_gomuleri() -> tuple[list[tuple[str, str]], np.ndarray]:
    """Sözlüğün metin gömüleri. (eksen, etiket) listesi + matris."""
    import torch

    model, islemci = _yukle()
    anahtarlar, istemler = [], []
    for eksen, sozluk in SOZLUK.items():
        for etiket, istem in sozluk.items():
            anahtarlar.append((eksen, etiket))
            istemler.append(istem)
    girdi = islemci(text=istemler, return_tensors="pt", padding=True)
    cikti = model.get_text_features(**girdi)
    gomu = cikti.pooler_output
    gomu = gomu / gomu.norm(dim=-1, keepdim=True)
    return anahtarlar, gomu.cpu().numpy().astype("float32")


def etiketle(conn: sqlite3.Connection) -> list[tuple[str, str, str, float]]:
    """Kayıtlı gömüleri sözlükle eşleştir. (album_id, eksen, etiket, skor)."""
    anahtarlar, T = metin_gomuleri()
    eksen_indeks: dict[str, list[int]] = {}
    for i, (eksen, _) in enumerate(anahtarlar):
        eksen_indeks.setdefault(eksen, []).append(i)

    sonuc = []
    for dosya in sorted(GOMU_KLASOR.glob("*.npy")):
        a = np.load(dosya)
        skor = T @ a
        # Softmax EKSEN İÇİNDE: "tür" etiketleri kendi aralarında, "ruh"
        # kendi arasında yarışsın. Hepsini tek havuzda yarıştırmak, sözlüğü
        # kalabalık olan ekseni bastırırdı.
        for eksen, indeksler in eksen_indeks.items():
            alt = skor[indeksler]
            us = np.exp((alt - alt.max()) * 100.0)   # CLAP logit ölçeği
            p = us / us.sum()
            esik = ESIK_CARPANI / len(indeksler)
            for j, pay in zip(indeksler, p):
                if pay >= esik:
                    sonuc.append((dosya.stem, eksen, anahtarlar[j][1], float(pay)))
    return sonuc


def yaz(conn: sqlite3.Connection, satirlar) -> int:
    with conn:
        conn.execute("DELETE FROM album_etiket WHERE kaynak = 'clap'")
        conn.executemany(
            "INSERT OR REPLACE INTO album_etiket "
            "(album_id, eksen, etiket, kaynak, skor) VALUES (?,?,?,'clap',?)",
            [(a, f"clap_{e}", t, round(s, 4)) for a, e, t, s in satirlar],
        )
    return len(satirlar)


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--db", type=Path, default=VARSAYILAN_DB)
    ayristirici.add_argument("--gomu", action="store_true")
    ayristirici.add_argument("--etiketle", action="store_true")
    ayristirici.add_argument("--limit", type=int)
    ayristirici.add_argument("--parca-gomu", action="store_true")
    #: Kaç listede geçen sanatçı gömülsün. 3 = PMI'ya giren çekirdek
    #: (1.384 sanatçı). Düşürmek uzun kuyruğu açar: ses benzerliği PMI'a
    #: ihtiyaç duymaz, tek listede geçen sanatçıyı da bulabilir — ve
    #: "hiç duymadığım sanatçı" hedefi tam orada yaşıyor.
    ayristirici.add_argument("--asgari-liste", type=int, default=3)
    args = ayristirici.parse_args(argv)

    conn = baglan(args.db)
    try:
        if args.parca_gomu:
            s = parca_gomule(conn, limit=args.limit,
                             asgari_liste=args.asgari_liste)
            print(f"denenen {s['denenen']} · gömülen {s['gomulen']} · "
                  f"atlanan {s['atlanan']}")
            return 0
        if args.gomu:
            print(f"{gomu_cikar(conn, limit=args.limit)} yeni gömü")
        if args.etiketle or not args.gomu:
            satirlar = etiketle(conn)
            print(f"{yaz(conn, satirlar)} CLAP etiketi, "
                  f"{len({a for a, *_ in satirlar})} albüm")
    finally:
        conn.close()
    return 0



# --------------------------------------------------------------------------- #
# CLAP benzerliği — SINIFLANDIRICI DEĞİL, komşuluk
# --------------------------------------------------------------------------- #
#
# Sıfır-atışlı etiketleme (metne eşleme) ölçüldü ve yetmedi: istem yanlılığı
# yüzünden "türk rock" Eminem'e de A-Ha'ya da yapışıyor, altı albümde üç doğru.
#
# Aynı gömüler ALAN İÇİ BENZERLİKTE çok iyi çalışıyor ve sebebi açık: iki klip
# karşılaştırılırken ne istem yanlılığı devreye giriyor ne alan kayması.
# Ölçüldü — Meshuggah → Gojira/The Ocean, Casiopea → Scott Henderson/Animals As
# Leaders, Opeth → Dream Theater, Slipknot → Mushroomhead, Eminem → Kendrick
# Lamar.
#
# Bu, projenin baştan beri eksik olan parçası: İÇERİK TEMELLİ öneri. Kredi
# grafiği "kim çalmış", kalabalık "kim dinliyor" diyordu; bu "kulağa nasıl
# geliyor" diyor.

def gomuleri_oku(kimlikler: list[str] | None = None) -> tuple[list[str], np.ndarray]:
    dosyalar = sorted(GOMU_KLASOR.glob("*.npy"))
    if kimlikler is not None:
        istenen = set(kimlikler)
        dosyalar = [d for d in dosyalar if d.stem in istenen]
    if not dosyalar:
        return [], np.zeros((0, 512), dtype="float32")
    return [d.stem for d in dosyalar], np.stack([np.load(d) for d in dosyalar])


def benzer_adaylar(
    conn: sqlite3.Connection, calisma_id: str, eksen: int, *, adet: int = 12
) -> list[dict]:
    """Eksenin albümlerine CLAP uzayında en yakın ADAYLAR.

    Eksenin merkezi değil, ÜYELERİNE tek tek yakınlık kullanılıyor: merkez
    almak heterojen bir ekseni ortalayıp hiçbir albüme benzemeyen bir nokta
    üretiyor. "Şu albümün gibi" demek, "şu kümenin ortalaması gibi" demekten
    hem daha doğru hem daha açıklanabilir — gerekçede hangi albüme benzediğini
    yazabiliyoruz.
    """
    uyelik = conn.execute(
        """SELECT album_id FROM memberships WHERE calisma_id = ?
            AND kume_id = ? AND uyelik >= 0.25""",
        (calisma_id, eksen),
    ).fetchall()
    uyeler = [r[0] for r in uyelik]
    if not uyeler:
        return []

    aday_kimlik = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT album_id FROM stem_profili WHERE tur = 'aday'")
    }
    sahip_ad = {
        r[0]: f"{r[1]} — {r[2]}" for r in conn.execute(
            "SELECT album_id, artist, title FROM albums")
    }

    k_uye, A_uye = gomuleri_oku(uyeler)
    k_aday, A_aday = gomuleri_oku(sorted(aday_kimlik))
    if not k_uye or not k_aday:
        return []

    # HUBNESS DÜZELTMESİ. Ham kosinüste bir albüm HER ŞEYE en yakın çıkıyordu
    # («Foo Fighters — Today's Song», beş adayın dördünde). Gömü uzaylarında
    # bilinen "hub" olgusu: bazı noktalar merkeze yakın durup evrensel komşu
    # oluyor. Skorlar da 0.92–0.98'e sıkışmış, ham fark okunmuyor.
    #
    # Çözüm bu projede beşinci kez aynı: adayın TÜM kütüphaneye ortalama
    # benzerliği çıkarılıyor. Kalan şey "bu eksene, genel olarak benzediğinden
    # NE KADAR fazla benziyor" — kesişim, lift, eksen-özgüllüğü ve PMI ile
    # aynı aile.
    k_tum, A_tum = gomuleri_oku(sorted(sahip_ad))
    if len(k_tum) >= 10:
        taban_aday = (A_aday @ A_tum.T).mean(axis=1, keepdims=True)
        taban_uye = (A_uye @ A_tum.T).mean(axis=1, keepdims=True)
    else:
        taban_aday = taban_uye = 0.0

    S = (A_aday - 0) @ A_uye.T - taban_aday - taban_uye.T
    en_yakin = S.argmax(axis=1)
    skor = S.max(axis=1)

    sonuc = []
    for i in np.argsort(-skor)[: adet * 3]:
        sonuc.append({
            "aday_id": k_aday[i],
            "benzedigi": sahip_ad.get(k_uye[en_yakin[i]], k_uye[en_yakin[i]]),
            "skor": float(skor[i]),
        })
    return sonuc[: adet * 3]


# --------------------------------------------------------------------------- #
# Havuzu büyütme: çalma listesi parçalarını gömme
# --------------------------------------------------------------------------- #
#
# CLAP benzerliği en iyi çalışan yöntem ama havuzu küçüktü — 469 klip, bunun
# ~180'i aday. Oysa çalma listesi hasadından 45.899 parça kimliği var.
#
# Saklanan önizleme URL'leri KULLANILAMIYOR: Deezer onları kısa ömürlü
# imzalıyor, ölçüldü — hasattan saatler sonra 10 URL'nin 10'u da 403 döndü.
# Kalıcı olan parça kimliği; taze URL `track/{id}` ile alınıyor.

PARCA_GOMU = Path("data/cache/clap_parca")


def parca_gomule(
    conn: sqlite3.Connection, *, asgari_liste: int = 3, kisi_basi: int = 2,
    limit: int | None = None,
) -> dict[str, int]:
    """Çalma listesi parçalarını göm — sanatçı başına birkaç parça.

    `asgari_liste`: birden az listede geçen sanatçı zaten PMI'ya girmiyor;
    gömmek boşa maliyet. Üç listede geçen 1.384 sanatçı var.

    Sanatçı başına birkaç parça: tek parça o sanatçının atipik bir anına denk
    gelebilir. Sorgu sırasında sanatçının gömüleri ortalanmaz, en yakın olan
    kullanılır — "bu sanatçının şu parçası senin şuna benziyor" daha kesin.
    """
    PARCA_GOMU.mkdir(parents=True, exist_ok=True)
    from python.discover.calma_listesi import deezer_listesi
    istemci = deezer_listesi()

    hedefler = conn.execute(
        """SELECT p.parca_id, p.sanatci, p.parca FROM liste_parca p
            WHERE p.parca_id IS NOT NULL AND p.sanatci_anahtar IN (
              SELECT sanatci_anahtar FROM liste_parca
               GROUP BY sanatci_anahtar HAVING COUNT(DISTINCT liste_id) >= ?)
            GROUP BY p.sanatci_anahtar, p.parca_id
            ORDER BY p.sanatci_anahtar""",
        (asgari_liste,),
    ).fetchall()

    # Sanatçı başına en fazla `kisi_basi` parça.
    secilen, sayac_sanatci = [], {}
    for parca_id, sanatci, parca in hedefler:
        n = sayac_sanatci.get(sanatci, 0)
        if n < kisi_basi:
            secilen.append((parca_id, sanatci, parca))
            sayac_sanatci[sanatci] = n + 1
    if limit:
        secilen = secilen[:limit]

    sayac = {"denenen": 0, "gomulen": 0, "atlanan": 0}
    for sira, (parca_id, sanatci, parca) in enumerate(secilen, 1):
        dosya = PARCA_GOMU / f"{parca_id}.npy"
        if dosya.exists():
            continue
        sayac["denenen"] += 1
        try:
            # yenile=True: önbellekteki yanıtın URL imzası çoktan dolmuş olur
            # (aynı hata `web/sunucu.py:taze_onizleme`'de 2026-09-02'de düzeldi).
            bilgi = istemci.get_json(f"track/{parca_id}", {}, yenile=True)
            url = (bilgi or {}).get("preview")
            if not url:
                sayac["atlanan"] += 1
                continue
            gomu = onizleme_gomusu(url)
            if gomu is None:
                sayac["atlanan"] += 1
                continue
            np.save(dosya, gomu)
            sayac["gomulen"] += 1
        except Exception:
            sayac["atlanan"] += 1
        if sira % 50 == 0:
            print(f"  {sira}/{len(secilen)} · {sayac['gomulen']} gömüldü",
                  file=sys.stderr)
    return sayac

if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------- #
# Çok sesli kural: tek parça, tek albüm değil (kullanıcı isteği, 2026-09-28)
# --------------------------------------------------------------------------- #
#
# «Birkaç farklı ses üzerinden öner, tek şarkı değil.» Eski kural parçayı,
# kütüphanedeki EN YAKIN TEK albüm eksendeyse sayıyordu ve sanatçıyı en iyi
# TEK parçasıyla sıralıyordu. Bir sakin klip Haken'in akustik bir anına denk
# gelince Gabi Hartmann progresif metal ekseninde öneriliyordu. İki taraflı
# çoğunluk:
#   - kütüphane tarafı: parçanın en yakın KOMSU_K albümünden en az
#     KOMSU_COGUNLUK'u eksende; parça skoru eksendeki en yakınlarının ortalaması;
#   - aday tarafı: sanatçının en az ASGARI_PARCA parçası geçmeli; havuzda tek
#     parçası olan sanatçı ancak KOMSU_K'nın hepsi eksendeyse. Sanatçı skoru en
#     iyi (en çok 3) geçen parçasının ortalaması.

#: "cok_sesli" (varsayılan, 2026-09-28) | "en_yakin_eksen" (eski).
SES_KURALI = "cok_sesli"
KOMSU_K = 3
KOMSU_COGUNLUK = 2
ASGARI_PARCA = 2


def komsu_cogunlugu(tum: np.ndarray, eksende: np.ndarray, k: int = KOMSU_K
                    ) -> tuple[np.ndarray, np.ndarray]:
    """(eksendeki komşu sayısı, eksendeki en yakın k albüme ortalama skor).

    `tum`: (parça × kütüphane albümü) hubness düzeltilmiş benzerlik;
    `eksende`: kütüphane albümü eksende mi (bool). Satır başına.
    """
    k = max(1, min(k, tum.shape[1]))
    en_yakin = np.argpartition(-tum, k - 1, axis=1)[:, :k]
    sayi = eksende[en_yakin].sum(axis=1)
    eksen_s = np.where(eksende[None, :], tum, -np.inf)
    ke = max(1, min(k, int(eksende.sum())))
    ust = -np.sort(-eksen_s, axis=1)[:, :ke]
    ust = np.where(np.isfinite(ust), ust, np.nan)
    with np.errstate(invalid="ignore"):
        ort = np.nanmean(ust, axis=1) if ust.size else np.full(tum.shape[0], np.nan)
    return sayi, ort


def sanatci_sirala(skor: np.ndarray, sayi: np.ndarray, sahipler: list[str],
                   k: int = KOMSU_K) -> dict[str, float]:
    """Parça skorlarından sanatçı skoru, çok sesli kurala göre."""
    parcalar: dict[str, list[tuple[float, int]]] = {}
    for d, n, a in zip(skor, sayi, sahipler):
        parcalar.setdefault(a, []).append((float(d), int(n)))
    sonuc = {}
    for a, liste in parcalar.items():
        gecen = sorted((d for d, n in liste if n >= KOMSU_COGUNLUK and d == d), reverse=True)
        if len(liste) == 1:
            if liste[0][1] >= k and gecen:
                sonuc[a] = gecen[0]
        elif len(gecen) >= ASGARI_PARCA:
            sonuc[a] = float(np.mean(gecen[:3]))
    return sonuc


def acik_havuz_adaylari(
    conn: sqlite3.Connection, calisma_id: str, eksen: int, *, adet: int = 12,
) -> list[dict]:
    """Eksenin albümlerine en yakın, SENDE OLMAYAN kayıtlar — AÇIK havuzdan.

    `benzer_adaylar`'ın yerini alıyor. Aradaki fark havuzun büyüklüğü ve bu
    fark ölçüldü (`python/degerlendirme.py`, 2026-09-01):

    - `benzer_adaylar` `stem_profili` tablosundaki aday albümleri sıralıyordu:
      125 kayıt. Kapalı havuz. Gizlenen sanatçı orada olmadığı için
      leave-one-artist-out sınamasında yapısal olarak bulunamıyordu.
    - Bu işlev çalma listesi parçalarının tamamında arıyor: 3.000+ gömü ve
      arka planda büyüyor. Ses kümeleri sayfasında Jiro Inagaki'yi bulan yol
      buydu; öneri sayfası aynı havuzu görmüyordu.

    Sonuç ÇOĞUNLUKLA PARÇA, albüm değil. Bu kasıtlı: parçanın 30 sn önizlemesi
    hemen çalınabiliyor, kullanıcı gerekçeyi kulağıyla sınayabiliyor. Albüm
    adayında önizlemeyi ayrıca aramak gerekiyor ve çoğu zaman bulunamıyor.

    Dönen kayıtlarda `parca_id` var, `onizleme` yok: Deezer'ın imzalı URL'leri
    kısa ömürlü, saklanmış hâli işe yaramıyor.
    """
    from python.ses_kume import havuz_gomuleri

    # Üyeler KESKİN atamayla (her albüm en yüksek üyelikli eksenine).
    # Önceden `uyelik >= 0.25` idi: bulanık albüm iki eksenin de üyesi oluyor,
    # ona yakın kayıtlar iki eksende birden çıkıyordu — ölçüldü (2026-09-21),
    # önerilerin %34'ü (seto) ve %28'i (52 albüm) birden çok eksende. Ayrıca
    # değerlendirme (`degerlendirme.eksen_haritasi`) ve liste stratejisi
    # (`adaylar.eksen_sanatcilari`) zaten keskin atama kullanıyordu; ölçülen
    # şey üretimin yaptığı şey değildi (K19).
    uyeler = [
        r[0] for r in conn.execute(
            """SELECT album_id FROM memberships m WHERE calisma_id = ?
                AND kume_id = ? AND uyelik = (
                  SELECT MAX(uyelik) FROM memberships
                   WHERE calisma_id = m.calisma_id AND album_id = m.album_id)""",
            (calisma_id, eksen),
        )
    ]
    if not uyeler:
        return []

    sahip_ad = {
        r[0]: f"{r[1]} — {r[2]}" for r in conn.execute(
            "SELECT album_id, artist, title FROM albums")
    }
    k_uye, A_uye = gomuleri_oku(uyeler)
    kayitlar, A_havuz = havuz_gomuleri(conn)
    if not k_uye or not kayitlar:
        return []

    # HUBNESS DÜZELTMESİ — `benzer_adaylar` ile aynı gerekçe: düzeltmesiz
    # kosinüste bazı kayıtlar HER ŞEYE en yakın çıkıyor. Taban TÜM kütüphaneye
    # göre alınıyor, eksene göre değil: hubness genel bir özellik.
    k_tum, A_tum = gomuleri_oku(sorted(sahip_ad))
    if len(k_tum) >= 10:
        taban_havuz = (A_havuz @ A_tum.T).mean(axis=1, keepdims=True)
        taban_uye = (A_uye @ A_tum.T).mean(axis=1, keepdims=True)
    else:
        taban_havuz = taban_uye = 0.0

    S = A_havuz @ A_uye.T - taban_havuz - taban_uye.T
    en_yakin = S.argmax(axis=1)
    skor = S.max(axis=1)

    # EN YAKIN ALBÜM KURALI: kayıt yalnız kütüphanedeki en yakın albümü bu
    # eksendeyse önerilir. Keskin üyelik tek başına yetmedi — seto'da ses
    # önerilerinin %32'si hâlâ birden çok eksende çıkıyordu: birçok eksene
    # birden yakın duran kayıtlar (hubness). Kural kartın gerekçesiyle de
    # örtüşüyor: "senin X albümüne benziyor" diyorsak X bu eksende olmalı.
    # Leave-one-artist-out (2026-09-21, seto / 52 albüm): recall@50 ve MRR
    # korunuyor (ses 0,03→0,04 / 0,04→0,04; melez MRR 0,012→0,017, @50
    # 0,10→0,09); yinelenme tanım gereği sıfır.
    if len(k_tum) >= 10:
        taban_tum = (A_tum @ A_tum.T).mean(axis=1, keepdims=True)
        S_tum = A_havuz @ A_tum.T - taban_havuz - taban_tum.T
        uye_kume = set(k_uye)
        eksende = np.array([k in uye_kume for k in k_tum])
        skor = np.where(eksende[S_tum.argmax(axis=1)], skor, -np.inf)

    if SES_KURALI == "cok_sesli" and len(k_tum) >= 10:
        return _cok_sesli_sonuc(kayitlar, S_tum, eksende, k_tum, sahip_ad, adet)

    # Aynı sanatçının birden çok parçası havuzda; sanatçı başına en iyisi.
    # Tekilleştirilmezse tek bir sanatçı listeyi kaplıyor.
    en_iyi: dict[str, dict] = {}
    for i in np.argsort(-skor):
        if skor[i] == -np.inf:
            break
        kayit = kayitlar[i]
        anahtar = normalize_esleme(kayit["sanatci"])
        if anahtar in en_iyi:
            continue
        en_iyi[anahtar] = {
            "kimlik": kayit["kimlik"],
            "tur": kayit["tur"],
            "sanatci": kayit["sanatci"],
            "ad": kayit["ad"],
            "parca_id": int(kayit["kimlik"]) if kayit["tur"] == "parca" else None,
            "benzedigi": sahip_ad.get(k_uye[en_yakin[i]], k_uye[en_yakin[i]]),
            "skor": float(skor[i]),
        }
        if len(en_iyi) >= adet:
            break
    return list(en_iyi.values())


def _cok_sesli_sonuc(kayitlar, S_tum, eksende, k_tum, sahip_ad, adet) -> list[dict]:
    """Çok sesli kuralla sanatçı sırası; kart için sanatçının EN İYİ parçası
    çalınır ve gerekçe eksendeki en yakın albümleri (en çok 3) sayar."""
    sayi, ort = komsu_cogunlugu(S_tum, eksende)
    sahipler = [normalize_esleme(k["sanatci"]) for k in kayitlar]
    sanatci_skor = sanatci_sirala(ort, sayi, sahipler)
    eksen_idx = np.flatnonzero(eksende)
    sonuc = []
    for anahtar, skor in sorted(sanatci_skor.items(), key=lambda x: -x[1])[:adet]:
        satirlar = [i for i, a in enumerate(sahipler) if a == anahtar and sayi[i] >= KOMSU_COGUNLUK]
        i = max(satirlar, key=lambda j: ort[j])
        yakinlar = eksen_idx[np.argsort(-S_tum[i, eksen_idx])[:3]]
        kayit = kayitlar[i]
        sonuc.append({
            "kimlik": kayit["kimlik"], "tur": kayit["tur"], "sanatci": kayit["sanatci"],
            "ad": kayit["ad"],
            "parca_id": int(kayit["kimlik"]) if kayit["tur"] == "parca" else None,
            "benzedigi": sahip_ad.get(k_tum[yakinlar[0]], k_tum[yakinlar[0]]),
            "benzedikleri": [sahip_ad.get(k_tum[j], k_tum[j]) for j in yakinlar],
            "parca_sayisi": len(satirlar),
            "skor": float(skor),
        })
    return sonuc
