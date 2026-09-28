"""«Sen» — kullanıcıya kısa, düz bir dille "sen böylesin" diyen portre.

## Hangi cümleler kurulabilir (K13)

"Sen şöylesin" demek bir dayanak ister. Burada YALNIZ şunlar kullanılıyor:

- **Zevk eksenleri** (FCM kümeleri): her eksen merkezine en yakın sanatçılarla
  anlatılır ("Casiopea · Takanaka · Plini gibi"); kullanıcı ad verdiyse o ad.
  Her kullanıcıda var: yerel, liste ya da Spotify.
- **Dönem**: albüm yılları — mutlak bilgi.
- **Türler**: MusicBrainz etiketleri, yalnız albümlerin yeterli bir kısmında
  varsa. Sesten SIFIRDAN tür tahmini KULLANILMAZ: tüm kütüphanede ölçüldü
  ve çöktü (TOOL → "anadolu", karar günlüğü 2026-08-18).
- **Sanatçılar**: kütüphanede en çok albümü olanlar.
- **Keşif tarzı**: kaydırma kararlarının kendisi.

Ölçüm etiketleri ("hızlı", "ride ağırlıklı davul") burada YOK: eşikleri
kütüphanenin kendi kuyruğundan geldiği için her kütüphanede %20 "hızlı" çıkar;
"sen hızlı müzik seviyorsun" cümlesi tanım gereği boş olurdu.

Sayılar önbelleğe girebilir, cümleler girmez (K22): metin gösterimde kurulur.
"""

from __future__ import annotations

import sqlite3
from collections import Counter

from python.dil import t
from python.metin import normalize_esleme

#: Bir tür etiketinin portreye girmesi için albümlerin en az bu kadarında olması.
TUR_ASGARI_PAY = 0.10
#: Türlerden söz etmek için albümlerin en az bu kadarında HERHANGİ bir etiket olmalı.
TUR_KAPSAMA = 0.40
#: Bir eksen bu kadar albümden küçükse "damar" sayılmaz.
EKSEN_ASGARI_ALBUM = 3


def _eksenler(conn: sqlite3.Connection, calisma_id: str | None) -> list[dict]:
    """Eksen başına keskin üye sayısı ve merkezdeki üç sanatçı, büyükten küçüğe."""
    if not calisma_id:
        return []
    uyeler = conn.execute(
        """SELECT m.album_id, m.kume_id, m.uyelik, a.artist
             FROM memberships m JOIN albums a USING (album_id)
            WHERE m.calisma_id = ?""", (calisma_id,)).fetchall()
    en_iyi: dict[str, tuple[int, float, str]] = {}
    for r in uyeler:
        onceki = en_iyi.get(r["album_id"])
        if onceki is None or r["uyelik"] > onceki[1]:
            en_iyi[r["album_id"]] = (int(r["kume_id"]), float(r["uyelik"]), r["artist"])
    adlar = {int(r[0]): r[1] for r in conn.execute(
        "SELECT kume_id, kullanici_adi FROM clusters WHERE calisma_id = ?", (calisma_id,))}
    gruplar: dict[int, list[tuple[float, str]]] = {}
    for kume, uyelik, sanatci in en_iyi.values():
        gruplar.setdefault(kume, []).append((uyelik, sanatci))
    toplam = max(1, len(en_iyi))
    # Renk sırası panoyla aynı: TÜM tarzlar büyüklüğe göre (web/grafik.py:tarz_rengi).
    renk = {k: i for i, k in enumerate(sorted(gruplar, key=lambda k: -len(gruplar[k])))}
    sonuc = []
    for kume, albumler in gruplar.items():
        if len(albumler) < EKSEN_ASGARI_ALBUM:
            continue
        sanatcilar: list[str] = []
        for _, s in sorted(albumler, reverse=True):
            if s not in sanatcilar:
                sanatcilar.append(s)
            if len(sanatcilar) == 3:
                break
        sonuc.append({"kume": kume, "ad": adlar.get(kume) or "", "album": len(albumler),
                      "pay": len(albumler) / toplam, "sanatcilar": sanatcilar,
                      "renk": renk[kume]})
    return sorted(sonuc, key=lambda e: -e["album"])


def _donem(conn: sqlite3.Connection) -> dict | None:
    yillar = [int(r[0]) for r in conn.execute("SELECT year FROM albums WHERE year > 1900")]
    albumler = conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0]
    if not yillar or len(yillar) < 0.5 * albumler:
        return None
    onyil = Counter(y // 10 * 10 for y in yillar)
    en, adet = onyil.most_common(1)[0]
    return {"onyil": en, "pay": adet / len(yillar), "en_eski": min(yillar),
            "en_yeni": max(yillar),
            "dagilim": [(o, onyil.get(o, 0)) for o in range(min(onyil), max(onyil) + 10, 10)]}


def _turler(conn: sqlite3.Connection) -> list[dict]:
    albumler = conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0]
    etiketli = conn.execute("SELECT COUNT(DISTINCT album_id) FROM tags").fetchone()[0]
    if not albumler or etiketli < TUR_KAPSAMA * albumler:
        return []
    sayac = Counter(r[0] for r in conn.execute(
        "SELECT tag FROM tags WHERE tag IS NOT NULL GROUP BY album_id, tag"))
    return [{"etiket": e, "pay": n / etiketli} for e, n in sayac.most_common(6)
            if n / etiketli >= TUR_ASGARI_PAY]


def _sanatcilar(conn: sqlite3.Connection, adet: int = 8) -> list[dict]:
    """En çok albümü olan sanatçılar + raf için birer albüm (kapak)."""
    return [{"ad": r[0], "album": int(r[1]), "album_id": r[2], "baslik": r[3]}
            for r in conn.execute(
                """SELECT artist, COUNT(*) n, MIN(album_id), MIN(title) FROM albums
                    GROUP BY artist HAVING n >= 2 ORDER BY n DESC, artist LIMIT ?""", (adet,))]


def _kesif(conn: sqlite3.Connection) -> dict | None:
    """Sanatçı düzeyinde karar sayıları (dört albümlük sanatçı bir kez sayılır)."""
    satirlar = conn.execute(
        """SELECT a.artist, f.karar FROM feedback f
             JOIN adaylar a ON a.aday_id = f.aday_id AND a.calisma_id = f.calisma_id""").fetchall()
    kararlar: dict[str, str] = {}
    for r in satirlar:
        kararlar[normalize_esleme(r["artist"])] = r["karar"]
    if not kararlar:
        return None
    say = Counter(kararlar.values())
    liste = conn.execute("SELECT COUNT(*) FROM liste").fetchone()[0] if _tablo_var(conn, "liste") else 0
    return {"sanatci": len(kararlar), "begendim": say.get("begendim", 0),
            "tutmadi": say.get("tutmadi", 0), "biliyorum": say.get("zaten_biliyorum", 0),
            "liste": int(liste)}


def _tablo_var(conn: sqlite3.Connection, ad: str) -> bool:
    try:
        conn.execute(f"SELECT 1 FROM {ad} LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def _vitrin(conn: sqlite3.Connection, calisma_id: str | None, adet: int = 9) -> list[dict]:
    """Kapak mozaiği: tarzların en yüksek üyelikli albümleri, sırayla birer
    birer (her tarzdan), sanatçı tekrarı yok. Tarz yoksa rastgele değil,
    en çok albümü olan sanatçılardan."""
    satirlar = []
    if calisma_id:
        satirlar = conn.execute(
            """SELECT m.kume_id, a.album_id, a.artist, a.title FROM memberships m
                 JOIN albums a USING (album_id) WHERE m.calisma_id = ?
                ORDER BY m.uyelik DESC""", (calisma_id,)).fetchall()
    if not satirlar:
        satirlar = conn.execute(
            "SELECT 0, album_id, artist, title FROM albums ORDER BY artist, year").fetchall()
    kuyruk: dict[int, list] = {}
    for r in satirlar:
        kuyruk.setdefault(int(r[0]), []).append(r)
    secilen, gorulen = [], set()
    while len(secilen) < adet and any(kuyruk.values()):
        for k in list(kuyruk):
            while kuyruk[k]:
                r = kuyruk[k].pop(0)
                if r[2] not in gorulen:
                    gorulen.add(r[2])
                    secilen.append({"album_id": r[1], "artist": r[2], "title": r[3]})
                    break
            if len(secilen) >= adet:
                break
    return secilen


def portre(conn: sqlite3.Connection, calisma_id: str | None) -> dict:
    """Sayılar ve adlar — cümleler gösterimde (`ozet_cumlesi`, şablon)."""
    return {
        "album": conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0],
        "eksenler": _eksenler(conn, calisma_id),
        "donem": _donem(conn),
        "turler": _turler(conn),
        "sanatcilar": _sanatcilar(conn),
        "kesif": _kesif(conn),
        "vitrin": _vitrin(conn, calisma_id),
    }


def eksen_adi(e: dict) -> str:
    """Kullanıcının verdiği ad; yoksa merkezdeki sanatçılar."""
    return e["ad"] or t(" · ".join(e["sanatcilar"]) + " gibi", "like " + " · ".join(e["sanatcilar"]))


#: On yılın çoğul eki, sayının OKUNUŞUNA göre: 1990 "doksan" → 'lar,
#: 1980 "seksen" → 'ler, 2010 "on" → 'lar, 2000 "bin" → 'ler.
_ONYIL_EKI = {0: "ler", 10: "lar", 20: "ler", 30: "lar", 40: "lar",
              50: "ler", 60: "lar", 70: "ler", 80: "ler", 90: "lar"}


def onyil_adi(onyil: int) -> str:
    return t(f"{onyil}'{_ONYIL_EKI[onyil % 100]}", f"the {onyil}s")


def ozet_cumlesi(p: dict) -> str:
    """Tek cümlelik portre. Dayanağı olmayan parça cümleye girmez."""
    parcalar = []
    eksenler = p["eksenler"]
    if eksenler:
        ilk = eksenler[0]
        if len(eksenler) > 1:
            parcalar.append(t(
                f"Müziğin {len(eksenler)} tarza ayrılıyor; en büyüğü {eksen_adi(ilk)}",
                f"Your music splits into {len(eksenler)} styles; the biggest is {eksen_adi(ilk)}"))
        else:
            parcalar.append(t(f"Müziğin tek bir tarzda toplanıyor: {eksen_adi(ilk)}",
                              f"Your music sits in one style: {eksen_adi(ilk)}"))
    if p["turler"]:
        ilk_iki = " ve ".join(x["etiket"] for x in p["turler"][:2])
        ilk_iki_en = " and ".join(x["etiket"] for x in p["turler"][:2])
        parcalar.append(t(f"en sık rastlanan türler {ilk_iki}", f"the most common genres are {ilk_iki_en}"))
    if p["donem"] and p["donem"]["pay"] >= 0.3:
        parcalar.append(t(f"kalbin {onyil_adi(p['donem']['onyil'])} müziğinde",
                          f"your heart is in {onyil_adi(p['donem']['onyil'])}"))
    if not parcalar:
        return ""
    cumle = "; ".join(parcalar) + "."
    return cumle[0].upper() + cumle[1:]
