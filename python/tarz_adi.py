"""Tarzlara otomatik ad — ama İLGİLİ ad (kullanıcı isteği, 2026-09-28).

Ad iki kaynaktan, bu sırayla:

1. **Ayırt eden MusicBrainz etiketi.** Tarzın üyelerinde sık (≥ %30) VE
   kütüphanenin geneline göre belirgin şekilde fazla (kaldıraç ≥ 1,3) olan
   etiket. Yalnız sıklığa bakılsa her tarz "rock" olurdu; yalnız kaldıraca
   bakılsa tek albümlük bir etiket kazanırdı. Skor = pay × kaldıraç.
   Üyelerin en az %40'ında etiket yoksa bu yol denenmez.
2. **Merkezdeki sanatçılar**: "Casiopea · Plini tarzı". Her zaman doğru —
   etiketsiz (liste/Spotify) kullanıcılar bu yola düşer.

Sesten SIFIRDAN tür tahmini (CLAP metin eşleşmesi) kullanılmaz: tüm
kütüphanede ölçülüp çöktü (karar günlüğü 2026-08-18).

Aynı ad iki tarza düşerse ikincisine merkezdeki sanatçı eklenir. Kullanıcının
verdiği ada DOKUNULMAZ; yalnız boş olanlar doldurulur.
"""

from __future__ import annotations

import sqlite3
from collections import Counter

from python.dil import t

ASGARI_PAY = 0.30
ASGARI_KALDIRAC = 1.3
ETIKET_KAPSAMA = 0.40


def _keskin_uyeler(conn: sqlite3.Connection, calisma_id: str) -> dict[int, list[tuple[float, str, str]]]:
    """kume_id → [(üyelik, album_id, sanatçı)], üyeliğe göre azalan."""
    en_iyi: dict[str, tuple[int, float, str]] = {}
    for r in conn.execute(
            """SELECT m.album_id, m.kume_id, m.uyelik, a.artist FROM memberships m
                 JOIN albums a USING (album_id) WHERE m.calisma_id = ?""", (calisma_id,)):
        onceki = en_iyi.get(r[0])
        if onceki is None or r[2] > onceki[1]:
            en_iyi[r[0]] = (int(r[1]), float(r[2]), r[3])
    gruplar: dict[int, list[tuple[float, str, str]]] = {}
    for album_id, (kume, uyelik, sanatci) in en_iyi.items():
        gruplar.setdefault(kume, []).append((uyelik, album_id, sanatci))
    for g in gruplar.values():
        g.sort(reverse=True)
    return gruplar


def _merkez_sanatcilar(uyeler: list[tuple[float, str, str]], adet: int = 2) -> list[str]:
    sonuc: list[str] = []
    for _, _, s in uyeler:
        if s not in sonuc:
            sonuc.append(s)
        if len(sonuc) == adet:
            break
    return sonuc


def ad_onerileri(conn: sqlite3.Connection, calisma_id: str) -> dict[int, str]:
    """Her kümeye ilgili bir ad önerisi (kaydetmez)."""
    gruplar = _keskin_uyeler(conn, calisma_id)
    etiketler: dict[str, set[str]] = {}
    for album_id, tag in conn.execute("SELECT album_id, tag FROM tags WHERE tag IS NOT NULL"):
        etiketler.setdefault(album_id, set()).add(tag)
    tum = [a for g in gruplar.values() for _, a, _ in g]
    genel = Counter(tag for a in tum for tag in etiketler.get(a, ()))
    genel_payda = max(1, sum(1 for a in tum if a in etiketler))

    oneriler: dict[int, str] = {}
    for kume, uyeler in sorted(gruplar.items(), key=lambda kv: -len(kv[1])):
        albumler = [a for _, a, _ in uyeler]
        etiketli = [a for a in albumler if a in etiketler]
        ad = ""
        if len(etiketli) >= ETIKET_KAPSAMA * len(albumler):
            say = Counter(tag for a in etiketli for tag in etiketler[a])
            en_iyi, en_skor = "", 0.0
            for tag, n in say.items():
                pay = n / len(etiketli)
                kaldirac = pay / (genel[tag] / genel_payda)
                if pay >= ASGARI_PAY and kaldirac >= ASGARI_KALDIRAC and pay * kaldirac > en_skor:
                    en_iyi, en_skor = tag, pay * kaldirac
            ad = en_iyi
        merkez = _merkez_sanatcilar(uyeler)
        if not ad:
            ad = t(" · ".join(merkez) + " tarzı", " · ".join(merkez) + " style")
        if ad.casefold() in {v.casefold() for v in oneriler.values()} and merkez:
            ad = f"{ad} ({merkez[0]})"
        oneriler[kume] = ad
    return oneriler


def bos_olanlari_adlandir(conn: sqlite3.Connection, calisma_id: str) -> int:
    """Adı boş STABİL tarzlara öneriyi yaz. Kullanıcının adına dokunmaz."""
    oneriler = ad_onerileri(conn, calisma_id)
    bos = [r[0] for r in conn.execute(
        "SELECT kume_id FROM clusters WHERE calisma_id = ? AND stabil_mi = 1 "
        "AND COALESCE(kullanici_adi, '') = ''", (calisma_id,))]
    adli = {r[0].casefold() for r in conn.execute(
        "SELECT kullanici_adi FROM clusters WHERE calisma_id = ? "
        "AND COALESCE(kullanici_adi, '') != ''", (calisma_id,))}
    yazilan = 0
    with conn:
        for kume in bos:
            ad = oneriler.get(kume)
            if not ad or ad.casefold() in adli:
                continue
            conn.execute("UPDATE clusters SET kullanici_adi = ? WHERE calisma_id = ? AND kume_id = ?",
                         (ad, calisma_id, kume))
            adli.add(ad.casefold())
            yazilan += 1
    return yazilan
